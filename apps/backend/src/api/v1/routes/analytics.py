"""
Analytics routes - Performance metrics and reporting.
"""

from datetime import date
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from src.services.trading_service import get_trading_service
from src.engines.data.market_data import get_market_data_service
from src.engines.data.indicators import TechnicalIndicators
from src.engines.trading.broker_factory import NoBrokerConfiguredError
from src.engines.trading.metatrader_broker import RateLimitError

router = APIRouter()


class PerformanceMetrics(BaseModel):
    """Overall performance metrics."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: str
    profit_factor: str
    total_pnl: str
    average_win: str
    average_loss: str
    largest_win: str
    largest_loss: str
    max_drawdown: str
    max_drawdown_percent: str
    sharpe_ratio: Optional[str] = None
    sortino_ratio: Optional[str] = None
    expectancy: str
    average_hold_time: str


class DailyPerformance(BaseModel):
    """Daily P&L record."""
    date: date
    pnl: str
    trades: int
    win_rate: str
    cumulative_pnl: str


class EquityPoint(BaseModel):
    """Point on equity curve."""
    timestamp: str
    equity: str
    drawdown: str
    drawdown_percent: str


class AccountSummary(BaseModel):
    """Account summary."""
    account_id: str
    balance: str
    equity: str
    margin_used: str
    margin_available: str
    unrealized_pnl: str
    realized_pnl_today: str
    currency: str
    leverage: int
    margin_level: Optional[str] = None
    open_positions: int
    pending_orders: int


class IndicatorData(BaseModel):
    """Technical indicator values."""
    symbol: str
    timeframe: str
    timestamp: str
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    ema_20: float
    ema_50: float
    bb_upper: float
    bb_middle: float
    bb_lower: float
    atr: float
    stoch_k: float
    stoch_d: float
    price: float


class AnalysisResponse(BaseModel):
    """Technical analysis response."""
    symbol: str
    timeframe: str
    timestamp: str
    trend: str
    trend_strength: float
    recommendation: str
    confidence: float
    support_levels: List[float]
    resistance_levels: List[float]
    indicators: dict


@router.get("/account", response_model=AccountSummary)
async def get_account_summary():
    """Get current account summary."""
    import os
    import logging
    logger = logging.getLogger(__name__)

    # Debug: Log environment variables
    broker_type = os.environ.get("BROKER_TYPE", "not set")
    metaapi_token = os.environ.get("METAAPI_ACCESS_TOKEN", "not set")
    metaapi_account = os.environ.get("METAAPI_ACCOUNT_ID", "not set")
    logger.info(f"DEBUG: BROKER_TYPE={broker_type}")
    logger.info(f"DEBUG: METAAPI_ACCESS_TOKEN={'set' if metaapi_token != 'not set' else 'not set'}")
    logger.info(f"DEBUG: METAAPI_ACCOUNT_ID={'set' if metaapi_account != 'not set' else 'not set'}")

    try:
        service = await get_trading_service()
        logger.info("DEBUG: Trading service obtained successfully")

        account = await service.get_account_summary()
        logger.info(f"DEBUG: Account summary obtained: {account.get('account_id', 'unknown')}")

        positions = await service.get_positions()
        orders = await service.get_open_orders()

        return AccountSummary(
            account_id=account["account_id"],
            balance=account["balance"],
            equity=account["equity"],
            margin_used=account["margin_used"],
            margin_available=account["margin_available"],
            unrealized_pnl=account["unrealized_pnl"],
            realized_pnl_today=account["realized_pnl_today"],
            currency=account["currency"],
            leverage=account["leverage"],
            margin_level=account["margin_level"],
            open_positions=len(positions),
            pending_orders=len(orders),
        )
    except NoBrokerConfiguredError as e:
        logger.error(f"DEBUG: NoBrokerConfiguredError: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except RateLimitError as e:
        logger.warning(f"Rate limit reached for account summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded. Please wait a few minutes and try again.",
        )
    except Exception as e:
        logger.error(f"DEBUG: Exception in get_account_summary: {type(e).__name__}: {e}")
        # Check if it's a rate limit error from the message
        if "429" in str(e) or "rate limit" in str(e).lower() or "TooManyRequestsError" in str(e):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API rate limit exceeded. Please wait a few minutes and try again.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get overall performance metrics."""
    # TODO: Calculate from database trade history
    return PerformanceMetrics(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        win_rate="0.00",
        profit_factor="0.00",
        total_pnl="0.00",
        average_win="0.00",
        average_loss="0.00",
        largest_win="0.00",
        largest_loss="0.00",
        max_drawdown="0.00",
        max_drawdown_percent="0.00",
        sharpe_ratio=None,
        sortino_ratio=None,
        expectancy="0.00",
        average_hold_time="0h",
    )


@router.get("/daily", response_model=List[DailyPerformance])
async def get_daily_performance(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """Get daily P&L breakdown."""
    # TODO: Calculate from database
    return []


@router.get("/equity-curve", response_model=List[EquityPoint])
async def get_equity_curve(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    resolution: str = Query("1h", pattern="^(1m|5m|15m|1h|4h|1d)$"),
):
    """Get equity curve data."""
    # TODO: Calculate from database
    return []


@router.get("/indicators/{symbol}", response_model=IndicatorData)
async def get_indicators(
    symbol: str,
    timeframe: str = Query("M15", pattern="^(M1|M5|M15|M30|H1|H4|D)$"),
):
    """Get technical indicators for a symbol."""
    market_data = await get_market_data_service()

    # Get candle data
    df = await market_data.get_candles_df(
        symbol=symbol,
        timeframe=timeframe,
        count=200,
    )

    if df.empty:
        return IndicatorData(
            symbol=symbol,
            timeframe=timeframe,
            timestamp="",
            rsi=0, macd=0, macd_signal=0, macd_histogram=0,
            ema_20=0, ema_50=0,
            bb_upper=0, bb_middle=0, bb_lower=0,
            atr=0, stoch_k=0, stoch_d=0, price=0,
        )

    # Calculate indicators
    indicators = TechnicalIndicators(df)
    data = indicators.to_dict()

    return IndicatorData(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=str(df.index[-1]),
        **data,
    )


@router.get("/analysis/{symbol}", response_model=AnalysisResponse)
async def get_analysis(
    symbol: str,
    timeframe: str = Query("M15", pattern="^(M1|M5|M15|M30|H1|H4|D)$"),
):
    """Get full technical analysis for a symbol."""
    market_data = await get_market_data_service()

    # Get candle data
    df = await market_data.get_candles_df(
        symbol=symbol,
        timeframe=timeframe,
        count=200,
    )

    if df.empty:
        return AnalysisResponse(
            symbol=symbol,
            timeframe=timeframe,
            timestamp="",
            trend="neutral",
            trend_strength=0,
            recommendation="HOLD",
            confidence=0,
            support_levels=[],
            resistance_levels=[],
            indicators={},
        )

    # Perform analysis
    indicators = TechnicalIndicators(df)
    analysis = indicators.analyze(symbol=symbol, timeframe=timeframe)

    return AnalysisResponse(
        symbol=analysis.symbol,
        timeframe=analysis.timeframe,
        timestamp=analysis.timestamp,
        trend=analysis.trend,
        trend_strength=analysis.trend_strength,
        recommendation=analysis.recommendation,
        confidence=analysis.confidence,
        support_levels=analysis.support_levels,
        resistance_levels=analysis.resistance_levels,
        indicators={
            i.name: {
                "value": i.value,
                "signal": i.signal,
                "strength": i.strength,
                "details": i.details,
            }
            for i in analysis.indicators
        },
    )
