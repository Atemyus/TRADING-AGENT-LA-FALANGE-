"""
AI Engine Module

Multi-model AI analysis with consensus-based decision making.
"""

from .base_ai import (
    AIAnalysis,
    BaseAIProvider,
    MarketContext,
    TradeDirection,
)
from .consensus_engine import (
    AgreementLevel,
    ConsensusEngine,
    ConsensusMethod,
    ConsensusResult,
    ProviderVote,
    create_consensus_engine,
)
from .providers import (
    PROVIDERS,
    AIMLProvider,
    AnthropicProvider,
    GoogleProvider,
    GroqProvider,
    MistralProvider,
    OllamaProvider,
    OpenAIProvider,
)

__all__ = [
    # Base
    "AIAnalysis",
    "BaseAIProvider",
    "MarketContext",
    "TradeDirection",
    # Consensus
    "AgreementLevel",
    "ConsensusEngine",
    "ConsensusMethod",
    "ConsensusResult",
    "ProviderVote",
    "create_consensus_engine",
    # Providers
    "AIMLProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "GroqProvider",
    "MistralProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "PROVIDERS",
]
