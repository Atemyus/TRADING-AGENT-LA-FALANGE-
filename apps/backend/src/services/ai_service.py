"""
AI Service Orchestrator

Orchestrates multiple AI providers to run analysis in parallel
and produces consensus-based trading decisions.

Integrates with MarketDataService for real OHLCV data
and TechnicalAnalysisService for indicators and SMC analysis.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Type

from src.core.config import settings
from src.engines.ai.base_ai import AIAnalysis, BaseAIProvider, MarketContext, TradeDirection
from src.engines.ai.consensus_engine import (
    ConsensusEngine,
    ConsensusMethod,
    ConsensusResult,
    create_consensus_engine,
)
from src.engines.ai.providers import (
    AIMLProvider,
    AnthropicProvider,
    GoogleProvider,
    GroqProvider,
    MistralProvider,
    OllamaProvider,
    OpenAIProvider,
)
from src.services.market_data_service import get_market_data_service, MarketData
from src.services.technical_analysis_service import get_technical_analysis_service, FullAnalysis


@dataclass
class ProviderConfig:
    """Configuration for an AI provider."""
    provider_class: Type[BaseAIProvider]
    model_name: str
    enabled: bool = True
    weight: float = 1.0
    api_key: Optional[str] = None
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AIServiceConfig:
    """Configuration for the AI Service."""
    # Consensus settings
    consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED
    min_confidence_threshold: float = 50.0
    min_agreement_threshold: float = 0.6
    require_risk_reward: bool = True
    min_risk_reward: float = 1.5

    # Execution settings
    parallel_execution: bool = True
    timeout_seconds: float = 60.0
    retry_failed: bool = True
    max_retries: int = 2

    # Provider settings
    providers: List[ProviderConfig] = field(default_factory=list)


# Default provider configurations - AIML API with 6 models
# All models accessed via api.aimlapi.com with single API key
# Model IDs verified from https://docs.aimlapi.com/api-references/model-database
DEFAULT_PROVIDERS = [
    # ChatGPT 5.2 (OpenAI via AIML)
    ProviderConfig(
        provider_class=AIMLProvider,
        model_name="chatgpt-5.2",
        weight=1.0,
    ),
    # Gemini 3 Pro Preview (Google via AIML)
    ProviderConfig(
        provider_class=AIMLProvider,
        model_name="gemini-3-pro",
        weight=1.0,
    ),
    # DeepSeek V3.2 (DeepSeek via AIML)
    ProviderConfig(
        provider_class=AIMLProvider,
        model_name="deepseek-v3.2",
        weight=1.0,
    ),
    # Grok 4.1 Fast (xAI via AIML)
    ProviderConfig(
        provider_class=AIMLProvider,
        model_name="grok-4.1-fast",
        weight=1.0,
    ),
    # Qwen Max (Alibaba via AIML)
    ProviderConfig(
        provider_class=AIMLProvider,
        model_name="qwen-max",
        weight=1.0,
    ),
    # GLM 4.5 Air (Zhipu via AIML)
    ProviderConfig(
        provider_class=AIMLProvider,
        model_name="glm-4.5",
        weight=1.0,
    ),
]


class AIService:
    """
    AI Service Orchestrator

    Manages multiple AI providers, runs them in parallel,
    and produces consensus-based trading decisions.
    """

    def __init__(self, config: Optional[AIServiceConfig] = None):
        """
        Initialize AI Service.

        Args:
            config: Service configuration. Uses defaults if not provided.
        """
        self.config = config or AIServiceConfig()

        # Use default providers if none configured
        if not self.config.providers:
            self.config.providers = DEFAULT_PROVIDERS

        # Initialize consensus engine FIRST (needed by _initialize_providers)
        self._consensus_engine = create_consensus_engine(
            method=self.config.consensus_method.value,
            min_confidence_threshold=self.config.min_confidence_threshold,
            min_agreement_threshold=self.config.min_agreement_threshold,
            require_risk_reward=self.config.require_risk_reward,
            min_risk_reward=self.config.min_risk_reward,
        )

        # Initialize providers (uses _consensus_engine)
        self._providers: Dict[str, BaseAIProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize enabled AI providers."""
        for provider_config in self.config.providers:
            if not provider_config.enabled:
                continue

            try:
                # Create provider instance
                provider = provider_config.provider_class(
                    model_name=provider_config.model_name,
                    api_key=provider_config.api_key,
                    **provider_config.extra_config,
                )

                # Set weight in consensus engine
                self._consensus_engine.set_provider_weight(
                    provider.provider_name,
                    provider_config.weight,
                )

                # Store provider with unique key
                key = f"{provider.provider_name}_{provider_config.model_name}"
                self._providers[key] = provider

            except Exception as e:
                print(f"Failed to initialize provider {provider_config.model_name}: {e}")

    @property
    def provider_count(self) -> int:
        """Get number of active providers."""
        return len(self._providers)

    @property
    def provider_names(self) -> List[str]:
        """Get list of active provider names."""
        return list(self._providers.keys())

    async def health_check(self) -> Dict[str, bool]:
        """Check health of all providers."""
        results = {}

        async def check_provider(key: str, provider: BaseAIProvider) -> Tuple[str, bool]:
            try:
                healthy = await provider.health_check()
                return key, healthy
            except Exception:
                return key, False

        tasks = [
            check_provider(key, provider)
            for key, provider in self._providers.items()
        ]

        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, tuple):
                key, healthy = result
                results[key] = healthy
            else:
                # Exception occurred
                pass

        return results

    async def analyze(
        self,
        context: MarketContext,
        providers: Optional[List[str]] = None,
        mode: str = "standard",
        trading_style: str = "intraday",
    ) -> ConsensusResult:
        """
        Run analysis across all (or selected) AI providers.

        Args:
            context: Market context with all relevant data
            providers: Optional list of provider keys to use.
                      Uses all if not specified.
            mode: Analysis mode - "quick", "standard", or "premium"
            trading_style: Trading style - "scalping", "intraday", or "swing"

        Returns:
            ConsensusResult with aggregated decision
        """
        # Select providers
        if providers:
            selected = {k: v for k, v in self._providers.items() if k in providers}
        else:
            selected = self._providers

        if not selected:
            raise ValueError("No providers available for analysis")

        # Run analyses
        if self.config.parallel_execution:
            analyses = await self._run_parallel(context, selected, mode, trading_style)
        else:
            analyses = await self._run_sequential(context, selected, mode, trading_style)

        # Calculate consensus
        result = self._consensus_engine.calculate_consensus(analyses)

        return result

    async def _run_parallel(
        self,
        context: MarketContext,
        providers: Dict[str, BaseAIProvider],
        mode: str = "standard",
        trading_style: str = "intraday",
    ) -> List[AIAnalysis]:
        """Run all providers in parallel."""

        async def analyze_with_provider(
            key: str, provider: BaseAIProvider
        ) -> AIAnalysis:
            try:
                # Check if provider supports mode parameter
                if hasattr(provider, 'analyze') and 'mode' in provider.analyze.__code__.co_varnames:
                    return await asyncio.wait_for(
                        provider.analyze(context, mode=mode, trading_style=trading_style),
                        timeout=self.config.timeout_seconds,
                    )
                else:
                    return await asyncio.wait_for(
                        provider.analyze(context),
                        timeout=self.config.timeout_seconds,
                    )
            except asyncio.TimeoutError:
                return AIAnalysis(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    direction=TradeDirection.HOLD,
                    confidence=0,
                    reasoning=f"Error: Timeout after {self.config.timeout_seconds}s",
                    key_factors=[],
                    risks=[],
                )
            except Exception as e:
                return AIAnalysis(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    direction=TradeDirection.HOLD,
                    confidence=0,
                    reasoning=f"Error: {str(e)}",
                    key_factors=[],
                    risks=[],
                )

        tasks = [
            analyze_with_provider(key, provider)
            for key, provider in providers.items()
        ]

        analyses = await asyncio.gather(*tasks)

        # Retry failed if configured
        if self.config.retry_failed:
            failed_indices = [
                i for i, a in enumerate(analyses)
                if a.reasoning.startswith("Error:")
            ]

            for attempt in range(self.config.max_retries):
                if not failed_indices:
                    break

                retry_tasks = [
                    analyze_with_provider(
                        list(providers.keys())[i],
                        list(providers.values())[i],
                    )
                    for i in failed_indices
                ]

                retry_results = await asyncio.gather(*retry_tasks)

                # Update analyses with successful retries
                new_failed = []
                for idx, (orig_idx, result) in enumerate(zip(failed_indices, retry_results)):
                    if not result.reasoning.startswith("Error:"):
                        analyses[orig_idx] = result
                    else:
                        new_failed.append(orig_idx)

                failed_indices = new_failed

        return list(analyses)

    async def _run_sequential(
        self,
        context: MarketContext,
        providers: Dict[str, BaseAIProvider],
        mode: str = "standard",
        trading_style: str = "intraday",
    ) -> List[AIAnalysis]:
        """Run providers sequentially."""
        analyses = []

        for key, provider in providers.items():
            try:
                # Check if provider supports mode parameter
                if hasattr(provider, 'analyze') and 'mode' in provider.analyze.__code__.co_varnames:
                    analysis = await asyncio.wait_for(
                        provider.analyze(context, mode=mode, trading_style=trading_style),
                        timeout=self.config.timeout_seconds,
                    )
                else:
                    analysis = await asyncio.wait_for(
                        provider.analyze(context),
                        timeout=self.config.timeout_seconds,
                    )
                analyses.append(analysis)
            except Exception as e:
                analyses.append(AIAnalysis(
                    provider_name=provider.provider_name,
                    model_name=provider.model_name,
                    direction=TradeDirection.HOLD,
                    confidence=0,
                    reasoning=f"Error: {str(e)}",
                    key_factors=[],
                    risks=[],
                ))

        return analyses

    async def quick_analyze(
        self,
        context: MarketContext,
        trading_style: str = "scalping",
    ) -> ConsensusResult:
        """
        Quick analysis using fastest AIML models.

        Uses Grok 4.1 Fast, DeepSeek, and Qwen for rapid decisions.
        Good for real-time scalping scenarios.
        Focuses on momentum and immediate price action.
        """
        fast_providers = [
            "aiml_xai_grok-4.1-fast",
            "aiml_deepseek_deepseek-v3.2",
            "aiml_alibaba_qwen-max",
        ]

        available = [p for p in fast_providers if p in self._providers]

        if not available:
            # Fall back to first 3 available
            available = list(self._providers.keys())[:3]

        return await self.analyze(
            context,
            providers=available,
            mode="quick",
            trading_style=trading_style,
        )

    async def premium_analyze(
        self,
        context: MarketContext,
        trading_style: str = "intraday",
    ) -> ConsensusResult:
        """
        Premium analysis using all 6 AIML models with comprehensive prompts.

        Uses ChatGPT 5.2, Gemini 3 Pro, DeepSeek, Grok, Qwen, GLM.
        Full institutional-grade analysis with SMC concepts, liquidity analysis,
        and detailed trade narrative.
        """
        # Use all 6 models with premium prompts for best analysis
        return await self.analyze(
            context,
            mode="premium",
            trading_style=trading_style,
        )

    def enable_provider(self, provider_key: str) -> bool:
        """Enable a disabled provider."""
        for config in self.config.providers:
            key = f"{config.provider_class.__name__.replace('Provider', '').lower()}_{config.model_name}"
            if key == provider_key and not config.enabled:
                config.enabled = True
                self._initialize_providers()
                return True
        return False

    def disable_provider(self, provider_key: str) -> bool:
        """Disable an active provider."""
        if provider_key in self._providers:
            del self._providers[provider_key]
            for config in self.config.providers:
                key = f"{config.provider_class.__name__.replace('Provider', '').lower()}_{config.model_name}"
                if key == provider_key:
                    config.enabled = False
            return True
        return False

    def get_provider_stats(self) -> Dict[str, Any]:
        """Get statistics about configured providers."""
        enabled = [c for c in self.config.providers if c.enabled]
        disabled = [c for c in self.config.providers if not c.enabled]

        return {
            "total_configured": len(self.config.providers),
            "enabled": len(enabled),
            "disabled": len(disabled),
            "active_providers": list(self._providers.keys()),
            "consensus_method": self.config.consensus_method.value,
            "min_confidence": self.config.min_confidence_threshold,
            "min_agreement": self.config.min_agreement_threshold,
        }


# Singleton instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or create AI Service singleton."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service


def reset_ai_service() -> None:
    """Reset the AI service singleton to reload configuration."""
    global _ai_service
    _ai_service = None


async def create_market_context(
    symbol: str,
    timeframe: str,
    current_price: Optional[Decimal] = None,
    indicators: Optional[Dict[str, Any]] = None,
    candles: Optional[List[Dict[str, Any]]] = None,
    news_sentiment: Optional[float] = None,
    market_session: Optional[str] = None,
    economic_events: Optional[List[Dict[str, Any]]] = None,
    support_levels: Optional[List[Decimal]] = None,
    resistance_levels: Optional[List[Decimal]] = None,
    fetch_real_data: bool = True,
    include_mtf: bool = False,
) -> MarketContext:
    """
    Helper to create MarketContext from trading data.

    If fetch_real_data is True, will fetch real OHLCV data from
    MarketDataService and calculate full technical analysis.

    Args:
        symbol: Trading symbol (e.g., EUR_USD)
        timeframe: Chart timeframe (e.g., 5m, 1h)
        current_price: Optional current price (fetched if not provided)
        indicators: Optional pre-calculated indicators
        candles: Optional pre-fetched candles
        news_sentiment: Optional news sentiment score
        market_session: Current trading session
        economic_events: Upcoming economic events
        support_levels: Pre-defined support levels
        resistance_levels: Pre-defined resistance levels
        fetch_real_data: Whether to fetch real market data
        include_mtf: Include multi-timeframe analysis (premium mode)

    Returns:
        MarketContext with full technical analysis
    """
    full_analysis = None
    final_price = current_price or Decimal("1.0")
    final_candles = candles or []
    final_indicators = indicators or {}
    final_support = support_levels or []
    final_resistance = resistance_levels or []

    if fetch_real_data:
        try:
            # Fetch real market data
            market_data_service = get_market_data_service()
            ta_service = get_technical_analysis_service()

            # Get market data
            market_data = await market_data_service.get_market_data(
                symbol=symbol,
                timeframe=timeframe,
                bars=200,  # Get 200 candles for analysis
            )

            final_price = market_data.current_price

            # Convert candles for context
            final_candles = [c.to_dict() for c in market_data.candles[-20:]]  # Last 20 for prompt

            # Perform full technical analysis
            mtf_data = None
            if include_mtf:
                mtf_data = await market_data_service.get_multiple_timeframes(
                    symbol=symbol,
                    timeframes=["15m", "1h", "4h"],
                    bars=100,
                )

            full_analysis = await ta_service.full_analysis(
                market_data=market_data,
                include_mtf=include_mtf,
                mtf_data=mtf_data,
            )

            # Extract indicators from analysis
            final_indicators = full_analysis.indicators.to_dict()

            # Extract support/resistance from SMC analysis
            if full_analysis.smc.support_levels:
                final_support = full_analysis.smc.support_levels
            if full_analysis.smc.resistance_levels:
                final_resistance = full_analysis.smc.resistance_levels

        except Exception as e:
            print(f"Error fetching real market data: {e}")
            # Fall back to provided data
            if current_price is None:
                final_price = Decimal("1.0")

    # Create context
    context = MarketContext(
        symbol=symbol,
        timeframe=timeframe,
        current_price=final_price,
        indicators=final_indicators,
        candles=final_candles,
        news_sentiment=news_sentiment,
        market_session=market_session or _detect_session(),
        economic_events=economic_events or [],
        support_levels=final_support,
        resistance_levels=final_resistance,
    )

    # Attach full analysis if available (for enhanced prompts)
    if full_analysis:
        context._full_analysis = full_analysis

    return context


def _detect_session() -> str:
    """Detect current trading session based on UTC time."""
    from datetime import datetime
    hour = datetime.utcnow().hour

    if 7 <= hour < 16:
        return "London"
    elif 13 <= hour < 22:
        return "New York"
    elif 23 <= hour or hour < 8:
        return "Tokyo/Sydney"
    else:
        return "Overlap"
