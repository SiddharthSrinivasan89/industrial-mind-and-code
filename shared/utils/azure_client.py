"""
Industrial Mind & Code - Azure OpenAI Client
Shared client for all IM&C experiments.
"""

import os
from openai import AzureOpenAI


def get_azure_client() -> AzureOpenAI:
    """Create Azure OpenAI client from .env variables."""
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
    )


def call_agent(client, system_prompt, user_message,
               temperature=0.7, max_tokens=4096,
               response_format=None):
    """Single-turn agent call."""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
kwargs = {
        "model": deployment,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content


def call_agent_multi_turn(client, system_prompt, messages,
                          temperature=0.7, max_tokens=4096):
    """Multi-turn agent call with full conversation history."""
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    response = client.chat.completions.create(
        model=deployment,
        messages=full_messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content
