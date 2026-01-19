from agent_framework import ContextProvider, Context, ChatMessage
from collections.abc import MutableSequence, Sequence
from typing import Any

from src.agents.signals_extraction_agent import agent
from src.agents.models.models import Preferences
from src.agents.tools.event_hub_tool import EventHubTool
from src.config import USER_ID

event_hub_tool = EventHubTool(customer_id=USER_ID)

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

        r = await agent.run(self._conversation_history)
        prefs = r.value
        print(prefs)
        event_hub_tool.send_preferences(prefs)
        
        
