import os
from typing import Union

from azure.eventhub import EventData, EventHubProducerClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from src.ingestion.models.events import GraphEdgeEvent, GraphNodeEvent


class EventHubService:
    """Service class for sending graph events to Azure Event Hub in batches."""

    def __init__(self, env_file: str = "app.env"):
        load_dotenv(env_file)

        self.namespace_name = os.getenv("EVENTHUB_NAMESPACE_NAME")
        self.eventhub_name = os.getenv("EVENTHUB_NAME", "")

        if not self.namespace_name or not self.eventhub_name:
            raise ValueError(
                "EVENTHUB_NAMESPACE_NAME and EVENTHUB_NAME must be set in environment"
            )

        self.fully_qualified_namespace = f"{self.namespace_name}.servicebus.windows.net"
        self._producer: EventHubProducerClient | None = None

    @property
    def producer(self) -> EventHubProducerClient:
        """Lazy initialization of the Event Hub producer client."""
        if self._producer is None:
            credential = DefaultAzureCredential()
            self._producer = EventHubProducerClient(
                fully_qualified_namespace=self.fully_qualified_namespace,
                eventhub_name=self.eventhub_name,
                credential=credential,
            )
        return self._producer

    def send_events(
        self,
        events: list[Union[GraphNodeEvent, GraphEdgeEvent]],
        partition_key: str | None = None,
    ) -> None:
        """
        Send a batch of graph events to Event Hub.

        Args:
            events: List of GraphNodeEvent or GraphEdgeEvent objects
            partition_key: Optional partition key for event ordering
        """
        if not events:
            return

        batch = self.producer.create_batch(partition_key=partition_key)

        for event in events:
            event_data = EventData(event.model_dump_json())
            try:
                batch.add(event_data)
            except ValueError:
                # Batch is full, send it and create a new one
                self.producer.send_batch(batch)
                batch = self.producer.create_batch(partition_key=partition_key)
                batch.add(event_data)

        # Send any remaining events
        if len(batch) > 0:
            self.producer.send_batch(batch)

    def send_node_events(
        self,
        events: list[GraphNodeEvent],
        partition_key: str | None = None,
    ) -> None:
        """Send a batch of node events to Event Hub."""
        self.send_events(events, partition_key)

    def send_edge_events(
        self,
        events: list[GraphEdgeEvent],
        partition_key: str | None = None,
    ) -> None:
        """Send a batch of edge events to Event Hub."""
        self.send_events(events, partition_key)

    def close(self) -> None:
        """Close the Event Hub producer client."""
        if self._producer is not None:
            self._producer.close()
            self._producer = None

    def __enter__(self) -> "EventHubService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
