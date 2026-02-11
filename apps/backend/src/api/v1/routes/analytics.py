"""
Analytics routes - Performance metrics and reporting.
"""

from datetime import UTC, date

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

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
):
    """Get overall performance metrics from bot trade history and broker deals."""
    from src.engines.trading.auto_trader import get_auto_trader

    bot = get_auto_trader()
    closed_trades = [t for t in bot.state.trade_history if t.profit_loss is not None]

    # Also try to get data from broker deal history
    try:
        service = await get_trading_service()
        if hasattr(service._broker, 'get_deals_history'):
            from datetime import datetime as dt
            from datetime import timedelta
            # Get last 30 days of deals
            start = dt.now(UTC) - timedelta(days=30)
            deals = await service._broker.get_deals_history(start.isoformat())
            # Extract profit from deals that have a profit field
            for deal in deals:
                profit = deal.get("profit", 0)
                if profit and profit != 0:
                    # Add broker deal as a pseudo-trade if not already tracked
                    deal_id = str(deal.get("id", deal.get("dealId", "")))
                    if not any(t.id == deal_id for t in closed_trades):
                        from src.engines.trading.auto_trader import TradeRecord
                        pseudo_trade = TradeRecord(
                            id=deal_id,
                            symbol=deal.get("symbol", "UNKNOWN"),
                            direction=deal.get("type", "UNKNOWN"),
                            entry_price=float(deal.get("price", 0)),
                            units=float(deal.get("volume", 0)),
                            timestamp=dt.now(UTC),
                            profit_loss=float(profit) + float(deal.get("swap", 0)) + float(deal.get("commission", 0)),
                            status="closed",
                        )
                        closed_trades.append(pseudo_trade)
    except Exception as e:
        print(f"[Analytics] Error fetching broker deals: {e}")

    if not closed_trades:
        return PerformanceMetrics(
            total_trades=0, winning_trades=0, losing_trades=0,
            win_rate="0.00", profit_factor="0.00", total_pnl="0.00",
            average_win="0.00", average_loss="0.00",
            largest_win="0.00", largest_loss="0.00",
            max_drawdown="0.00", max_drawdown_percent="0.00",
            sharpe_ratio=None, sortino_ratio=None,
            expectancy="0.00", average_hold_time="0h",
        )

    # Calculate metrics
    wins = [t for t in closed_trades if t.profit_loss and t.profit_loss > 0]
    losses = [t for t in closed_trades if t.profit_loss and t.profit_loss < 0]
    total = len(closed_trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total * 100) if total > 0 else 0

    total_pnl = sum(t.profit_loss for t in closed_trades if t.profit_loss)
    total_wins = sum(t.profit_loss for t in wins if t.profit_loss)
    total_losses = abs(sum(t.profit_loss for t in losses if t.profit_loss))
    avg_win = (total_wins / win_count) if win_count > 0 else 0
    avg_loss = (total_losses / loss_count) if loss_count > 0 else 0
    profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf') if total_wins > 0 else 0
    largest_win = max((t.profit_loss for t in wins if t.profit_loss), default=0)
    largest_loss = min((t.profit_loss for t in losses if t.profit_loss), default=0)
    expectancy = (total_pnl / total) if total > 0 else 0

    # Max drawdown
    cumulative = 0
    peak = 0
    max_dd = 0
    for t in closed_trades:
        cumulative += (t.profit_loss or 0)
        if cumulative > peak:
            peak = cumulative
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd

    # Average hold time
    hold_times = []
    for t in closed_trades:
        if t.exit_timestamp and t.timestamp:
            delta = t.exit_timestamp - t.timestamp
            hold_times.append(delta.total_seconds() / 3600)  # hours
    avg_hold = f"{sum(hold_times) / len(hold_times):.1f}h" if hold_times else "N/A"

    return PerformanceMetrics(
        total_trades=total,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate=f"{win_rate:.2f}",
        profit_factor=f"{profit_factor:.2f}" if profit_factor != float('inf') else "∞",
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
