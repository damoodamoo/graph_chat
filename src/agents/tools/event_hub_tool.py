import uuid
from logging import getLogger

from src.agents.models.models import Preferences
from src.ingestion.ingest.event_hub_producer import EventHubService
from src.ingestion.models.events import Action, EdgeType, GraphEdgeEvent, NodeType


logger = getLogger(__name__)


class EventHubTool:
    """Tool for sending preference events to Azure Event Hub."""

    def __init__(self, customer_id: str, env_file: str = "app.env"):
        """
        Initialize the EventHubTool.

        Args:
            customer_id: The customer ID to associate with preference events.
            env_file: Path to the environment file for Event Hub configuration.
        """
        self._customer_id = customer_id
        self._event_hub_service = EventHubService(env_file=env_file)

    def send_preferences(self, preferences: Preferences) -> None:
        """
        Convert Preferences to GraphEdgeEvents and send to Event Hub.

        Creates 'likes' edges between the customer and the items they prefer
        (either colour_groups or articles).

        Args:
            preferences: The Preferences object containing user preference signals.
        """
        if not preferences or not preferences.prefs:
            logger.info("No preferences to send")
            return

        events: list[GraphEdgeEvent] = []

        for pref in preferences.prefs:
            # Map item_type to appropriate NodeType
            target_node_type = self._map_item_type_to_node_type(pref.item_type)
            if target_node_type is None:
                logger.warning(f"Unknown item type: {pref.item_type}, skipping")
                continue

            event = GraphEdgeEvent(
                event_id=uuid.uuid4(),
                edge_type=EdgeType.LIKES,
                source_node_id=self._customer_id,
                source_node_type=NodeType.USER,
                target_node_id=pref.value,
                target_node_type=target_node_type,
                data={},
                action=Action.UPSERT,
            )
            events.append(event)

        if events:
            logger.info(f"Sending {len(events)} preference events to Event Hub")
            self._event_hub_service.send_edge_events(events)

    def _map_item_type_to_node_type(self, item_type: str) -> NodeType | None:
        """
        Map preference item types to graph node types.

        Args:
            item_type: The item type from the preference (e.g., 'colour_group', 'article').

        Returns:
            The corresponding NodeType, or None if unknown.
        """
        mapping = {
            "colour_group": NodeType.COLOUR_GROUP,
            "article": NodeType.ARTICLE,
            "product": NodeType.PRODUCT,
            "product_type": NodeType.PRODUCT_TYPE,
            "product_group": NodeType.PRODUCT_GROUP,
            "department": NodeType.DEPARTMENT,
            "index_group": NodeType.INDEX_GROUP,
        }
        return mapping.get(item_type.lower())

    def close(self) -> None:
        """Close the underlying Event Hub service."""
        self._event_hub_service.close()

    def __enter__(self) -> "EventHubTool":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
