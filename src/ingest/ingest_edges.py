from uuid import uuid4

from src.ingest.csv_loader import CsvLoader
from src.ingest.event_hub_producer import EventHubService
from src.models.events import Action, EdgeType, GraphEdgeEvent, NodeType

ARTICLES_CSV = "data/articles.csv"


def ingest_edges(
    source_field: str,
    target_field: str,
    edge_type: EdgeType,
    source_node_type: NodeType,
    target_node_type: NodeType,
    csv_path: str = ARTICLES_CSV,
    batch_size: int = 10000,
    max_rows: int | None = None,
) -> None:
    """
    Load a CSV file, extract unique source->target relationships,
    create GraphEdgeEvents for each, and send them to Event Hub in batches.

    Args:
        source_field: Name of the column for the source node
        target_field: Name of the column for the target node
        edge_type: The EdgeType to assign to created events
        source_node_type: The NodeType of the source node
        target_node_type: The NodeType of the target node
        csv_path: Path to the CSV file
        batch_size: Number of events to send per batch
        max_rows: Maximum number of rows to read from CSV (default: None = all rows)
    """
    df = CsvLoader.load(csv_path, max_rows=max_rows)

    # Get unique source->target pairs, excluding rows with NaN in either field
    unique_pairs = df[[source_field, target_field]].dropna().drop_duplicates()

    print(f"Found {len(unique_pairs)} unique {source_field} -> {target_field} edges")

    # Create GraphEdgeEvents for each unique pair
    events: list[GraphEdgeEvent] = []
    for _, row in unique_pairs.iterrows():
        event = GraphEdgeEvent(
            event_id=uuid4(),
            edge_type=edge_type,
            source_node_id=str(row[source_field]),
            source_node_type=source_node_type,
            target_node_id=str(row[target_field]),
            target_node_type=target_node_type,
            action=Action.UPSERT,
        )
        events.append(event)

    # Send events to Event Hub in batches
    with EventHubService() as event_hub:
        for i in range(0, len(events), batch_size):
            batch = events[i : i + batch_size]
            event_hub.send_edge_events(batch)
            print(f"Sent batch {i // batch_size + 1}: {len(batch)} events")

    print(f"Successfully sent {len(events)} {source_field} -> {target_field} edge events")


def ingest_all_edges(max_rows: int | None = None) -> None:
    """Ingest all edge relationships from the articles CSV.
    
    Args:
        max_rows: Maximum number of rows to read from CSV (default: None = all rows)
    """
    
    # product_type_name -> product_group_name
    ingest_edges(
        source_field="product_type_name",
        target_field="product_group_name",
        edge_type=EdgeType.BELONGS_TO,
        source_node_type=NodeType.PRODUCT_TYPE,
        target_node_type=NodeType.PRODUCT_GROUP,
        max_rows=max_rows,
    )

    # product_name -> product_type_name
    ingest_edges(
        source_field="prod_name",
        target_field="product_type_name",
        edge_type=EdgeType.BELONGS_TO,
        source_node_type=NodeType.PRODUCT,
        target_node_type=NodeType.PRODUCT_TYPE,
        max_rows=max_rows,
    )

    # product -> index_group
    ingest_edges(
        source_field="prod_name",
        target_field="index_group_name",
        edge_type=EdgeType.BELONGS_TO,
        source_node_type=NodeType.PRODUCT,
        target_node_type=NodeType.INDEX_GROUP,
        max_rows=max_rows,
    )

    # article -> product
    ingest_edges(
        source_field="article_id",
        target_field="prod_name",
        edge_type=EdgeType.BELONGS_TO,
        source_node_type=NodeType.ARTICLE,
        target_node_type=NodeType.PRODUCT,
        max_rows=max_rows,
    )

    # article -> colour
    ingest_edges(
        source_field="article_id",
        target_field="colour_group_name",
        edge_type=EdgeType.BELONGS_TO,
        source_node_type=NodeType.ARTICLE,
        target_node_type=NodeType.COLOUR_GROUP,
        max_rows=max_rows,
    )


if __name__ == "__main__":
    ingest_all_edges()
