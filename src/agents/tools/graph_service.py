import asyncio
import os
from typing import Any

from azure.identity import DefaultAzureCredential
from gremlin_python.driver import client, serializer
from gremlin_python.driver.protocol import GremlinServerError
from dotenv import load_dotenv


class GraphService:
    """Service class for querying the Azure Cosmos DB Gremlin graph."""

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

        self._credential = DefaultAzureCredential()
        self._client: client.Client | None = None

    @property
    def gremlin_client(self) -> client.Client:
        """Lazy initialization of the Gremlin client with Azure AD authentication."""
        if self._client is None:
            token = self._credential.get_token("https://cosmos.azure.com/.default")
            self._client = client.Client(
                url=self.endpoint,
                traversal_source="g",
                username=f"/dbs/{self.database}/colls/{self.graph}",
                password=token.token,
                message_serializer=serializer.GraphSONSerializersV2d0(),
            )
        return self._client

    def _reset_client(self) -> None:
        """Close and reset the client to force reconnection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    def _execute_query_sync(self, query: str) -> list[Any]:
        """Synchronous query execution."""
        try:
            result_set = self.gremlin_client.submit(query)
            return result_set.all().result()
        except GremlinServerError as e:
            error_str = str(e)
            # Handle token expiration by resetting client
            if "403" in error_str or "Forbidden" in error_str:
                self._reset_client()
            raise

    async def execute_query(self, query: str) -> list[Any]:
        """
        Execute a Gremlin query against the graph database.

        Args:
            query: Gremlin query string

        Returns:
            List of query results

        Raises:
            GremlinServerError: If the query fails
        """
        return await asyncio.to_thread(self._execute_query_sync, query)

    def close(self) -> None:
        """Close the Gremlin client connection."""
        self._reset_client()

    def __enter__(self) -> "GraphService":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
