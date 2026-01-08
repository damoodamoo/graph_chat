from uuid import uuid4

from src.ingest.csv_loader import CsvLoader
from src.ingest.event_hub_producer import EventHubService
from src.models.events import Action, GraphNodeEvent, NodeType


def ingest_colour_groups(articles_path: str = "data/articles.csv", batch_size: int = 50) -> None:
    """
    Load articles.csv, extract unique colour_group_name values,
    create GraphNodeEvents for each, and send them to Event Hub in batches.

    Args:
        articles_path: Path to the articles CSV file
        batch_size: Number of events to send per batch (default: 50)
    """
    # Load the CSV file
    df = CsvLoader.load(articles_path)

    # Get unique colour_group_name values, excluding NaN
    unique_colours = df["colour_group_name"].dropna().unique()

    print(f"Found {len(unique_colours)} unique colour groups")

    # Create GraphNodeEvents for each unique colour
    events: list[GraphNodeEvent] = []
    for colour_name in unique_colours:
        event = GraphNodeEvent(
            event_id=uuid4(),
            node_type=NodeType.COLOUR_GROUP,
            data={"name": colour_name},
            action=Action.UPSERT,
        )
        events.append(event)

    # Send events to Event Hub in batches
    with EventHubService() as event_hub:
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            event_hub.send_node_events(batch)
            print(f"Sent batch {i // batch_size + 1}: {len(batch)} events")

    print(f"Successfully sent {len(events)} colour group events")


if __name__ == "__main__":
    ingest_colour_groups()

