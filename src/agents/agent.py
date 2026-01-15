import asyncio
from functools import partial
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from agent_framework.devui import serve

from src.agents.tools.graph_tool import GraphTool

from dotenv import load_dotenv

load_dotenv('app.env')

graph_tool = GraphTool()
