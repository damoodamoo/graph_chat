"""Integration test for GraphTool - calls real Cosmos DB."""

import pytest
from src.agents.tools.graph_tool import GraphTool
from src.config import USER_ID


@pytest.mark.integration
class TestGraphToolIntegration:
    """Integration tests that call real Cosmos DB.
    
    These tests require CosmosDB credentials and are skipped in CI.
    Run locally with: pytest tests/test_graph_tool.py -v -m integration
    """

    @pytest.fixture
    def graph_tool(self):
        return GraphTool()

    @pytest.mark.asyncio
    async def test_get_user_returns_user(self, graph_tool):
        """Test getting a user that exists in the database."""
        # Use a known customer ID from your data
        result = await graph_tool.get_user(USER_ID)

        assert result is not None
        assert result.customer_id == USER_ID
        print(f"Found user: {result}")

    @pytest.mark.asyncio
    async def test_get_user_not_found_returns_none(self, graph_tool):
        """Test getting a user that doesn't exist."""
        result = await graph_tool.get_user("nonexistent_user_12345")

        assert result is None
