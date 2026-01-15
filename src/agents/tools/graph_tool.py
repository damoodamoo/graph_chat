from typing import Annotated, Any

from src.agents.models.models import Article, User
from src.agents.tools.graph_service import GraphService


class GraphTool:
    """Tool for retrieving nodes from the graph database."""

    def __init__(self, graph_service: GraphService | None = None):
        self._graph_service = graph_service or GraphService()

    async def get_user(
        self,
        user_id: Annotated[str, "The unique customer ID to look up in the graph"],
    ) -> User | None:
        """
        Retrieve a user node by customer ID.

        Args:
            user_id: The customer ID to look up

        Returns:
            User model with age, club_member_status, fashion_news_frequency,
            or None if not found
        """
        query = f"g.V().has('id', '{user_id}').valueMap(true)"

        results = await self._graph_service.execute_query(query)

        print(results)

        if not results:
            return None

        node = self._parse_node(results[0])
        return User(
            customer_id=node.get("name", user_id),
            age=node.get("age"),
            club_member_status=node.get("club_member_status"),
            fashion_news_frequency=node.get("fashion_news_frequency"),
        )

    async def get_product(self, product_id: str) -> dict[str, Any] | None:
        """
        Retrieve a product (article) node by article ID.

        Args:
            product_id: The article ID to look up

        Returns:
            Product node data including product details like name, type, colour, etc.,
            or None if not found
        """
        query = f"g.V().has('product', 'name', '{product_id}').valueMap(true)"
        results = await self._graph_service.execute_query(query)

        if not results:
            return None

        return self._parse_node(results[0])

    def _parse_node(self, node: dict[str, Any]) -> dict[str, Any]:
        """
        Parse a Gremlin node result into a flat dictionary.

        Gremlin returns property values as lists, so this extracts single values.
        """
        parsed = {}
        for key, value in node.items():
            if isinstance(value, list) and len(value) == 1:
                parsed[key] = value[0]
            else:
                parsed[key] = value
        return parsed

    async def get_latest_purchases(
        self,
        user_id: Annotated[str, "The unique customer ID to look up in the graph"],
        limit: Annotated[int, "Maximum number of purchased products to return"] = 5,
    ) -> list[Article]:
        """
        Retrieve the latest purchased products for a user.

        Args:
            user_id: The customer ID to look up
            limit: Maximum number of products to return (default: 5)

        Returns:
            List of Article models representing purchased products
        """
        query = (
            f"g.V().has('id', '{user_id}')"
            f".out('purchased')"
            f".limit({limit})"
            f".valueMap(true)"
        )

        results = await self._graph_service.execute_query(query)

        if not results:
            return []

        articles = []
        for result in results:
            node = self._parse_node(result)
            article = Article(
                article_id=node.get("name", node.get("id", "")),
                product_code=node.get("product_code"),
                prod_name=node.get("prod_name"),
                detail_desc=node.get("detail_desc"),
            )
            articles.append(article)

        return articles

    async def execute_gremlin_query(
        self,
        query: Annotated[str, "The Gremlin query to execute against the graph database"],
    ) -> list[dict[str, Any]]:
        """
        Execute a Gremlin query and return the results.

        Args:
            query: A valid Gremlin query string

        Returns:
            List of results from the query, with node properties parsed
        """
        results = await self._graph_service.execute_query(query)

        if not results:
            return []

        # Parse results if they're node/edge data
        parsed_results = []
        for result in results:
            if isinstance(result, dict):
                parsed_results.append(self._parse_node(result))
            else:
                parsed_results.append(result)

        return parsed_results
