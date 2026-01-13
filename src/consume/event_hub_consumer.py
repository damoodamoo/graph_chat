import json
import os
from pathlib import Path
from typing import Callable

from azure.eventhub import EventHubConsumerClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from src.models.events import GraphEdgeEvent, GraphNodeEvent


class LocalCheckpointStore:
    """Simple file-based checkpoint store for local development."""

    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def _get_checkpoint_path(
        self, fully_qualified_namespace: str, eventhub_name: str, consumer_group: str, partition_id: str
    ) -> Path:
        """Get the path to the checkpoint file for a partition."""
        safe_name = f"{eventhub_name}_{consumer_group}_{partition_id}".replace("/", "_").replace("$", "_")
        return self.checkpoint_dir / f"{safe_name}.json"

    def get_checkpoint(
        self, fully_qualified_namespace: str, eventhub_name: str, consumer_group: str, partition_id: str
    ) -> dict | None:
        """Load checkpoint for a partition."""
        path = self._get_checkpoint_path(fully_qualified_namespace, eventhub_name, consumer_group, partition_id)
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def save_checkpoint(
        self,
        fully_qualified_namespace: str,
        eventhub_name: str,
        consumer_group: str,
        partition_id: str,
        offset: str,
        sequence_number: int,
    ) -> None:
        """Save checkpoint for a partition."""
        path = self._get_checkpoint_path(fully_qualified_namespace, eventhub_name, consumer_group, partition_id)
        with open(path, "w") as f:
            json.dump({"offset": offset, "sequence_number": sequence_number}, f)


class EventHubConsumerService:
    """Service class for consuming graph events from Azure Event Hub."""

    def __init__(
        self,
        env_file: str = "app.env",
        consumer_group: str = "$Default",
        checkpoint_store: LocalCheckpointStore | None = None,
    ):
        load_dotenv(env_file)

        self.namespace_name = os.getenv("EVENTHUB_NAMESPACE_NAME")
        self.eventhub_name = os.getenv("EVENTHUB_NAME", "")
        self.consumer_group = consumer_group

        if not self.namespace_name or not self.eventhub_name:
            raise ValueError(
                "EVENTHUB_NAMESPACE_NAME and EVENTHUB_NAME must be set in environment"
            )

        self.fully_qualified_namespace = f"{self.namespace_name}.servicebus.windows.net"
        self._consumer: EventHubConsumerClient | None = None
        self._checkpoint_store = checkpoint_store or LocalCheckpointStore()
        self._on_node_event: Callable[[GraphNodeEvent], None] | None = None
        self._on_edge_event: Callable[[GraphEdgeEvent], None] | None = None

    @property
    def consumer(self) -> EventHubConsumerClient:
        """Lazy initialization of the Event Hub consumer client."""
        if self._consumer is None:
            credential = DefaultAzureCredential()

            self._consumer = EventHubConsumerClient(
                fully_qualified_namespace=self.fully_qualified_namespace,
                eventhub_name=self.eventhub_name,
                consumer_group=self.consumer_group,
                credential=credential,
            )

        return self._consumer

    def set_node_event_handler(
        self, handler: Callable[[GraphNodeEvent], None]
    ) -> "EventHubConsumerService":
        """
        Set the handler for processing node events.

        Args:
            handler: Callback function to process GraphNodeEvent objects

        Returns:
            Self for method chaining
        """
        self._on_node_event = handler
        return self

    def set_edge_event_handler(
        self, handler: Callable[[GraphEdgeEvent], None]
    ) -> "EventHubConsumerService":
        """
        Set the handler for processing edge events.

        Args:
            handler: Callback function to process GraphEdgeEvent objects

        Returns:
            Self for method chaining
        """
        self._on_edge_event = handler
        return self

    def _process_event(self, partition_context, event) -> None:
        """
        Process a single event from Event Hub.

        Determines if the event is a node or edge event and calls the appropriate handler.
        """
        if event is None:
            return

        try:
            event_body = event.body_as_str()
            data = json.loads(event_body)

            # Determine event type based on fields present
            if "node_type" in data:
                node_event = GraphNodeEvent.model_validate(data)
                if self._on_node_event:
                    self._on_node_event(node_event)
                    print(
                        f"Processed node event: {node_event.event_id} "
                        f"({node_event.node_type.value})"
                    )
            elif "edge_type" in data:
                edge_event = GraphEdgeEvent.model_validate(data)
                if self._on_edge_event:
                    self._on_edge_event(edge_event)
                    print(
                        f"Processed edge event: {edge_event.event_id} "
                        f"({edge_event.edge_type.value})"
                    )
            else:
                print(f"Unknown event type: {data}")

        except json.JSONDecodeError as e:
            print(f"Failed to parse event JSON: {e}")
        except Exception as e:
            print(f"Error processing event: {e}")

        # Update local checkpoint
        self._checkpoint_store.save_checkpoint(
            fully_qualified_namespace=self.fully_qualified_namespace,
            eventhub_name=self.eventhub_name,
            consumer_group=self.consumer_group,
            partition_id=partition_context.partition_id,
            offset=event.offset,
            sequence_number=event.sequence_number,
        )

    def _on_error(self, partition_context, error) -> None:
        """Handle errors during event processing."""
        if partition_context:
            print(
                f"Error in partition {partition_context.partition_id}: {error}"
            )
        else:
            print(f"Error in consumer: {error}")

    def _get_starting_positions_from_checkpoints(self) -> dict[str, str] | None:
        """
        Get starting positions for each partition from checkpoint files.

        Returns:
            Dict mapping partition_id to offset, or None if no checkpoints exist.
        """
        partition_ids = self.consumer.get_partition_ids()
        starting_positions = {}
        
        for partition_id in partition_ids:
            checkpoint = self._checkpoint_store.get_checkpoint(
                fully_qualified_namespace=self.fully_qualified_namespace,
                eventhub_name=self.eventhub_name,
                consumer_group=self.consumer_group,
                partition_id=partition_id,
            )
            if checkpoint and "offset" in checkpoint:
                starting_positions[partition_id] = checkpoint["offset"]
                print(f"Resuming partition {partition_id} from offset {checkpoint['offset']} (seq: {checkpoint.get('sequence_number', 'unknown')})")
        
        if starting_positions:
            return starting_positions
        return None

    def start_consuming(self, starting_position: str = "-1", resume_from_checkpoint: bool = True) -> None:
        """
        Start consuming events from Event Hub.

        This is a blocking call that will continuously process events.

        Args:
            starting_position: Position to start consuming from.
                              "-1" means from the beginning, "@latest" from new events.
            resume_from_checkpoint: If True, attempt to resume from saved checkpoints.
                                   Falls back to starting_position if no checkpoints exist.
        """
        print(f"Starting to consume events from {self.eventhub_name}...")

        # Try to resume from checkpoints if enabled
        position = starting_position
        if resume_from_checkpoint:
            checkpoint_positions = self._get_starting_positions_from_checkpoints()
            if checkpoint_positions:
                print(f"Resuming from checkpoints for {len(checkpoint_positions)} partition(s)")
                position = checkpoint_positions
            else:
                print(f"No checkpoints found, starting from position: {starting_position}")

        self.consumer.receive(
            on_event=self._process_event,
            on_error=self._on_error,
            starting_position=position,
        )

    def receive_batch(
        self,
        max_batch_size: int = 10000,
        max_wait_time: float = 5.0,
        starting_position: str = "-1",
        resume_from_checkpoint: bool = True,
    ) -> None:
        """
        Receive events in batches from Event Hub.

        Args:
            max_batch_size: Maximum number of events per batch
            max_wait_time: Maximum time to wait for events in seconds
            starting_position: Position to start consuming from
            resume_from_checkpoint: If True, attempt to resume from saved checkpoints.
                                   Falls back to starting_position if no checkpoints exist.
        """

        def on_event_batch(partition_context, events):
            if not events:
                return

            last_event = None
            for event in events:
                self._process_event(partition_context, event)
                last_event = event

            # Checkpoint after processing batch using local store
            if last_event:
                self._checkpoint_store.save_checkpoint(
                    fully_qualified_namespace=self.fully_qualified_namespace,
                    eventhub_name=self.eventhub_name,
                    consumer_group=self.consumer_group,
                    partition_id=partition_context.partition_id,
                    offset=last_event.offset,
                    sequence_number=last_event.sequence_number,
                )

        print(f"Starting batch consumption from {self.eventhub_name}...")

        # Try to resume from checkpoints if enabled
        position = starting_position
        if resume_from_checkpoint:
            checkpoint_positions = self._get_starting_positions_from_checkpoints()
            if checkpoint_positions:
                print(f"Resuming from checkpoints for {len(checkpoint_positions)} partition(s)")
                position = checkpoint_positions
            else:
                print(f"No checkpoints found, starting from position: {starting_position}")

        self.consumer.receive_batch(
            on_event_batch=on_event_batch,
            on_error=self._on_error,
            max_batch_size=max_batch_size,
            max_wait_time=max_wait_time,
            starting_position=position,
        )

    def close(self) -> None:
        """Close the Event Hub consumer client."""
        if self._consumer is not None:
            self._consumer.close()
            self._consumer = None

    def __enter__(self) -> "EventHubConsumerService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
