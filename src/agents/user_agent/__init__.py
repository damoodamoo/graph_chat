from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

from src.agents.tools.graph_tool import GraphTool

graph_tool = GraphTool()
USER_ID = "0000757967448a6cb83efb3ea7a3fb9d418ac7adf2379d8cd0c725276a467a2a"


agent = AzureOpenAIChatClient(credential=AzureCliCredential()).create_agent(
    name="insight_agent",
    instructions=f"""
        This user is {USER_ID}. 
        Start by getting their details and past purchases, and summarising what they've bought.
        Summarise their sense of style and vibe based on their past purchses.
    """,
    tools=[graph_tool.get_user, graph_tool.get_latest_purchases]
)