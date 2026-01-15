from src.ingestion.ingest.ingest_article_nodes import ingest_unique_field_values
from src.ingestion.models.events import NodeType


def ingest_customer_nodes(max_rows: int | None = None):
    """
    Ingest customer-related nodes from customers.csv.
    
    Creates nodes for:
    - USER: Individual customers with their attributes
    """

    ingest_unique_field_values(
        field_name="customer_id",
        node_type=NodeType.USER,
        data_fields=["age", "club_member_status", "fashion_news_frequency"],
        csv_path="data/customers_mini.csv",
        max_rows=max_rows,
    )
