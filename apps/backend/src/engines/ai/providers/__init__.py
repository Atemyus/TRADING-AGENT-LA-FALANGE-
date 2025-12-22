"""
AI Providers Module

All available AI providers for market analysis.
"""

from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .groq_provider import GroqProvider
from .mistral_provider import MistralProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "GroqProvider",
    "MistralProvider",
    "OllamaProvider",
]

# Provider registry for easy access
PROVIDERS = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "ollama": OllamaProvider,
}
