"""
Script to create smaller versions of the CSV files for testing/development.

This script:
1. Selects the top 1000 customers from customers.csv
2. Finds all transactions for those customers from transactions_train.csv (chunked reading)
3. Finds all articles referenced in those transactions from articles.csv
4. Saves the filtered data to *_mini.csv files in the data folder
"""

import pandas as pd
from pathlib import Path

# File paths
DATA_DIR = Path("data")
CUSTOMERS_CSV = DATA_DIR / "customers.csv"
TRANSACTIONS_CSV = DATA_DIR / "transactions_train.csv"
ARTICLES_CSV = DATA_DIR / "articles.csv"

# Output paths
CUSTOMERS_MINI = DATA_DIR / "customers_mini.csv"
TRANSACTIONS_MINI = DATA_DIR / "transactions_train_mini.csv"
ARTICLES_MINI = DATA_DIR / "articles_mini.csv"

# Configuration
TOP_N_CUSTOMERS = 1000
CHUNK_SIZE = 100000


def create_mini_csvs():
    """Create mini versions of the CSV files."""
    
    # Step 1: Load top 1000 customers
    print(f"Loading top {TOP_N_CUSTOMERS} customers from {CUSTOMERS_CSV}...")
    customers_df = pd.read_csv(CUSTOMERS_CSV, nrows=TOP_N_CUSTOMERS)
    customer_ids = set(customers_df["customer_id"].astype(str))
    print(f"Loaded {len(customer_ids)} customers")
    
    # Step 2: Find all transactions for these customers (chunked reading)
    print(f"Finding transactions for selected customers from {TRANSACTIONS_CSV}...")
    matching_transactions = []
    article_ids = set()
    
    for chunk_num, chunk in enumerate(pd.read_csv(TRANSACTIONS_CSV, chunksize=CHUNK_SIZE)):
        # Convert customer_id to string for matching
        chunk["customer_id"] = chunk["customer_id"].astype(str)
        
        # Filter transactions for our customers
        matching = chunk[chunk["customer_id"].isin(customer_ids)]
        
        if len(matching) > 0:
            matching_transactions.append(matching)
            # Collect article IDs
            article_ids.update(matching["article_id"].astype(str).unique())
        
        print(f"  Chunk {chunk_num + 1}: found {len(matching)} matching transactions (total articles so far: {len(article_ids)})")
    
    # Combine all matching transactions
    if matching_transactions:
        transactions_df = pd.concat(matching_transactions, ignore_index=True)
    else:
        transactions_df = pd.DataFrame()
    
    print(f"Found {len(transactions_df)} total transactions for selected customers")
    print(f"Found {len(article_ids)} unique articles in transactions")
    
    # Step 3: Find all articles referenced in transactions
    print(f"Loading matching articles from {ARTICLES_CSV}...")
    articles_df = pd.read_csv(ARTICLES_CSV)
    articles_df["article_id"] = articles_df["article_id"].astype(str)
    matching_articles = articles_df[articles_df["article_id"].isin(article_ids)]
    print(f"Found {len(matching_articles)} matching articles")
    
    # Step 4: Save to mini CSV files
    print(f"\nSaving mini CSV files...")
    
    customers_df.to_csv(CUSTOMERS_MINI, index=False)
    print(f"  Saved {len(customers_df)} customers to {CUSTOMERS_MINI}")
    
    transactions_df.to_csv(TRANSACTIONS_MINI, index=False)
    print(f"  Saved {len(transactions_df)} transactions to {TRANSACTIONS_MINI}")
    
    matching_articles.to_csv(ARTICLES_MINI, index=False)
    print(f"  Saved {len(matching_articles)} articles to {ARTICLES_MINI}")
    
    print("\nDone!")


if __name__ == "__main__":
    create_mini_csvs()