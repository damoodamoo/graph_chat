import os
import random
import time

from azure.identity import DefaultAzureCredential
from gremlin_python.driver import client, serializer
from gremlin_python.driver.protocol import GremlinServerError
from dotenv import load_dotenv

from src.models.events import (
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

    def _get_access_token(self) -> str:
        """Get an access token for Cosmos DB Gremlin API."""
        token = self._credential.get_token("https://cosmos.azure.com/.default")
        return token.token

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

        Args:
            query: Gremlin query string

        Returns:
            List of query results
        """
        last_exception = None

        for attempt in range(self.MAX_RETRIES):
            try:
                result_set = self.gremlin_client.submit(query)
                return result_set.all().result()
            except GremlinServerError as e:
                # Check if this is a 429 rate limit error
                if "429" in str(e) or "RequestRateTooLarge" in str(e):
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

    def close(self) -> None:
        """Close the Gremlin client connection."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> "GremlinService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
