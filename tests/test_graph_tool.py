"""Integration test for GraphTool - calls real Cosmos DB."""

import pytest
from src.agents.tools.graph_tool import GraphTool


class TestGraphToolIntegration:
    """Integration tests that call real Cosmos DB."""

    @pytest.fixture
    def graph_tool(self):
        return GraphTool()

    @pytest.mark.asyncio
    async def test_get_user_returns_user(self, graph_tool):
        """Test getting a user that exists in the database."""
        # Use a known customer ID from your data
        user_id = "0000757967448a6cb83efb3ea7a3fb9d418ac7adf2379d8cd0c725276a467a2a"

        result = await graph_tool.get_user(user_id)

        assert result is not None
        assert result.customer_id == user_id
        print(f"Found user: {result}")

    @pytest.mark.asyncio
    async def test_get_user_not_found_returns_none(self, graph_tool):
        """Test getting a user that doesn't exist."""
        result = await graph_tool.get_user("nonexistent_user_12345")

        assert result is None


if __name__ == "__main__":
    # Run directly for quick testing
    import asyncio
    tool = GraphTool()
    user = asyncio.run(tool.get_user("0000423b620805d70a8d24a74265e620f2daeac8b3cb5b0450e19b1896789b07"))
    print(f"Result: {user}")
