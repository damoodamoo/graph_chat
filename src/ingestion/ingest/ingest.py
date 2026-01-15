import argparse

from src.ingestion.ingest.ingest_article_nodes import ingest_article_nodes
from src.ingestion.ingest.ingest_customer_nodes import ingest_customer_nodes
from src.ingestion.ingest.ingest_edges import ingest_all_edges


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest data from CSV files to Event Hub")
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Maximum number of rows to read from CSV files (default: all rows)",
    )
    args = parser.parse_args()

    if args.max_rows:
        print(f"Limiting ingestion to top {args.max_rows} rows from CSV files")

    # nodes without edges
    ingest_article_nodes(max_rows=args.max_rows)
    ingest_customer_nodes(max_rows=args.max_rows)

    # ingest edge events. connect:
    # product_type_name -> product_group_name
    # product_name -> product_type_name
    # product -> index_group
    # article -> product
    # customer -> article
    ingest_all_edges(max_rows=args.max_rows)





