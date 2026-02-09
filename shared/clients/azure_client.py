"""
Azure OpenAI Client Utilities for Industrial Mind & Code
Provides centralized client initialization and agent calling functions.
"""

import os
from openai import AzureOpenAI

def get_azure_client():
    """
    Initialize and return an Azure OpenAI client using environment variables.
    Expects: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_API_VERSION
    """
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not endpoint or not api_key:
        raise ValueError("Missing required Azure OpenAI credentials in environment variables")
    
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=api_version
    )
    
    return client

def call_agent(client, system_prompt, user_prompt, model=None, response_format=None):
    """
    Call Azure OpenAI with system and user prompts.
    Returns the assistant's message content.
    """
    if model is None:
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    kwargs = {
        "model": model,
        "messages": messages
    }
    
    if response_format:
        kwargs["response_format"] = response_format
    
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content
