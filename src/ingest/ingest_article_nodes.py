from uuid import uuid4

from src.ingest.csv_loader import CsvLoader
from src.ingest.event_hub_producer import EventHubService
from src.models.events import Action, GraphNodeEvent, NodeType


def ingest_unique_field_values(
    field_name: str,
    node_type: NodeType,
    csv_path: str = "data/articles.csv",
    batch_size: int = 10000,
    max_rows: int | None = None,
) -> None:
    """
    Load a CSV file, extract unique values for a given field,
    create GraphNodeEvents for each, and send them to Event Hub in batches.

    Args:
        field_name: Name of the column to extract unique values from
        node_type: The NodeType to assign to created events
        csv_path: Path to the CSV file
        batch_size: Number of events to send per batch (default: 50)
        max_rows: Maximum number of rows to read from CSV (default: None = all rows)
    """
    # Load the CSV file
    df = CsvLoader.load(csv_path, max_rows=max_rows)

    # Get unique values for the field, excluding NaN
    unique_values = df[field_name].dropna().unique().astype(str)

    print(f"Found {len(unique_values)} unique {field_name} values")


    #TODO: refactor this to a more generic file?
    # Create GraphNodeEvents for each unique value
    events: list[GraphNodeEvent] = []
    for value in unique_values:
        event = GraphNodeEvent(
            event_id=uuid4(),
            node_type=node_type,
            data={"name": value},
            label=value,
            action=Action.UPSERT,
        )
        events.append(event)

    # Send events to Event Hub in batches
    with EventHubService() as event_hub:
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            event_hub.send_node_events(batch)
            print(f"Sent batch {i // batch_size + 1}: {len(batch)} events")

    print(f"Successfully sent {len(events)} {field_name} events")


def ingest_article_nodes(max_rows: int | None = None):
    ingest_unique_field_values(
        field_name="colour_group_name",
        node_type=NodeType.COLOUR_GROUP,
        max_rows=max_rows,
    )

    ingest_unique_field_values(
        field_name="department_name",
        node_type=NodeType.DEPARTMENT,
        max_rows=max_rows,
    )

    ingest_unique_field_values(
        field_name="index_group_name",
        node_type=NodeType.INDEX_GROUP,
        max_rows=max_rows,
    )

    ingest_unique_field_values(
        field_name="product_group_name",
        node_type=NodeType.PRODUCT_GROUP,
        max_rows=max_rows,
    )

    ingest_unique_field_values(
        field_name="product_type_name",
        node_type=NodeType.PRODUCT_TYPE,
        max_rows=max_rows,
    )

    ingest_unique_field_values(
        field_name="prod_name",
        node_type=NodeType.PRODUCT,
        max_rows=max_rows,
    )

    ingest_unique_field_values(
        field_name="article_id",
        node_type=NodeType.ARTICLE,
        max_rows=max_rows,
    )
