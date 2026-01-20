"""
AI Providers Module

All available AI providers for market analysis.
"""

from .aiml_provider import AIMLProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider
from .groq_provider import GroqProvider
from .mistral_provider import MistralProvider
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "AIMLProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "GroqProvider",
    "MistralProvider",
    "OllamaProvider",
]

# Provider registry for easy access
PROVIDERS = {
    "aiml": AIMLProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "groq": GroqProvider,
    "mistral": MistralProvider,
    "ollama": OllamaProvider,
}
