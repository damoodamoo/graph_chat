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

    async def get_product(self, article_id: str) -> dict[str, Any] | None:
        """
        Retrieve a product (article) node by article ID.

        Args:
            article_id: The article ID to look up

        Returns:
            Product node data including product details like name, type, colour, etc.,
            or None if not found
        """
        query = f"g.V().has('product', 'name', '{article_id}').valueMap(true)"
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

    async def recommend_similar(
        self,
        article_id: Annotated[str, "The article ID to find similar items for"],
        limit: Annotated[int, "Maximum number of similar articles to return"] = 10,
    ) -> list[Article]:
        """
        Find similar articles based on graph traversal.

        Traverses the graph to find articles that share the same product type
        or colour group as the given article.

        Args:
            article_id: The article ID to find similar items for
            limit: Maximum number of similar articles to return (default: 3, max: 3)

        Returns:
            List of Article models representing similar products
        """
        # Limit to max 3 suggestions
        limit = min(limit, 10)

        # Find articles that share the same product or colour group
        # by traversing: article -> belongs_to -> (product/colour_group) <- belongs_to <- other articles
        query = (
            f"g.V().has('article', 'name', '{article_id}')"
            f".out('belongs_to')"  # Go to product or colour_group
            f".in('belongs_to')"  # Find other articles in same category
            f".hasLabel('article')"  # Only get articles
            f".where(__.has('name', neq('{article_id}')))"  # Exclude the original article
            f".dedup()"  # Remove duplicates
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

    async def inspire_me(
        self,
        user_id: Annotated[str, "The customer ID to get inspiration for"],
        limit: Annotated[int, "Maximum number of suggested articles to return"] = 10,
    ) -> list[Article]:
        """
        Get product inspiration by finding what similar users have purchased.

        Traverses the graph to find users who bought the same items as the given user,
        then suggests the most popular items those similar users have bought.

        Args:
            user_id: The customer ID to get inspiration for
            limit: Maximum number of suggested articles to return (default: 3, max: 3)

        Returns:
            List of Article models representing popular items from similar users
        """
        # Limit to max 3 suggestions
        limit = min(limit, 10)

        # Find similar users by traversing:
        # user -> purchased -> article <- purchased <- similar users -> purchased -> their other articles
        # Group by article and order by popularity (how many similar users bought it)
        query = (
            f"g.V().has('user', 'name', '{user_id}')"
            f".out('purchased')"  # Articles this user purchased
            f".in('purchased')"  # Other users who purchased same articles
            f".hasLabel('user')"
            f".where(__.has('name', neq('{user_id}')))"  # Exclude the original user
            f".out('purchased')"  # Articles those similar users purchased
            f".where(__.in('purchased').has('name', '{user_id}').count().is(0))"  # Exclude articles user already bought
            f".groupCount()"  # Count popularity
            f".order(local).by(values, decr)"  # Order by popularity descending
            f".limit(local, {limit})"  # Limit results
            f".select(keys)"  # Get the article vertices
            f".unfold()"
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
