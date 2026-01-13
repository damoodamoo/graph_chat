"""Utility to skip/ignore all existing events from Event Hub by updating checkpoints to latest."""

import argparse
import json
import os
from pathlib import Path

from azure.eventhub import EventHubConsumerClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def clear_checkpoints(checkpoint_dir: str = ".checkpoints") -> int:
    """
    Clear all local checkpoint files.
    
    Args:
        checkpoint_dir: Directory containing checkpoint files
        
    Returns:
        Number of checkpoint files deleted
    """
    checkpoint_path = Path(checkpoint_dir)
    if not checkpoint_path.exists():
        print(f"No checkpoint directory found at {checkpoint_dir}")
        return 0
    
    count = 0
    for checkpoint_file in checkpoint_path.glob("*.json"):
        checkpoint_file.unlink()
        count += 1
        print(f"  Deleted checkpoint: {checkpoint_file.name}")
    
    return count


def set_checkpoints_to_latest(
    env_file: str = "app.env",
    consumer_group: str = "$Default",
    checkpoint_dir: str = ".checkpoints",
) -> int:
    """
    Set checkpoints to the latest position for all partitions.
    
    This effectively makes the consumer skip all existing events and only
    process new events that arrive after this point.
    
    Args:
        env_file: Path to environment file with Event Hub config
        consumer_group: Consumer group name
        checkpoint_dir: Directory for checkpoint files
        
    Returns:
        Number of partitions updated
    """
    load_dotenv(env_file)
    
    namespace_name = os.getenv("EVENTHUB_NAMESPACE_NAME")
    eventhub_name = os.getenv("EVENTHUB_NAME", "")
    
    if not namespace_name or not eventhub_name:
        raise ValueError(
            "EVENTHUB_NAMESPACE_NAME and EVENTHUB_NAME must be set in environment"
        )
    
    fully_qualified_namespace = f"{namespace_name}.servicebus.windows.net"
    credential = DefaultAzureCredential()
    
    print(f"Connecting to Event Hub: {eventhub_name}")
    print(f"Consumer group: {consumer_group}")
    
    consumer = EventHubConsumerClient(
        fully_qualified_namespace=fully_qualified_namespace,
        eventhub_name=eventhub_name,
        consumer_group=consumer_group,
        credential=credential,
    )
    
    # Ensure checkpoint directory exists
    checkpoint_path = Path(checkpoint_dir)
    checkpoint_path.mkdir(parents=True, exist_ok=True)
    
    partitions_updated = 0
    total_events_skipped = 0
    
    with consumer:
        partition_ids = consumer.get_partition_ids()
        print(f"Found {len(partition_ids)} partition(s)")
        
        for partition_id in partition_ids:
            # Get partition properties to find the latest sequence number
            partition_props = consumer.get_partition_properties(partition_id)
            
            last_sequence_number = partition_props["last_enqueued_sequence_number"]
            last_offset = partition_props["last_enqueued_offset"]
            
            # Calculate events being skipped
            beginning_sequence = partition_props["beginning_sequence_number"]
            events_in_partition = max(0, last_sequence_number - beginning_sequence + 1)
            total_events_skipped += events_in_partition
            
            print(f"  Partition {partition_id}:")
            print(f"    Last sequence number: {last_sequence_number}")
            print(f"    Last offset: {last_offset}")
            print(f"    Events to skip: {events_in_partition}")
            
            # Save checkpoint to the latest position
            # Use same naming convention as LocalCheckpointStore
            safe_name = f"{eventhub_name}_{consumer_group}_{partition_id}".replace("/", "_").replace("$", "_")
            checkpoint_file = checkpoint_path / f"{safe_name}.json"
            
            with open(checkpoint_file, "w") as f:
                json.dump({
                    "offset": last_offset,
                    "sequence_number": last_sequence_number
                }, f)
            
            print(f"    Checkpoint updated: {checkpoint_file.name}")
            partitions_updated += 1
    
    return partitions_updated, total_events_skipped


def main():
    parser = argparse.ArgumentParser(
        description="Skip all existing events in Event Hub by updating checkpoints to latest position"
    )
    parser.add_argument(
        "--env-file",
        default="app.env",
        help="Path to environment file (default: app.env)",
    )
    parser.add_argument(
        "--consumer-group",
        default="$Default",
        help="Consumer group (default: $Default)",
    )
    parser.add_argument(
        "--checkpoint-dir",
        default=".checkpoints",
        help="Checkpoint directory (default: .checkpoints)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset checkpoints (delete them) so consumer reads from beginning",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Event Hub Clear Utility")
    print("=" * 60)
    
    if args.reset:
        # Reset mode: delete checkpoints to start from beginning
        print("\nMode: RESET (delete checkpoints, consumer will read from beginning)")
        print("\nClearing local checkpoints...")
        checkpoints_cleared = clear_checkpoints(args.checkpoint_dir)
        print(f"\nCleared {checkpoints_cleared} checkpoint file(s)")
        print("\nNext time the consumer runs, it will process all events from the beginning.")
    else:
        # Skip mode: set checkpoints to latest
        print("\nMode: SKIP (set checkpoints to latest, consumer will skip existing events)")
        print("\nUpdating checkpoints to latest position...")
        try:
            partitions_updated, events_skipped = set_checkpoints_to_latest(
                env_file=args.env_file,
                consumer_group=args.consumer_group,
                checkpoint_dir=args.checkpoint_dir,
            )
            print(f"\nUpdated {partitions_updated} partition checkpoint(s)")
            print(f"Total events that will be skipped: {events_skipped}")
            print("\nNext time the consumer runs, it will only process NEW events.")
        except Exception as e:
            print(f"\nError: {e}")
            raise
    
    print("=" * 60)


if __name__ == "__main__":
    main()
