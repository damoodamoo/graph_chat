"""
Main consumer module for processing graph events from Event Hub into Cosmos DB.
"""

import signal
import sys
from typing import NoReturn

from src.consume.event_hub_consumer import EventHubConsumerService
from src.consume.gremlin_client import GremlinService
from src.models.events import GraphEdgeEvent, GraphNodeEvent


class GraphEventProcessor:
    """
    Processor that consumes events from Event Hub and writes them to Cosmos DB Graph.
    """

    def __init__(self):
        self.gremlin_service = GremlinService()
        self.consumer_service = EventHubConsumerService()
        self._running = False

    def _handle_node_event(self, event: GraphNodeEvent) -> None:
        """Process a node event by writing to Cosmos DB."""
        try:
            self.gremlin_service.process_node_event(event)
        except Exception as e:
            print(f"Failed to process node event {event.event_id}: {e}")

    def _handle_edge_event(self, event: GraphEdgeEvent) -> None:
        """Process an edge event by writing to Cosmos DB."""
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

        # Configure handlers
        self.consumer_service.set_node_event_handler(self._handle_node_event)
        self.consumer_service.set_edge_event_handler(self._handle_edge_event)

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
