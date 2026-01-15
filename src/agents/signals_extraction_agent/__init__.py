from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from pydantic import BaseModel


class Preferences(BaseModel):
    prefs: list[Preference]

class Preference(BaseModel):
    item_type: str # colour_group or article
    value: str # value of colour or article_id


PREFERENCE_EXTRACTION_PROMPT = """
Analyse this conversation and return all user preferences.
A preference is where the user expresses a like for:
- colour_group (red, orange, beige, etc)
- a product or article. article_ids will be found in the tool call responses.

If no clear signals exist, return None.

User message to analyze:
"""


agent = AzureOpenAIChatClient(
    credential=AzureCliCredential()
).create_agent(
    name="preference_extractor",
    instructions=PREFERENCE_EXTRACTION_PROMPT,
    response_format=Preferences
)

