"""
Base AI Provider Interface

Abstract base class that all AI providers must implement.
Ensures consistent interface across OpenAI, Anthropic, Google, etc.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any


class TradeDirection(str, Enum):
    """Trade direction."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class MarketContext:
    """
    Market context passed to AI for analysis.
    Contains all relevant information for making a trading decision.
    """
    symbol: str
    timeframe: str
    current_price: Decimal

    # Price data (optional - computed from current_price if not provided)
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    spread: Optional[Decimal] = None

    # Technical indicators
    indicators: Dict[str, Any] = field(default_factory=dict)

    # Historical candles
    candles: List[Dict[str, Any]] = field(default_factory=list)

    # Support/Resistance levels
    support_levels: List[Decimal] = field(default_factory=list)
    resistance_levels: List[Decimal] = field(default_factory=list)

    # Additional context
    news_sentiment: Optional[float] = None
    market_session: Optional[str] = None  # "London", "New York", "Tokyo", "Sydney"
    volatility: Optional[str] = None  # "low", "medium", "high"

    # Economic events
    economic_events: List[Dict[str, Any]] = field(default_factory=list)

    # Account context
    account_balance: Optional[Decimal] = None
    open_positions: List[Dict] = field(default_factory=list)

    # Timestamp
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Set default bid/ask/spread based on current_price if not provided."""
        if self.bid is None:
            self.bid = self.current_price
        if self.ask is None:
            self.ask = self.current_price
        if self.spread is None:
            self.spread = Decimal('0')

    def to_prompt_string(self) -> str:
        """Convert context to a string for AI prompt."""
        lines = [
            f"Symbol: {self.symbol}",
            f"Timeframe: {self.timeframe}",
            f"Current Price: {self.current_price}",
            f"Bid/Ask: {self.bid}/{self.ask} (Spread: {self.spread})",
            "",
            "=== TECHNICAL INDICATORS ===",
        ]

        for name, value in self.indicators.items():
            if isinstance(value, dict):
                lines.append(f"{name}:")
                for k, v in value.items():
                    lines.append(f"  - {k}: {v}")
            else:
                lines.append(f"{name}: {value}")

        lines.extend([
            "",
            f"Support Levels: {self.support_levels}",
            f"Resistance Levels: {self.resistance_levels}",
        ])

        if self.news_sentiment:
            lines.append(f"News Sentiment: {self.news_sentiment}")
        if self.market_session:
            lines.append(f"Market Session: {self.market_session}")
        if self.volatility:
            lines.append(f"Volatility: {self.volatility}")

        if self.open_positions:
            lines.append("")
            lines.append("=== OPEN POSITIONS ===")
            for pos in self.open_positions:
                lines.append(f"  {pos}")

        return "\n".join(lines)


@dataclass
class AIAnalysis:
    """
    Analysis result from a single AI provider.
    Each AI must return this structured response.
    """
    # Provider identification
    provider_name: str  # "openai", "anthropic", "google", etc.
    model_name: str  # "gpt-4o", "claude-sonnet", etc.

    # Trading decision
    direction: TradeDirection
    confidence: float  # 0-100

    # Price targets
    entry_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    risk_reward_ratio: Optional[float] = None

    # Reasoning
    reasoning: str = ""
    key_factors: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)

    # Timing
    suggested_timeframe: str = ""  # How long to hold
    urgency: str = "normal"  # "immediate", "normal", "wait"

    # Metadata
    processing_time_ms: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_response: Optional[str] = None

    # Error handling
    error: Optional[str] = None
    is_valid: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "entry_price": str(self.entry_price) if self.entry_price else None,
            "stop_loss": str(self.stop_loss) if self.stop_loss else None,
            "take_profit": str(self.take_profit) if self.take_profit else None,
            "reasoning": self.reasoning,
            "key_factors": self.key_factors,
            "risks": self.risks,
            "processing_time_ms": self.processing_time_ms,
        }


class BaseAIProvider(ABC):
    """
    Abstract base class for AI providers.

    All AI providers (OpenAI, Anthropic, etc.) must implement this interface.
    This ensures consistent behavior across different AI services.
    """

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        """
        Initialize the AI provider.

        Args:
            model_name: The specific model to use (e.g., "gpt-4o", "claude-sonnet")
            api_key: API key for the service (optional, can use env vars)
        """
        self.model_name = model_name
        self.api_key = api_key
        self._client = None

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g., 'openai', 'anthropic')."""
        pass

    @property
    @abstractmethod
    def supported_models(self) -> List[str]:
        """List of supported model names for this provider."""
        pass

    @property
    def cost_per_1k_input_tokens(self) -> float:
        """Cost per 1000 input tokens in USD."""
        return 0.0

    @property
    def cost_per_1k_output_tokens(self) -> float:
        """Cost per 1000 output tokens in USD."""
        return 0.0

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the client/connection."""
        pass

    @abstractmethod
    async def analyze(self, context: MarketContext) -> AIAnalysis:
        """
        Analyze market context and return trading recommendation.

        Args:
            context: Market context with indicators, prices, etc.

        Returns:
            AIAnalysis with trading recommendation
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available and working."""
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a request."""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input_tokens
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output_tokens
        return input_cost + output_cost

    def _create_error_response(self, error_message: str) -> AIAnalysis:
        """Create an error response."""
        return AIAnalysis(
            provider_name=self.provider_name,
            model_name=self.model_name,
            direction=TradeDirection.HOLD,
            confidence=0,
            reasoning=f"Error: {error_message}",
            error=error_message,
            is_valid=False,
        )

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
