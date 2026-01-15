from agent_framework import ContextProvider, Context, ChatMessage
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from collections.abc import MutableSequence, Sequence
from typing import Any
from logging import getLogger
import json

from src.agents.signals_extraction_agent import agent


class UserPreferenceSignalsMemory(ContextProvider):
    def __init__(self):
        self._preferences = {}
        self._conversation_history: list[ChatMessage] = []  # Accumulate full history

    async def invoking(self, messages: ChatMessage | MutableSequence[ChatMessage], **kwargs: Any) -> Context:
        # not interested in pushing context into the convo at this point
        return Context()

    async def invoked(
        self,
        request_messages: ChatMessage | Sequence[ChatMessage],
        response_messages: ChatMessage | Sequence[ChatMessage] | None = None,
        invoke_exception: Exception | None = None,
        **kwargs: Any,
    ) -> None:
        """Extract and store user preferences from the conversation."""
        
         # Normalize to list
        if isinstance(request_messages, ChatMessage):
            request_messages = [request_messages]
        if isinstance(response_messages, ChatMessage):
            response_messages = [response_messages]
        
        # Accumulate messages into full conversation history
        for m in request_messages:
            self._conversation_history.append(m)

        if response_messages:
            for m in response_messages:
                self._conversation_history.append(m)

        prefs = await agent.run(self._conversation_history)
        print(prefs)
        
        
