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

    # Build indicators dict
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

    # Create market context
    context = await create_market_context(
        symbol=request.symbol,
        timeframe=request.timeframe,
        current_price=Decimal(str(request.current_price)),
        indicators=indicators,
        candles=candles,
        news_sentiment=request.news_sentiment,
        market_session=request.market_session,
        support_levels=support,
        resistance_levels=resistance,
    )

    # Run analysis based on mode
    try:
        if request.mode == "quick":
            result = await service.quick_analyze(context)
        elif request.mode == "premium":
            result = await service.premium_analyze(context)
        else:
            result = await service.analyze(context, providers=request.providers)
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
