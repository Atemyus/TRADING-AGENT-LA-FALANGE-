"""
Market Data Routes

Endpoints for real-time market data, technical analysis, and price information.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.services.market_data_service import get_market_data_service, SYMBOL_MAPPINGS
from src.services.technical_analysis_service import get_technical_analysis_service

router = APIRouter()


# ========== Response Models ==========


class PriceResponse(BaseModel):
    """Current price response."""
    symbol: str
    price: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    spread: Optional[float] = None
    daily_high: Optional[float] = None
    daily_low: Optional[float] = None
    daily_change_percent: Optional[float] = None
    source: str
    timestamp: str


class CandleResponse(BaseModel):
    """OHLCV candle response."""
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class IndicatorsResponse(BaseModel):
    """Technical indicators response."""
    # Trend
    ema_9: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None

    # Momentum
    rsi_14: Optional[float] = None
    rsi_7: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None

    # Volatility
    atr_14: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None

    # Trend Strength
    adx: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None


class ZoneResponse(BaseModel):
    """Price zone (Order Block, FVG, Supply/Demand, etc.)."""
    type: str
    price_high: float
    price_low: float
    mid_price: float
    strength: float
    timestamp: str
    description: str


class SMCResponse(BaseModel):
    """Smart Money Concepts analysis response."""
    trend: str
    trend_strength: float
    institutional_bias: str
    last_structure: Optional[str] = None
    order_blocks: List[ZoneResponse]
    fair_value_gaps: List[ZoneResponse]
    supply_zones: List[ZoneResponse]
    demand_zones: List[ZoneResponse]
    liquidity_pools: List[ZoneResponse]
    support_levels: List[float]
    resistance_levels: List[float]
    pivot_points: Dict[str, float]
    retail_trap_warning: Optional[str] = None


class FullAnalysisResponse(BaseModel):
    """Complete technical analysis response."""
    symbol: str
    timeframe: str
    current_price: float
    timestamp: str
    indicators: IndicatorsResponse
    smc: SMCResponse
    candle_patterns: List[str]
    mtf_trend: Dict[str, str]
    mtf_bias: str


# ========== Endpoints ==========


@router.get("/symbols")
async def list_symbols():
    """List all available trading symbols."""
    return {
        "symbols": [
            {
                "symbol": symbol,
                "category": _get_symbol_category(symbol),
            }
            for symbol in SYMBOL_MAPPINGS.keys()
        ],
        "categories": ["forex", "commodities", "indices", "crypto"],
    }


@router.get("/price/{symbol}", response_model=PriceResponse)
async def get_price(symbol: str):
    """
    Get current price for a symbol.

    Args:
        symbol: Trading symbol (e.g., EUR_USD, XAU_USD)

    Returns:
        Current price and basic metadata
    """
    try:
        service = get_market_data_service()
        data = await service.get_market_data(symbol, timeframe="1m", bars=1)

        return PriceResponse(
            symbol=symbol,
            price=float(data.current_price),
            bid=float(data.bid) if data.bid else None,
            ask=float(data.ask) if data.ask else None,
            spread=float(data.spread) if data.spread else None,
            daily_high=float(data.daily_high) if data.daily_high else None,
            daily_low=float(data.daily_low) if data.daily_low else None,
            daily_change_percent=data.daily_change_percent,
            source=data.source.value,
            timestamp=data.last_updated.isoformat(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price: {str(e)}")


@router.get("/candles/{symbol}")
async def get_candles(
    symbol: str,
    timeframe: str = Query(default="5m", description="Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d)"),
    bars: int = Query(default=100, ge=1, le=500, description="Number of candles"),
):
    """
    Get OHLCV candles for a symbol.

    Args:
        symbol: Trading symbol
        timeframe: Chart timeframe
        bars: Number of candles to fetch

    Returns:
        List of OHLCV candles
    """
    try:
        service = get_market_data_service()
        data = await service.get_market_data(symbol, timeframe=timeframe, bars=bars)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "count": len(data.candles),
            "candles": [
                CandleResponse(
                    timestamp=c.timestamp.isoformat(),
                    open=float(c.open),
                    high=float(c.high),
                    low=float(c.low),
                    close=float(c.close),
                    volume=c.volume,
                )
                for c in data.candles
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch candles: {str(e)}")


@router.get("/indicators/{symbol}", response_model=IndicatorsResponse)
async def get_indicators(
    symbol: str,
    timeframe: str = Query(default="5m", description="Timeframe"),
):
    """
    Get technical indicators for a symbol.

    Calculates RSI, MACD, EMAs, Bollinger Bands, ADX, etc.
    """
    try:
        market_service = get_market_data_service()
        ta_service = get_technical_analysis_service()

        data = await market_service.get_market_data(symbol, timeframe=timeframe, bars=200)
        df = data.to_dataframe()

        indicators = ta_service.calculate_indicators(df)

        return IndicatorsResponse(**indicators.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate indicators: {str(e)}")


@router.get("/smc/{symbol}", response_model=SMCResponse)
async def get_smc_analysis(
    symbol: str,
    timeframe: str = Query(default="5m", description="Timeframe"),
):
    """
    Get Smart Money Concepts analysis for a symbol.

    Identifies Order Blocks, Fair Value Gaps, Supply/Demand zones,
    Liquidity pools, and market structure.
    """
    try:
        market_service = get_market_data_service()
        ta_service = get_technical_analysis_service()

        data = await market_service.get_market_data(symbol, timeframe=timeframe, bars=200)
        df = data.to_dataframe()

        smc = ta_service.analyze_smc(df, data.current_price)

        return SMCResponse(
            trend=smc.trend.value,
            trend_strength=smc.trend_strength,
            institutional_bias=smc.institutional_bias,
            last_structure=smc.last_structure.value if smc.last_structure else None,
            order_blocks=[
                ZoneResponse(
                    type=z.zone_type.value,
                    price_high=float(z.price_high),
                    price_low=float(z.price_low),
                    mid_price=float(z.mid_price),
                    strength=z.strength,
                    timestamp=z.timestamp.isoformat(),
                    description=z.description,
                )
                for z in smc.order_blocks
            ],
            fair_value_gaps=[
                ZoneResponse(
                    type=z.zone_type.value,
                    price_high=float(z.price_high),
                    price_low=float(z.price_low),
                    mid_price=float(z.mid_price),
                    strength=z.strength,
                    timestamp=z.timestamp.isoformat(),
                    description=z.description,
                )
                for z in smc.fair_value_gaps
            ],
            supply_zones=[
                ZoneResponse(
                    type=z.zone_type.value,
                    price_high=float(z.price_high),
                    price_low=float(z.price_low),
                    mid_price=float(z.mid_price),
                    strength=z.strength,
                    timestamp=z.timestamp.isoformat(),
                    description=z.description,
                )
                for z in smc.supply_zones
            ],
            demand_zones=[
                ZoneResponse(
                    type=z.zone_type.value,
                    price_high=float(z.price_high),
                    price_low=float(z.price_low),
                    mid_price=float(z.mid_price),
                    strength=z.strength,
                    timestamp=z.timestamp.isoformat(),
                    description=z.description,
                )
                for z in smc.demand_zones
            ],
            liquidity_pools=[
                ZoneResponse(
                    type=z.zone_type.value,
                    price_high=float(z.price_high),
                    price_low=float(z.price_low),
                    mid_price=float(z.mid_price),
                    strength=z.strength,
                    timestamp=z.timestamp.isoformat(),
                    description=z.description,
                )
                for z in smc.liquidity_pools
            ],
            support_levels=[float(s) for s in smc.support_levels],
            resistance_levels=[float(r) for r in smc.resistance_levels],
            pivot_points={k: float(v) for k, v in smc.pivot_points.items()},
            retail_trap_warning=smc.retail_trap_warning,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze SMC: {str(e)}")


@router.get("/analysis/{symbol}", response_model=FullAnalysisResponse)
async def get_full_analysis(
    symbol: str,
    timeframe: str = Query(default="5m", description="Timeframe"),
    include_mtf: bool = Query(default=False, description="Include multi-timeframe analysis"),
):
    """
    Get complete technical analysis for a symbol.

    Includes all indicators, SMC zones, candle patterns, and optionally
    multi-timeframe trend analysis.
    """
    try:
        market_service = get_market_data_service()
        ta_service = get_technical_analysis_service()

        # Fetch market data
        data = await market_service.get_market_data(symbol, timeframe=timeframe, bars=200)

        # Fetch MTF data if requested
        mtf_data = None
        if include_mtf:
            mtf_data = await market_service.get_multiple_timeframes(
                symbol=symbol,
                timeframes=["15m", "1h", "4h"],
                bars=100,
            )

        # Perform full analysis
        analysis = await ta_service.full_analysis(
            market_data=data,
            include_mtf=include_mtf,
            mtf_data=mtf_data,
        )

        # Build response
        smc = analysis.smc
        indicators = analysis.indicators

        return FullAnalysisResponse(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            current_price=float(analysis.current_price),
            timestamp=analysis.timestamp.isoformat(),
            indicators=IndicatorsResponse(**indicators.to_dict()),
            smc=SMCResponse(
                trend=smc.trend.value,
                trend_strength=smc.trend_strength,
                institutional_bias=smc.institutional_bias,
                last_structure=smc.last_structure.value if smc.last_structure else None,
                order_blocks=[
                    ZoneResponse(
                        type=z.zone_type.value,
                        price_high=float(z.price_high),
                        price_low=float(z.price_low),
                        mid_price=float(z.mid_price),
                        strength=z.strength,
                        timestamp=z.timestamp.isoformat(),
                        description=z.description,
                    )
                    for z in smc.order_blocks
                ],
                fair_value_gaps=[
                    ZoneResponse(
                        type=z.zone_type.value,
                        price_high=float(z.price_high),
                        price_low=float(z.price_low),
                        mid_price=float(z.mid_price),
                        strength=z.strength,
                        timestamp=z.timestamp.isoformat(),
                        description=z.description,
                    )
                    for z in smc.fair_value_gaps
                ],
                supply_zones=[
                    ZoneResponse(
                        type=z.zone_type.value,
                        price_high=float(z.price_high),
                        price_low=float(z.price_low),
                        mid_price=float(z.mid_price),
                        strength=z.strength,
                        timestamp=z.timestamp.isoformat(),
                        description=z.description,
                    )
                    for z in smc.supply_zones
                ],
                demand_zones=[
                    ZoneResponse(
                        type=z.zone_type.value,
                        price_high=float(z.price_high),
                        price_low=float(z.price_low),
                        mid_price=float(z.mid_price),
                        strength=z.strength,
                        timestamp=z.timestamp.isoformat(),
                        description=z.description,
                    )
                    for z in smc.demand_zones
                ],
                liquidity_pools=[
                    ZoneResponse(
                        type=z.zone_type.value,
                        price_high=float(z.price_high),
                        price_low=float(z.price_low),
                        mid_price=float(z.mid_price),
                        strength=z.strength,
                        timestamp=z.timestamp.isoformat(),
                        description=z.description,
                    )
                    for z in smc.liquidity_pools
                ],
                support_levels=[float(s) for s in smc.support_levels],
                resistance_levels=[float(r) for r in smc.resistance_levels],
                pivot_points={k: float(v) for k, v in smc.pivot_points.items()},
                retail_trap_warning=smc.retail_trap_warning,
            ),
            candle_patterns=analysis.candle_patterns,
            mtf_trend={k: v.value for k, v in analysis.mtf_trend.items()},
            mtf_bias=analysis.mtf_bias,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform analysis: {str(e)}")


@router.get("/debug/streaming-status")
async def get_streaming_status():
    """
    Debug endpoint to check price streaming status.
    Shows broker connection, data source, and cached prices.
    """
    from src.services.price_streaming_service import get_price_streaming_service
    from src.engines.trading.broker_factory import BrokerFactory
    import os

    try:
        # Get price streaming service status
        price_service = await get_price_streaming_service()

        # Get broker info
        broker_type = os.environ.get("BROKER_TYPE", "none")
        broker_configured = BrokerFactory.is_configured()

        # Get cached prices
        cached_prices = price_service.get_all_prices()
        price_summary = {
            symbol: {
                "bid": str(tick.bid),
                "ask": str(tick.ask),
                "mid": str(tick.mid),
            }
            for symbol, tick in list(cached_prices.items())[:10]  # First 10 only
        }

        return {
            "broker_type": broker_type,
            "broker_configured": broker_configured,
            "broker_connected": price_service.is_broker_connected,
            "data_source": price_service.data_source,
            "simulation_disabled": price_service.simulation_disabled,
            "streaming_active": price_service._streaming,
            "subscribed_symbols_count": len(price_service._subscribers),
            "subscribed_symbols": list(price_service._subscribers.keys())[:20],
            "available_symbols": list(price_service.available_symbols)[:20],
            "failed_symbols": list(price_service.failed_symbols)[:20],
            "cached_prices_count": len(cached_prices),
            "sample_prices": price_summary,
        }
    except Exception as e:
        return {
            "error": str(e),
            "broker_type": os.environ.get("BROKER_TYPE", "none"),
        }


@router.get("/available-symbols")
async def get_available_symbols():
    """
    Get symbols that are available from the broker (real prices).
    Also returns symbols that failed (simulated).
    """
    from src.services.price_streaming_service import get_price_streaming_service

    try:
        price_service = await get_price_streaming_service()

        available = list(price_service.available_symbols)
        failed = list(price_service.failed_symbols)

        return {
            "broker_connected": price_service.is_broker_connected,
            "data_source": price_service.data_source,
            "simulation_disabled": price_service.simulation_disabled,
            "available_symbols": sorted(available),
            "available_count": len(available),
            "failed_symbols": sorted(failed),
            "failed_count": len(failed),
            "total_requested": len(available) + len(failed),
        }
    except Exception as e:
        return {
            "error": str(e),
            "available_symbols": [],
            "failed_symbols": [],
        }


def _get_symbol_category(symbol: str) -> str:
    """Get category for a symbol."""
    if symbol.endswith("_USD") and len(symbol) == 7:
        if symbol.startswith("X"):
            return "commodities"
        return "forex"
    if symbol in ["US30", "NAS100", "SPX500", "UK100", "DE40"]:
        return "indices"
    if symbol in ["BTC_USD", "ETH_USD"]:
        return "crypto"
    return "forex"
