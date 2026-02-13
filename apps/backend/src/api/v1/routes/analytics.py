"""
Analytics routes - Performance metrics and reporting.
"""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.routes.auth import get_current_user
from src.api.v1.routes.bot import collect_user_trades
from src.core.database import get_db
from src.core.models import User
from src.engines.data.indicators import TechnicalIndicators
from src.engines.data.market_data import get_market_data_service
from src.engines.trading.broker_factory import NoBrokerConfiguredError
from src.engines.trading.metatrader_broker import RateLimitError
from src.services.trading_service import get_trading_service

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
    sharpe_ratio: str | None = None
    sortino_ratio: str | None = None
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
    margin_level: str | None = None
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
    support_levels: list[float]
    resistance_levels: list[float]
    indicators: dict


def _parse_trade_timestamp(raw: str | None) -> datetime | None:
    """Parse timestamps from persisted trade payloads."""
    if not raw:
        return None

    normalized = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


@router.get("/account", response_model=AccountSummary)
async def get_account_summary():
    """Get current account summary."""
    import logging
    import os
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
    start_date: date | None = None,
    end_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get overall performance metrics scoped to the authenticated user."""
    all_trades = await collect_user_trades(db, current_user)

    closed_trades: list[dict] = []
    for trade in all_trades:
        pnl = trade.get("profit_loss")
        if pnl is None:
            continue

        ts = _parse_trade_timestamp(trade.get("exit_timestamp") or trade.get("timestamp"))
        if ts is None:
            continue

        trade_day = ts.date()
        if start_date and trade_day < start_date:
            continue
        if end_date and trade_day > end_date:
            continue

        closed_trades.append(trade)

    if not closed_trades:
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

    wins = [
        t
        for t in closed_trades
        if isinstance(t.get("profit_loss"), (int, float)) and float(t["profit_loss"]) > 0
    ]
    losses = [
        t
        for t in closed_trades
        if isinstance(t.get("profit_loss"), (int, float)) and float(t["profit_loss"]) < 0
    ]
    total = len(closed_trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total * 100) if total > 0 else 0

    total_pnl = sum(float(t.get("profit_loss", 0)) for t in closed_trades)
    total_wins = sum(float(t.get("profit_loss", 0)) for t in wins)
    total_losses = abs(sum(float(t.get("profit_loss", 0)) for t in losses))
    avg_win = (total_wins / win_count) if win_count > 0 else 0
    avg_loss = (total_losses / loss_count) if loss_count > 0 else 0
    profit_factor = (total_wins / total_losses) if total_losses > 0 else float("inf") if total_wins > 0 else 0
    largest_win = max((float(t.get("profit_loss", 0)) for t in wins), default=0)
    largest_loss = min((float(t.get("profit_loss", 0)) for t in losses), default=0)
    expectancy = (total_pnl / total) if total > 0 else 0

    sorted_for_drawdown = sorted(
        closed_trades,
        key=lambda t: (t.get("exit_timestamp") or t.get("timestamp") or ""),
    )
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted_for_drawdown:
        cumulative += float(t.get("profit_loss", 0) or 0)
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_dd:
            max_dd = drawdown

    hold_times: list[float] = []
    for t in closed_trades:
        entry_ts = _parse_trade_timestamp(t.get("timestamp"))
        exit_ts = _parse_trade_timestamp(t.get("exit_timestamp"))
        if entry_ts and exit_ts and exit_ts >= entry_ts:
            hold_times.append((exit_ts - entry_ts).total_seconds() / 3600)
    avg_hold = f"{sum(hold_times) / len(hold_times):.1f}h" if hold_times else "N/A"

    return PerformanceMetrics(
        total_trades=total,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate=f"{win_rate:.2f}",
        profit_factor=f"{profit_factor:.2f}" if profit_factor != float("inf") else "Infinity",
        total_pnl=f"{total_pnl:.2f}",
        average_win=f"{avg_win:.2f}",
        average_loss=f"{avg_loss:.2f}",
        largest_win=f"{largest_win:.2f}",
        largest_loss=f"{largest_loss:.2f}",
        max_drawdown=f"{max_dd:.2f}",
        max_drawdown_percent="0.00",
        sharpe_ratio=None,
        sortino_ratio=None,
        expectancy=f"{expectancy:.2f}",
        average_hold_time=avg_hold,
    )


@router.get("/daily", response_model=list[DailyPerformance])
async def get_daily_performance(
    start_date: date | None = None,
    end_date: date | None = None,
):
    """Get daily P&L breakdown."""
    # TODO: Calculate from database
    return []


@router.get("/equity-curve", response_model=list[EquityPoint])
async def get_equity_curve(
    start_date: date | None = None,
    end_date: date | None = None,
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

