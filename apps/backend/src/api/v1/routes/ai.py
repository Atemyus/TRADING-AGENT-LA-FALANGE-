"""
AI Analysis Routes

Endpoints for AI-powered market analysis using multi-model consensus.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.engines.ai.base_ai import MarketContext, TradeDirection
from src.engines.ai.consensus_engine import AgreementLevel, ConsensusMethod
from src.services.ai_service import get_ai_service, create_market_context

# TradingView Agent imports
try:
    from src.engines.ai.tradingview_agent import (
        TradingViewAIAgent,
        TradingViewAnalysisResult,
        get_tradingview_agent,
    )
    TRADINGVIEW_AGENT_AVAILABLE = True
except ImportError:
    TRADINGVIEW_AGENT_AVAILABLE = False

router = APIRouter()


# ========== Request/Response Models ==========


class IndicatorsInput(BaseModel):
    """Technical indicators input."""
    rsi: Optional[float] = Field(None, ge=0, le=100)
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    atr: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    stochastic_k: Optional[float] = None
    stochastic_d: Optional[float] = None
    adx: Optional[float] = None
    volume: Optional[float] = None
    vwap: Optional[float] = None


class CandleInput(BaseModel):
    """OHLCV candle input."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = 0


class AnalysisRequest(BaseModel):
    """Request for AI market analysis."""
    symbol: str = Field(..., description="Trading symbol (e.g., EUR_USD)")
    timeframe: str = Field(default="5m", description="Chart timeframe")
    current_price: float = Field(..., gt=0, description="Current market price")
    indicators: IndicatorsInput = Field(default_factory=IndicatorsInput)
    candles: Optional[List[CandleInput]] = Field(
        None, description="Recent OHLCV candles"
    )
    news_sentiment: Optional[float] = Field(
        None, ge=-1, le=1, description="News sentiment score (-1 to 1)"
    )
    market_session: Optional[str] = Field(
        None, description="Current market session (e.g., london, newyork)"
    )
    support_levels: Optional[List[float]] = None
    resistance_levels: Optional[List[float]] = None
    providers: Optional[List[str]] = Field(
        None, description="Specific providers to use (default: all)"
    )
    mode: Optional[str] = Field(
        "standard", description="Analysis mode: quick, standard, premium"
    )


class VoteDetail(BaseModel):
    """Individual provider vote details."""
    provider: str
    model: str
    direction: str
    confidence: float
    reasoning: str
    is_valid: bool
    error: Optional[str] = None


class ConsensusResponse(BaseModel):
    """AI consensus analysis response."""
    # Decision
    direction: str
    confidence: float
    should_trade: bool

    # Voting stats
    total_votes: int
    valid_votes: int
    votes_buy: int
    votes_sell: int
    votes_hold: int
    agreement_level: str
    agreement_percentage: float

    # Trade parameters
    suggested_entry: Optional[str] = None
    suggested_stop_loss: Optional[str] = None
    suggested_take_profit: Optional[str] = None
    risk_reward_ratio: Optional[float] = None

    # Insights
    key_factors: List[str]
    risks: List[str]
    reasoning_summary: str

    # Individual votes
    votes: List[VoteDetail]

    # Costs
    total_cost_usd: float
    total_tokens: int
    processing_time_ms: int

    # Metadata
    providers_used: List[str]
    failed_providers: List[str]


class ProviderStatus(BaseModel):
    """Individual provider status."""
    name: str
    healthy: bool
    model: str


class ServiceStatusResponse(BaseModel):
    """AI service status response."""
    total_providers: int
    active_providers: int
    disabled_providers: int
    consensus_method: str
    min_confidence: float
    min_agreement: float
    providers: List[ProviderStatus]


# ========== Endpoints ==========


@router.post("/analyze", response_model=ConsensusResponse)
async def analyze_market(request: AnalysisRequest):
    """
    Run AI-powered market analysis using multiple models.

    This endpoint:
    1. Sends market data to multiple AI providers in parallel
    2. Each AI returns a trade recommendation with confidence
    3. Consensus engine aggregates votes and produces unified decision
    4. Returns detailed analysis with individual votes and statistics

    Modes:
    - quick: Uses only fastest providers (Groq, GPT-4o-mini)
    - standard: Uses balanced set of providers
    - premium: Uses highest quality providers
    """
    service = get_ai_service()

    # Build indicators dict (will be overridden by real data if available)
    indicators = {
        k: v for k, v in request.indicators.model_dump().items()
        if v is not None
    }

    # Build candles list
    candles = None
    if request.candles:
        candles = [c.model_dump() for c in request.candles]

    # Build support/resistance levels
    support = [Decimal(str(x)) for x in request.support_levels] if request.support_levels else None
    resistance = [Decimal(str(x)) for x in request.resistance_levels] if request.resistance_levels else None

    # Determine if we should use premium features
    include_mtf = request.mode == "premium"

    # Create market context with REAL data from market data service
    # This will fetch actual OHLCV data and calculate technical indicators and SMC zones
    context = await create_market_context(
        symbol=request.symbol,
        timeframe=request.timeframe,
        current_price=Decimal(str(request.current_price)) if request.current_price else None,
        indicators=indicators if indicators else None,
        candles=candles,
        news_sentiment=request.news_sentiment,
        market_session=request.market_session,
        support_levels=support,
        resistance_levels=resistance,
        fetch_real_data=True,  # Fetch real OHLCV data from Yahoo/TwelveData
        include_mtf=include_mtf,  # Include multi-timeframe analysis for premium
    )

    # Determine trading style from timeframe
    trading_style = "scalping" if request.timeframe in ["1m", "5m"] else \
                    "swing" if request.timeframe in ["4h", "1d", "1w"] else "intraday"

    # Run analysis based on mode
    try:
        if request.mode == "quick":
            result = await service.quick_analyze(context, trading_style=trading_style)
        elif request.mode == "premium":
            result = await service.premium_analyze(context, trading_style=trading_style)
        else:
            result = await service.analyze(
                context,
                providers=request.providers,
                mode="standard",
                trading_style=trading_style,
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )

    # Build response
    votes = [
        VoteDetail(
            provider=v.provider_name,
            model=v.model_name,
            direction=v.direction.value,
            confidence=v.confidence,
            reasoning=v.reasoning[:500] if v.reasoning else "",
            is_valid=v.is_valid,
            error=v.error,
        )
        for v in result.individual_votes
    ]

    return ConsensusResponse(
        direction=result.direction.value,
        confidence=result.confidence,
        should_trade=result.should_trade,
        total_votes=result.total_votes,
        valid_votes=result.valid_votes,
        votes_buy=result.votes_for,
        votes_sell=result.votes_against,
        votes_hold=result.votes_hold,
        agreement_level=result.agreement_level.value,
        agreement_percentage=result.agreement_percentage * 100,
        suggested_entry=str(result.suggested_entry) if result.suggested_entry else None,
        suggested_stop_loss=str(result.suggested_stop_loss) if result.suggested_stop_loss else None,
        suggested_take_profit=str(result.suggested_take_profit) if result.suggested_take_profit else None,
        risk_reward_ratio=result.suggested_risk_reward,
        key_factors=result.key_factors,
        risks=result.risks,
        reasoning_summary=result.reasoning_summary,
        votes=votes,
        total_cost_usd=result.total_cost_usd,
        total_tokens=result.total_tokens,
        processing_time_ms=result.total_processing_time_ms,
        providers_used=result.providers_used,
        failed_providers=result.failed_providers,
    )


@router.get("/status", response_model=ServiceStatusResponse)
async def get_service_status():
    """
    Get AI service status and provider health.

    Returns information about configured providers,
    their health status, and consensus settings.
    """
    service = get_ai_service()
    stats = service.get_provider_stats()
    health = await service.health_check()

    providers = [
        ProviderStatus(
            name=name,
            healthy=health.get(name, False),
            model=name.split("_", 1)[1] if "_" in name else name,
        )
        for name in stats["active_providers"]
    ]

    return ServiceStatusResponse(
        total_providers=stats["total_configured"],
        active_providers=stats["enabled"],
        disabled_providers=stats["disabled"],
        consensus_method=stats["consensus_method"],
        min_confidence=stats["min_confidence"],
        min_agreement=stats["min_agreement"],
        providers=providers,
    )


@router.get("/providers")
async def list_providers():
    """
    List all available AI providers.

    Returns details about each provider including
    supported models, pricing, and capabilities.
    """
    service = get_ai_service()
    stats = service.get_provider_stats()

    return {
        "active": stats["active_providers"],
        "total_configured": stats["total_configured"],
        "providers": [
            {
                "key": name,
                "provider": name.split("_")[0] if "_" in name else name,
                "model": name.split("_", 1)[1] if "_" in name else name,
            }
            for name in stats["active_providers"]
        ],
    }


@router.post("/providers/{provider_key}/enable")
async def enable_provider(provider_key: str):
    """Enable a disabled provider."""
    service = get_ai_service()
    success = service.enable_provider(provider_key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_key} not found or already enabled",
        )

    return {"success": True, "provider": provider_key, "message": "Provider enabled"}


@router.post("/providers/{provider_key}/disable")
async def disable_provider(provider_key: str):
    """Disable an active provider."""
    service = get_ai_service()
    success = service.disable_provider(provider_key)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Provider {provider_key} not found or already disabled",
        )

    return {"success": True, "provider": provider_key, "message": "Provider disabled"}


@router.get("/health")
async def health_check():
    """
    Check health of all AI providers.

    Returns a dict with each provider's health status.
    """
    service = get_ai_service()
    health = await service.health_check()

    healthy_count = sum(1 for v in health.values() if v)
    total_count = len(health)

    return {
        "overall": healthy_count == total_count,
        "healthy_providers": healthy_count,
        "total_providers": total_count,
        "providers": health,
    }


@router.get("/consensus-methods")
async def list_consensus_methods():
    """
    List available consensus methods.

    Returns all available methods for vote aggregation.
    """
    return {
        "methods": [
            {
                "value": ConsensusMethod.MAJORITY.value,
                "name": "Majority",
                "description": "Simple majority voting - direction with most votes wins",
            },
            {
                "value": ConsensusMethod.WEIGHTED.value,
                "name": "Weighted",
                "description": "Weighted by confidence - higher confidence votes count more",
            },
            {
                "value": ConsensusMethod.CONFIDENCE_THRESHOLD.value,
                "name": "Confidence Threshold",
                "description": "Only votes with confidence >= 70% are counted",
            },
            {
                "value": ConsensusMethod.UNANIMOUS.value,
                "name": "Unanimous",
                "description": "All providers must agree for a trade signal",
            },
            {
                "value": ConsensusMethod.SUPERMAJORITY.value,
                "name": "Supermajority",
                "description": "At least 2/3 of providers must agree",
            },
        ],
        "current": "weighted",  # Default
    }


@router.get("/agreement-levels")
async def list_agreement_levels():
    """
    List agreement level thresholds.

    Returns the meaning of each agreement level.
    """
    return {
        "levels": [
            {
                "value": AgreementLevel.UNANIMOUS.value,
                "name": "Unanimous",
                "threshold": "100%",
                "description": "All providers agree on the direction",
            },
            {
                "value": AgreementLevel.STRONG.value,
                "name": "Strong",
                "threshold": "≥ 80%",
                "description": "Strong majority agrees on the direction",
            },
            {
                "value": AgreementLevel.MODERATE.value,
                "name": "Moderate",
                "threshold": "≥ 60%",
                "description": "Moderate majority agrees on the direction",
            },
            {
                "value": AgreementLevel.WEAK.value,
                "name": "Weak",
                "threshold": "≥ 40%",
                "description": "Weak plurality agrees on the direction",
            },
            {
                "value": AgreementLevel.SPLIT.value,
                "name": "Split",
                "threshold": "< 40%",
                "description": "Providers are split, no clear direction",
            },
        ],
    }


# ========== TradingView Agent Endpoints ==========


class TradingViewAgentRequest(BaseModel):
    """Request for TradingView Agent analysis."""
    symbol: str = Field(..., description="Trading symbol (e.g., EURUSD)")
    mode: str = Field(
        default="standard",
        description="Analysis mode: quick (1 TF), standard (2 TF), premium (3 TF), ultra (5 TF)"
    )
    max_indicators: int = Field(
        default=3,
        ge=1,
        le=25,
        description="Max indicators per TradingView plan (3=Basic, 5=Essential, 10=Plus, 25=Premium)"
    )
    headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )


class TimeframeConsensus(BaseModel):
    """Consensus for a single timeframe."""
    direction: str
    confidence: float
    models_agree: int
    total_models: int


class TradingViewModelResult(BaseModel):
    """Individual AI model result from TradingView analysis."""
    model: str
    model_display_name: str
    timeframe: str
    analysis_style: str
    direction: str
    confidence: float
    indicators_used: List[str]
    drawings_made: List[Dict[str, Any]]
    reasoning: str
    key_observations: List[str]
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: List[float] = []
    break_even_trigger: Optional[float] = None
    trailing_stop_pips: Optional[float] = None
    error: Optional[str] = None


class TradingViewAgentResponse(BaseModel):
    """Response from TradingView Agent analysis."""
    # Overall consensus
    direction: str
    confidence: float
    is_strong_signal: bool

    # Model agreement
    models_agree: int
    total_models: int

    # Multi-timeframe data
    mode: str
    timeframes_analyzed: List[str]
    models_used: List[str]
    timeframe_alignment: float
    is_aligned: bool
    timeframe_consensus: Dict[str, TimeframeConsensus]

    # Trade parameters
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    break_even_trigger: Optional[float] = None
    trailing_stop_pips: Optional[float] = None

    # Analysis details
    analysis_styles_used: List[str]
    indicators_used: List[str]
    key_observations: List[str]
    combined_reasoning: str

    # Vote breakdown
    vote_breakdown: Dict[str, int]

    # Individual results (optional, can be large)
    individual_results: Optional[List[TradingViewModelResult]] = None


@router.post("/tradingview-agent", response_model=TradingViewAgentResponse)
async def analyze_with_tradingview_agent(request: TradingViewAgentRequest):
    """
    Run AI analysis using TradingView Agent with real browser automation.

    This endpoint:
    1. Opens TradingView.com in a real browser
    2. Each AI model autonomously:
       - Changes timeframes on TradingView
       - Adds its preferred indicators
       - Draws zones, trendlines, support/resistance
       - Takes screenshots at each step
       - Provides detailed analysis with reasoning
    3. Returns multi-timeframe consensus with alignment score

    Modes:
    - quick: 1 timeframe (15m), 1 AI model
    - standard: 2 timeframes (15m, 1h), 2 AI models
    - premium: 3 timeframes (15m, 1h, 4h), 4 AI models
    - ultra: 5 timeframes (5m, 15m, 1h, 4h, D), 6 AI models
    """
    if not TRADINGVIEW_AGENT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TradingView Agent not available. Install playwright: pip install playwright && playwright install chromium"
        )

    try:
        # Get or create the TradingView agent
        agent = await get_tradingview_agent(
            headless=request.headless,
            max_indicators=request.max_indicators
        )

        # Run multi-timeframe analysis
        consensus = await agent.analyze_with_mode(
            symbol=request.symbol,
            mode=request.mode
        )

        # Build timeframe consensus response
        tf_consensus = {}
        for tf, tc in consensus.get("timeframe_consensus", {}).items():
            tf_consensus[tf] = TimeframeConsensus(
                direction=tc.get("direction", "HOLD"),
                confidence=tc.get("confidence", 0),
                models_agree=tc.get("models_agree", 0),
                total_models=tc.get("total_models", 0),
            )

        # Build individual results (without screenshots to reduce payload)
        individual_results = []
        for r in consensus.get("all_results", []):
            individual_results.append(TradingViewModelResult(
                model=r.model,
                model_display_name=r.model_display_name,
                timeframe=r.timeframe,
                analysis_style=r.analysis_style,
                direction=r.direction,
                confidence=r.confidence,
                indicators_used=r.indicators_used,
                drawings_made=r.drawings_made,
                reasoning=r.reasoning[:500] if r.reasoning else "",
                key_observations=r.key_observations[:5],
                entry_price=r.entry_price,
                stop_loss=r.stop_loss,
                take_profit=r.take_profit,
                break_even_trigger=r.break_even_trigger,
                trailing_stop_pips=r.trailing_stop_pips,
                error=r.error,
            ))

        return TradingViewAgentResponse(
            direction=consensus.get("direction", "HOLD"),
            confidence=consensus.get("confidence", 0),
            is_strong_signal=consensus.get("is_strong_signal", False),
            models_agree=consensus.get("models_agree", 0),
            total_models=consensus.get("total_models", 0),
            mode=consensus.get("mode", request.mode),
            timeframes_analyzed=consensus.get("timeframes_analyzed", []),
            models_used=consensus.get("models_used", []),
            timeframe_alignment=consensus.get("timeframe_alignment", 0),
            is_aligned=consensus.get("is_aligned", False),
            timeframe_consensus=tf_consensus,
            entry_price=consensus.get("entry_price"),
            stop_loss=consensus.get("stop_loss"),
            take_profit=consensus.get("take_profit"),
            break_even_trigger=consensus.get("break_even_trigger"),
            trailing_stop_pips=consensus.get("trailing_stop_pips"),
            analysis_styles_used=consensus.get("analysis_styles_used", []),
            indicators_used=consensus.get("indicators_used", []),
            key_observations=consensus.get("key_observations", [])[:10],
            combined_reasoning=consensus.get("combined_reasoning", "")[:2000],
            vote_breakdown=consensus.get("vote_breakdown", {}),
            individual_results=individual_results,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TradingView Agent analysis failed: {str(e)}"
        )


@router.get("/tradingview-agent/status")
async def get_tradingview_agent_status():
    """
    Get TradingView Agent availability and configuration.
    """
    return {
        "available": TRADINGVIEW_AGENT_AVAILABLE,
        "modes": {
            "quick": {"timeframes": ["15"], "models": 1},
            "standard": {"timeframes": ["15", "60"], "models": 2},
            "premium": {"timeframes": ["15", "60", "240"], "models": 4},
            "ultra": {"timeframes": ["5", "15", "60", "240", "D"], "models": 6},
        },
        "tradingview_plans": {
            "basic": {"max_indicators": 3, "price": "Free"},
            "essential": {"max_indicators": 5, "price": "$12.95/mo"},
            "plus": {"max_indicators": 10, "price": "$24.95/mo"},
            "premium": {"max_indicators": 25, "price": "$49.95/mo"},
        },
        "ai_models": [
            {"key": "chatgpt", "name": "ChatGPT 5.2", "style": "SMC"},
            {"key": "gemini", "name": "Gemini 3 Pro", "style": "Trend"},
            {"key": "deepseek", "name": "DeepSeek V3.2", "style": "Price Action"},
            {"key": "glm", "name": "GLM 4.5", "style": "Indicator-based"},
            {"key": "grok", "name": "Grok 4.1", "style": "Volatility"},
            {"key": "qwen", "name": "Qwen Max", "style": "Hybrid"},
        ],
    }
