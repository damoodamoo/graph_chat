from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential

from src.agents.tools.graph_tool import GraphTool
from src.agents.memory.preference_signals import UserPreferenceSignalsMemory
from src.config import USER_ID

graph_tool = GraphTool()
signals_memory = UserPreferenceSignalsMemory()


agent = AzureOpenAIChatClient(credential=AzureCliCredential()).create_agent(
    name="user_agent",
    instructions=f"""
        This user is {USER_ID}. 
        You are a fashion stylist. Help this customer with their questions and recommend relevant items where possible.
        They might want to get new ideas of products they might like - if so, use the inspire_me tool.
        They might want ideas about similar products - use the recommend_similar tool.
        For each tool call you will be given more data than you need to show. From the response, select only the 3 most relevant items based on the converstion the user has had with you. Select a variety of items.
        Throughout the conversation, the customer will give preference signals to you. These will be extracted for storage later on.
        Each time you get data from a tool, make sure to apply the conversation to the results to ensure the most relevant part is highlighted.
        Do **not** talk about products that have not come from tool calls. Only discuss products that have been returned from the database.
    """,
    tools=[
        graph_tool.get_user, 
        graph_tool.get_latest_purchases,
        graph_tool.inspire_me,
        graph_tool.recommend_similar
    ],
    context_providers=[signals_memory]
)
