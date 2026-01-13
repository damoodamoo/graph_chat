import os
import random
import time
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.core.credentials import AccessToken
from gremlin_python.driver import client, serializer
from gremlin_python.driver.protocol import GremlinServerError
from dotenv import load_dotenv

from src.ingestion.models.events import (
    Action,
    GraphEdgeEvent,
    GraphNodeEvent,
)


class GremlinService:
    """Service class for executing Gremlin queries against Cosmos DB."""

    # Retry configuration
    MAX_RETRIES = 5
    BASE_DELAY_SECONDS = 1.0
    MAX_DELAY_SECONDS = 32.0

    # Token refresh buffer - refresh token if it expires within this many seconds
    TOKEN_REFRESH_BUFFER_SECONDS = 300  # 5 minutes

    def __init__(self, env_file: str = "app.env"):
        load_dotenv(env_file)

        self.endpoint = os.getenv("COSMOSDB_GREMLIN_ENDPOINT")
        self.database = os.getenv("COSMOSDB_DATABASE_NAME")
        self.graph = os.getenv("COSMOSDB_GRAPH_NAME")

        if not all([self.endpoint, self.database, self.graph]):
            raise ValueError(
                "COSMOSDB_GREMLIN_ENDPOINT, COSMOSDB_DATABASE_NAME, "
                "and COSMOSDB_GRAPH_NAME must be set"
            )

        self._client: client.Client | None = None
        self._credential = DefaultAzureCredential()
        self._current_token: AccessToken | None = None

    def _get_access_token(self) -> str:
        """Get an access token for Cosmos DB Gremlin API."""
        token = self._credential.get_token("https://cosmos.azure.com/.default")
        self._current_token = token
        return token.token

    def _is_token_expired_or_expiring_soon(self) -> bool:
        """
        Check if the current token is expired or will expire soon.

        Returns:
            True if token is expired, expiring soon, or doesn't exist.
        """
        if self._current_token is None:
            return True

        current_time = datetime.now(timezone.utc).timestamp()
        # Token expires_on is a Unix timestamp
        time_until_expiry = self._current_token.expires_on - current_time

        return time_until_expiry < self.TOKEN_REFRESH_BUFFER_SECONDS

    def _refresh_client_if_needed(self) -> None:
        """
        Check if the token is expired or expiring soon and refresh the client if needed.

        This method closes the existing client and creates a new one with a fresh token.
        """
        if self._is_token_expired_or_expiring_soon():
            print("Token expired or expiring soon, refreshing...")
            self._close_client()
            # The next access to gremlin_client will create a new client with a fresh token

    @property
    def gremlin_client(self) -> client.Client:
        """Lazy initialization of the Gremlin client."""
        if self._client is None:
            self._client = client.Client(
                url=self.endpoint,
                traversal_source="g",
                username=f"/dbs/{self.database}/colls/{self.graph}",
                password=self._get_access_token(),
                message_serializer=serializer.GraphSONSerializersV2d0(),
            )
        return self._client

    def execute_query(self, query: str) -> list:
        """
        Execute a Gremlin query and return results.

        Implements exponential backoff retry for 429 (rate limit) errors.
        Automatically refreshes the access token if it has expired or is expiring soon.

        Args:
            query: Gremlin query string

        Returns:
            List of query results
        """
        # Check and refresh token before executing query
        self._refresh_client_if_needed()

        last_exception = None

        for attempt in range(self.MAX_RETRIES):
            try:
                result_set = self.gremlin_client.submit(query)
                return result_set.all().result()
            except GremlinServerError as e:
                error_str = str(e)

                # Check if this is an authentication/authorization error (401/403)
                if "401" in error_str or "Unauthorized" in error_str or "403" in error_str:
                    print("Authentication error detected, refreshing token...")
                    self._close_client()
                    if attempt < self.MAX_RETRIES - 1:
                        # Retry with a fresh token
                        continue
                    print(f"Authentication failed after token refresh: {e}")
                    raise

                # Check if this is a 429 rate limit error
                if "429" in error_str or "RequestRateTooLarge" in error_str:
                    last_exception = e
                    if attempt < self.MAX_RETRIES - 1:
                        # Calculate delay with exponential backoff and jitter
                        delay = min(
                            self.BASE_DELAY_SECONDS * (2 ** attempt) + random.uniform(0, 1),
                            self.MAX_DELAY_SECONDS,
                        )
                        print(
                            f"Rate limited (429), retrying in {delay:.2f}s "
                            f"(attempt {attempt + 1}/{self.MAX_RETRIES})"
                        )
                        time.sleep(delay)
                        continue
                # Not a 429 or out of retries, re-raise
                print(f"Gremlin error executing query: {e}")
                raise

        # If we exhausted all retries
        print(f"Failed after {self.MAX_RETRIES} retries due to rate limiting")
        raise last_exception

    def process_node_event(self, event: GraphNodeEvent) -> None:
        """
        Process a GraphNodeEvent by upserting or deleting the node.

        Args:
            event: The GraphNodeEvent to process
        """
        node_label = event.label
        node_type = event.node_type.value

        if event.action == Action.UPSERT:
            self._upsert_node(node_label, node_type, event.data)
        elif event.action == Action.DELETE:
            self._delete_node(node_label)

    def process_node_events_batch(self, events: list[GraphNodeEvent], batch_size: int = 50) -> None:
        """
        Process multiple GraphNodeEvents in batches using combined Gremlin queries.

        Groups events by action type and processes upserts in batches.
        Deletes are processed individually as they are typically fewer.

        Args:
            events: List of GraphNodeEvents to process
            batch_size: Maximum number of nodes per batch query (default 50)
        """
        if not events:
            return

        # Separate upserts and deletes
        upsert_events = [e for e in events if e.action == Action.UPSERT]
        delete_events = [e for e in events if e.action == Action.DELETE]

        # Process upserts in batches
        for i in range(0, len(upsert_events), batch_size):
            batch = upsert_events[i : i + batch_size]
            self._upsert_nodes_batch(batch)

        # Process deletes individually (typically fewer)
        for event in delete_events:
            self._delete_node(event.label)

    def _upsert_nodes_batch(self, events: list[GraphNodeEvent]) -> None:
        """
        Upsert multiple vertices in batched Gremlin queries.

        Cosmos DB Gremlin API has limitations on query complexity, so we
        execute individual upsert queries but group them for better organization
        and potential future optimization.

        Args:
            events: List of GraphNodeEvents to upsert
        """
        if not events:
            return

        # Execute upserts individually - Cosmos DB doesn't support union with V()
        for event in events:
            self._upsert_node(event.label, event.node_type.value, event.data)

    def process_edge_event(self, event: GraphEdgeEvent) -> None:
        """
        Process a GraphEdgeEvent by upserting or deleting the edge.

        Args:
            event: The GraphEdgeEvent to process
        """
        if event.action == Action.UPSERT:
            self._upsert_edge(event)
        elif event.action == Action.DELETE:
            self._delete_edge(event)

    def _upsert_node(self, label: str, node_type: str, data: dict) -> None:
        """
        Upsert a vertex in the graph.

        Uses coalesce pattern to update if exists, otherwise create.
        """
        # Build property assignments for the query
        properties = self._build_property_string(data, exclude_keys=["id", "partitionKey"])

        query = (
            f"g.V('{self._escape(label)}').has('label', '{self._escape(label)}')"
            f".fold()"
            f".coalesce("
            f"  unfold(){properties},"
            f"  addV('{self._escape(label)}').property('id', '{self._escape(label)}').property('partitionKey', '{self._escape(node_type)}'){properties}"
            f")"
        )

        self.execute_query(query)

    def _delete_node(self, label: str) -> None:
        """Delete a vertex from the graph."""
        query = f"g.V('{self._escape(label)}').has('label', '{self._escape(label)}').drop()"
        self.execute_query(query)

    def _upsert_edge(self, event: GraphEdgeEvent) -> None:
        """
        Upsert an edge in the graph.

        Creates source/target vertices if they don't exist, then creates the edge.
        """
        source_id = event.source_node_id
        source_pk = event.source_node_type.value
        target_id = event.target_node_id
        target_pk = event.target_node_type.value
        edge_label = event.edge_type.value

        properties = self._build_property_string(event.data)

        # Ensure source vertex exists
        self.execute_query(
            f"g.V('{self._escape(source_id)}')"
            f".fold()"
            f".coalesce(unfold(), addV('{self._escape(source_pk)}').property('id', '{self._escape(source_id)}').property('partitionKey', '{self._escape(source_pk)}'))"
        )

        # Ensure target vertex exists
        self.execute_query(
            f"g.V('{self._escape(target_id)}')"
            f".fold()"
            f".coalesce(unfold(), addV('{self._escape(target_pk)}').property('id', '{self._escape(target_id)}').property('partitionKey', '{self._escape(target_pk)}'))"
        )

        # Upsert the edge using coalesce pattern
        query = (
            f"g.V('{self._escape(source_id)}')"
            f".outE('{self._escape(edge_label)}').where(inV().has('id', '{self._escape(target_id)}'))"
            f".fold()"
            f".coalesce("
            f"  unfold(){properties},"
            f"  g.V('{self._escape(source_id)}').addE('{self._escape(edge_label)}').to(g.V('{self._escape(target_id)}')){properties}"
            f")"
        )

        self.execute_query(query)

    def _delete_edge(self, event: GraphEdgeEvent) -> None:
        """Delete an edge from the graph."""
        source_id = event.source_node_id
        target_id = event.target_node_id
        edge_label = event.edge_type.value

        query = (
            f"g.V('{self._escape(source_id)}')"
            f".outE('{self._escape(edge_label)}')"
            f".where(inV().has('id', '{self._escape(target_id)}'))"
            f".drop()"
        )

        self.execute_query(query)

    def _build_property_string(self, data: dict, exclude_keys: list[str] | None = None) -> str:
        """
        Build a Gremlin property string from a dictionary.

        Args:
            data: Dictionary of properties
            exclude_keys: Keys to exclude from the property string

        Returns:
            Gremlin property string like ".property('key', 'value')"
        """
        if not data:
            return ""

        exclude_keys = exclude_keys or []
        parts = []

        for key, value in data.items():
            if key in exclude_keys:
                continue
            if value is None:
                continue

            escaped_key = self._escape(str(key))
            escaped_value = self._escape(str(value))
            parts.append(f".property('{escaped_key}', '{escaped_value}')")

        return "".join(parts)

    @staticmethod
    def _escape(value: str) -> str:
        """Escape special characters for Gremlin query strings."""
        return value.replace("\\", "\\\\").replace("'", "\\'")

    def _close_client(self) -> None:
        """Close the Gremlin client connection without additional cleanup."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                print(f"Warning: Error closing Gremlin client: {e}")
            self._client = None

    def close(self) -> None:
        """Close the Gremlin client connection."""
        self._close_client()

    def __enter__(self) -> "GremlinService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
