"""Azure OpenAI Client Wrapper with automatic metrics tracking"""

import os
import time
from typing import Tuple, Dict, Optional
from openai import AzureOpenAI
from dotenv import load_dotenv


class AzureOpenAIClient:
    """Wrapper for Azure OpenAI API calls with automatic timing and token tracking"""
    
    def __init__(self):
        load_dotenv()
        
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_KEY")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
        
        if not all([self.endpoint, self.api_key, self.deployment]):
            raise ValueError(
                "Missing required environment variables. "
                "Please set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, and AZURE_OPENAI_DEPLOYMENT"
            )
        
        self.client = AzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version="2024-02-01"
        )
    
    def chat(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Tuple[str, Dict[str, int]]:
        """
        Send a chat completion request to Azure OpenAI
        
        Args:
            prompt: The user prompt
            system_message: Optional system message
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response
            
        Returns:
            Tuple of (response_text, metrics_dict)
            metrics_dict contains: latency_ms, prompt_tokens, completion_tokens, total_tokens
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        start_time = time.time()
        
        response = self.client.chat.completions.create(
            model=self.deployment,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)
        
        response_text = response.choices[0].message.content
        
        metrics = {
            "latency_ms": latency_ms,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        
        return response_text, metrics
