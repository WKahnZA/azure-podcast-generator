"""Module for LLM utils."""

import json
import os
from dataclasses import dataclass

import streamlit as st
import tiktoken
from openai import AzureOpenAI
from openai.types import CompletionUsage
from utils.identity import get_token_provider

PROMPT = """
Create a highly engaging podcast script named '{title}' between two people based on the input text. Use informal language to enhance the human-like quality of the conversation, including expressions like \"wow,\" laughter, and pauses such as \"uhm.\"

# Steps

1. **Review the Document(s) and Podcast Title**: Understand the main themes, key points, and tone.
2. **Character Development**: Define two distinct personalities for the hosts.
3. **Script Structure**: Outline the introduction, main discussion, and conclusion.
4. **Incorporate Informal Language**: Use expressions and fillers to create a natural dialogue flow.
5. **Engage with Humor and Emotion**: Include laughter and emotional responses to make the conversation lively.

# Output Format

- A conversational podcast script in structured JSON.
- Include informal expressions and pauses.
- Clearly mark speaker turns.
- Name the hosts Andrew and Emma.

# Examples

**Input:**
- Document: [Brief overview of the content, main themes, or key points]
- Podcast Title: \"Exploring the Wonders of Space\"

**Output:**
- Speaker 1: \"Hey everyone, welcome to 'Exploring the Wonders of Space!' I'm [Name], and with me is [Name].\"
- Speaker 2: \"Hey! Uhm, I'm super excited about today's topic. Did you see the latest on the new satellite launch?\"
- Speaker 1: \"Wow, yes! It's incredible. I mean, imagine the data we'll get! [laughter]\"
- (Continue with discussion, incorporating humor and informal language)

# Notes

- Maintain a balance between informal language and clear communication.
- Ensure the conversation is coherent and follows a logical progression.
- Adapt the style and tone based on the document's content and podcast title.
- Think step by step, grasp the key points of the document / paper, and explain them in a conversational tone.
- Make sure the conversation will take about 5 minutes to read out loud.
""".strip()

JSON_SCHEMA = {
    "name": "podcast",
    "strict": True,
    "description": "An AI generated podcast script.",
    "schema": {
        "type": "object",
        "properties": {
            "config": {
                "type": "object",
                "properties": {
                    "language": {
                        "type": "string",
                        "description": "Language code + locale (BCP-47), e.g. en-US or es-PA",
                    }
                },
                "required": ["language"],
                "additionalProperties": False,
            },
            "script": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name of the host in lower-case",
                        },
                        "message": {"type": "string"},
                    },
                    "required": ["name", "message"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["config", "script"],
        "additionalProperties": False,
    },
}


@dataclass
class PodcastScriptResponse:
    podcast: dict
    usage: CompletionUsage


def document_to_podcast_script(
    document: str, title: str = "AI in Action"
) -> PodcastScriptResponse:
    """Get LLM response."""

    if os.getenv("AZURE_OPENAI_KEY"):
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-09-01-preview",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )
    else:
        client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version="2024-09-01-preview",
            azure_ad_token_provider=get_token_provider(),
        )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": PROMPT.format(title=title),
            },
            # Wrap the document in <documents> tag for Prompt Shield Indirect attacks
            # https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/content-filter?tabs=warning%2Cindirect%2Cpython-new#embedding-documents-in-your-prompt
            {
                "role": "user",
                "content": f"<documents>{document}</documents>",
            },
        ],
        model=os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT", "gpt-4o"),
        temperature=0.7,
        response_format={"type": "json_schema", "json_schema": JSON_SCHEMA},
        max_tokens=8000,
    )

    message = chat_completion.choices[0].message.content
    json_message = json.loads(message)

    return PodcastScriptResponse(podcast=json_message, usage=chat_completion.usage)


@st.cache_resource
def get_encoding() -> tiktoken.Encoding:
    """Get TikToken."""
    encoding = tiktoken.encoding_for_model("gpt-4o")

    return encoding