from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from pathlib import Path

from src.agents.tools.graph_tool import GraphTool
from src.config import USER_ID

graph_tool = GraphTool()

_schema_path = Path(__file__).parent.parent.parent.parent / "docs" / "graph-schema.md"
with open(_schema_path, "r") as f:
    GRAPH_SCHEMA = f.read()

# Agent for natural language to Gremlin queries
agent = AzureOpenAIChatClient(credential=AzureCliCredential()).create_agent(
    name="dynamic_query_agent",
    instructions=f"""
        You are a graph database query assistant. You translate natural language questions 
        into Gremlin queries and execute them against an Azure Cosmos DB Gremlin database.
        
        The current user context is: {USER_ID}
        
        {GRAPH_SCHEMA}
        
        When the user asks a question:
        1. Understand what data they're looking for
        2. Construct a valid Gremlin query based on the schema above
        3. Execute the query using the execute_gremlin_query tool
        4. Present the results in a clear, readable format
        
        Always use .valueMap(true) when returning node properties.
        Limit results to avoid overwhelming output (use .limit(10) by default).
    """,
    tools=[graph_tool.execute_gremlin_query]
)