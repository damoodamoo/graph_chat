"""Central configuration for the graph_chat application."""

import os
from dotenv import load_dotenv

# Load environment variables from app.env file if present
# load_dotenv gracefully handles missing files (returns False without error)
load_dotenv("app.env")

# Default USER_ID for the application
DEFAULT_USER_ID = "0000757967448a6cb83efb3ea7a3fb9d418ac7adf2379d8cd0c725276a467a2a"

# USER_ID can be overridden via environment variable for testing/development
USER_ID = os.getenv("USER_ID", DEFAULT_USER_ID)
