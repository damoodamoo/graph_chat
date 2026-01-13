"""
Main consumer module for processing graph events from Event Hub into Cosmos DB.
"""

import signal
import sys
from typing import NoReturn

from src.ingestion.consume.event_hub_consumer import EventHubConsumerService
from src.ingestion.consume.gremlin_client import GremlinService
from src.ingestion.models.events import GraphEdgeEvent, GraphNodeEvent


class GraphEventProcessor:
    """
    Processor that consumes events from Event Hub and writes them to Cosmos DB Graph.

    Uses batch processing for node events to improve throughput.
    """

    # Batch configuration
    NODE_BATCH_SIZE = 50  # Number of nodes to process in a single Gremlin batch

    def __init__(self):
        self.gremlin_service = GremlinService()
        self.consumer_service = EventHubConsumerService()
        self._running = False
        self._node_event_batch: list[GraphNodeEvent] = []

    def _handle_node_event(self, event: GraphNodeEvent) -> None:
        """
        Collect node events for batch processing.

        Events are accumulated and processed when batch size is reached.
        """
        self._node_event_batch.append(event)

        if len(self._node_event_batch) >= self.NODE_BATCH_SIZE:
            self._flush_node_batch()

    def _flush_node_batch(self) -> None:
        """Process accumulated node events as a batch."""
        if not self._node_event_batch:
            return

        try:
            batch_size = len(self._node_event_batch)
            self.gremlin_service.process_node_events_batch(
                self._node_event_batch, batch_size=self.NODE_BATCH_SIZE
            )
            print(f"Processed batch of {batch_size} node events")
        except Exception as e:
            print(f"Failed to process node batch: {e}")
            # Fall back to processing individually
            for event in self._node_event_batch:
                try:
                    self.gremlin_service.process_node_event(event)
                except Exception as individual_error:
                    print(
                        f"Failed to process node event {event.event_id}: {individual_error}"
                    )
        finally:
            self._node_event_batch = []

    def _handle_edge_event(self, event: GraphEdgeEvent) -> None:
        """Process an edge event by writing to Cosmos DB."""
        # Flush any pending node events before processing edges
        # to ensure nodes exist before creating edges
        self._flush_node_batch()

        try:
            self.gremlin_service.process_edge_event(event)
        except Exception as e:
            print(f"Failed to process edge event {event.event_id}: {e}")

    def start(self, starting_position: str = "@latest") -> None:
        """
        Start consuming and processing events.

        Args:
            starting_position: Where to start consuming from.
                              "@latest" for new events only,
                              "-1" for all events from beginning.
        """
        self._running = True

        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print("Starting Graph Event Processor...")
        print(f"Starting position: {starting_position}")
        print(f"Node batch size: {self.NODE_BATCH_SIZE}")

        # Configure handlers
        self.consumer_service.set_node_event_handler(self._handle_node_event)
        self.consumer_service.set_edge_event_handler(self._handle_edge_event)
        self.consumer_service.set_batch_complete_handler(self._flush_node_batch)

        try:
            # Start consuming (this is blocking)
            self.consumer_service.receive_batch(starting_position=starting_position, resume_from_checkpoint=True)
        except KeyboardInterrupt:
            print("\nReceived keyboard interrupt")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the processor and clean up resources."""
        if not self._running:
            return

        print("Stopping Graph Event Processor...")
        self._running = False

        # Flush any remaining node events
        self._flush_node_batch()

        self.consumer_service.close()
        self.gremlin_service.close()

        print("Graph Event Processor stopped.")

    def _signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        print(f"\nReceived signal {signum}")
        self.stop()
        sys.exit(0)


def run_consumer(starting_position: str = "@latest") -> None:
    """
    Run the graph event consumer.

    Args:
        starting_position: Where to start consuming from.
    """
    processor = GraphEventProcessor()
    processor.start(starting_position=starting_position)


def process_all_events() -> None:
    """Process all events from the beginning of the Event Hub."""
    run_consumer(starting_position="-1")


def process_new_events() -> None:
    """Process only new events arriving in the Event Hub."""
    run_consumer(starting_position="@latest")


if __name__ == "__main__":
    # Default: process only new events
    process_new_events()
