"""
Bot Control API - Endpoints to manage the auto trading bot.
Bot configuration is persisted to database.
"""

import json
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import AppSettings
from src.engines.trading.auto_trader import (
    AnalysisMode,
    BotStatus,
    get_auto_trader,
)

router = APIRouter(prefix="/bot", tags=["Bot Control"])


# ============ Database Helper Functions ============

async def get_bot_config_from_db(db: AsyncSession) -> dict | None:
    """Load bot config from database."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "bot_config")
    )
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except Exception:
            pass
    return None


async def save_bot_config_to_db(db: AsyncSession, config_dict: dict) -> None:
    """Save bot config to database."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "bot_config")
    )
    setting = result.scalar_one_or_none()

    config_json = json.dumps(config_dict)
    if setting:
        setting.value = config_json
    else:
        setting = AppSettings(key="bot_config", value=config_json)
        db.add(setting)

    await db.commit()


async def _save_trade_history_to_db(db: AsyncSession, trades: list) -> None:
    """Save trade history to database for persistence across restarts."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "trade_history")
    )
    setting = result.scalar_one_or_none()

    # Keep last 200 trades to avoid bloating the DB
    trades_to_save = trades[-200:] if len(trades) > 200 else trades
    trades_json = json.dumps(trades_to_save)
    if setting:
        setting.value = trades_json
    else:
        setting = AppSettings(key="trade_history", value=trades_json)
        db.add(setting)

    await db.commit()


async def _load_trade_history_from_db(db: AsyncSession) -> list:
    """Load trade history from database."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == "trade_history")
    )
    setting = result.scalar_one_or_none()
    if setting and setting.value:
        try:
            return json.loads(setting.value)
        except Exception:
            pass
    return []


def apply_config_to_bot(config_dict: dict) -> None:
    """Apply loaded config to the bot instance."""
    bot = get_auto_trader()

    if "symbols" in config_dict:
        bot.config.symbols = config_dict["symbols"]
    if "analysis_mode" in config_dict:
        try:
            bot.config.analysis_mode = AnalysisMode(config_dict["analysis_mode"])
        except ValueError:
            pass
    if "analysis_interval_seconds" in config_dict:
        bot.config.analysis_interval_seconds = config_dict["analysis_interval_seconds"]
    if "min_confidence" in config_dict:
        bot.config.min_confidence = config_dict["min_confidence"]
    if "min_models_agree" in config_dict:
        bot.config.min_models_agree = config_dict["min_models_agree"]
    if "min_confluence" in config_dict:
        bot.config.min_confluence = config_dict["min_confluence"]
    if "risk_per_trade_percent" in config_dict:
        bot.config.risk_per_trade_percent = config_dict["risk_per_trade_percent"]
    if "max_open_positions" in config_dict:
        bot.config.max_open_positions = config_dict["max_open_positions"]
    if "max_daily_trades" in config_dict:
        bot.config.max_daily_trades = config_dict["max_daily_trades"]
    if "max_daily_loss_percent" in config_dict:
        bot.config.max_daily_loss_percent = config_dict["max_daily_loss_percent"]
    if "trading_start_hour" in config_dict:
        bot.config.trading_start_hour = config_dict["trading_start_hour"]
    if "trading_end_hour" in config_dict:
        bot.config.trading_end_hour = config_dict["trading_end_hour"]
    if "trade_on_weekends" in config_dict:
        bot.config.trade_on_weekends = config_dict["trade_on_weekends"]
    if "telegram_enabled" in config_dict:
        bot.config.telegram_enabled = config_dict["telegram_enabled"]
    if "discord_enabled" in config_dict:
        bot.config.discord_enabled = config_dict["discord_enabled"]
    if "use_autonomous_analysis" in config_dict:
        bot.config.use_autonomous_analysis = config_dict["use_autonomous_analysis"]
    if "autonomous_timeframe" in config_dict:
        bot.config.autonomous_timeframe = config_dict["autonomous_timeframe"]
    if "use_tradingview_agent" in config_dict:
        bot.config.use_tradingview_agent = config_dict["use_tradingview_agent"]
    if "tradingview_headless" in config_dict:
        bot.config.tradingview_headless = config_dict["tradingview_headless"]
    if "tradingview_max_indicators" in config_dict:
        bot.config.tradingview_max_indicators = config_dict["tradingview_max_indicators"]
    # AI Models
    if "enabled_models" in config_dict:
        valid_models = ["chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"]
        enabled = [m for m in config_dict["enabled_models"] if m in valid_models]
        if enabled:  # Almeno 1 modello deve restare abilitato
            bot.config.enabled_models = enabled
    # News Filter settings
    if "news_filter_enabled" in config_dict:
        bot.config.news_filter_enabled = config_dict["news_filter_enabled"]
    if "news_filter_high_impact" in config_dict:
        bot.config.news_filter_high_impact = config_dict["news_filter_high_impact"]
    if "news_filter_medium_impact" in config_dict:
        bot.config.news_filter_medium_impact = config_dict["news_filter_medium_impact"]
    if "news_filter_low_impact" in config_dict:
        bot.config.news_filter_low_impact = config_dict["news_filter_low_impact"]
    if "news_minutes_before" in config_dict:
        bot.config.news_minutes_before = config_dict["news_minutes_before"]
    if "news_minutes_after" in config_dict:
        bot.config.news_minutes_after = config_dict["news_minutes_after"]


class BotConfigRequest(BaseModel):
    """Request model for bot configuration."""
    symbols: list[str] | None = None
    analysis_mode: str | None = None
    analysis_interval_seconds: int | None = None
    min_confidence: float | None = None
    min_models_agree: int | None = None
    min_confluence: float | None = None
    risk_per_trade_percent: float | None = None
    max_open_positions: int | None = None
    max_daily_trades: int | None = None
    max_daily_loss_percent: float | None = None
    trading_start_hour: int | None = None
    trading_end_hour: int | None = None
    trade_on_weekends: bool | None = None
    telegram_enabled: bool | None = None
    discord_enabled: bool | None = None
    # Autonomous Analysis settings
    use_autonomous_analysis: bool | None = None
    autonomous_timeframe: str | None = None
    # TradingView AI Agent settings
    use_tradingview_agent: bool | None = None
    tradingview_headless: bool | None = None
    tradingview_max_indicators: int | None = None
    # AI Models - enable/disable individual models
    enabled_models: list[str] | None = None
    # News Filter settings
    news_filter_enabled: bool | None = None
    news_filter_high_impact: bool | None = None
    news_filter_medium_impact: bool | None = None
    news_filter_low_impact: bool | None = None
    news_minutes_before: int | None = None
    news_minutes_after: int | None = None


class BotStatusResponse(BaseModel):
    """Response model for bot status."""
    status: str
    started_at: str | None
    last_analysis_at: str | None
    config: dict
    statistics: dict
    open_positions: list
    recent_errors: list


@router.get("/status", response_model=BotStatusResponse)
async def get_bot_status():
    """Get current bot status and statistics."""
    bot = get_auto_trader()
    return bot.get_status()


@router.post("/start")
async def start_bot():
    """Start the auto trading bot."""
    import traceback
    bot = get_auto_trader()

    if bot.state.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is already running")

    try:
        await bot.start()
        return {"message": "Bot started successfully", "status": bot.state.status.value}
    except Exception as e:
        # Log full traceback for debugging
        error_traceback = traceback.format_exc()
        print(f"[BOT START ERROR] Full traceback:\n{error_traceback}")
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@router.post("/stop")
async def stop_bot():
    """Stop the auto trading bot."""
    bot = get_auto_trader()

    if bot.state.status == BotStatus.STOPPED:
        raise HTTPException(status_code=400, detail="Bot is already stopped")

    await bot.stop()
    return {"message": "Bot stopped successfully", "status": bot.state.status.value}


@router.post("/reset")
async def reset_bot():
    """Force reset the bot state. Use when bot is stuck."""
    import src.engines.trading.auto_trader as auto_trader_module

    bot = get_auto_trader()

    # Force stop any running tasks
    if bot._task:
        bot._task.cancel()
        try:
            await bot._task
        except Exception:
            pass

    # Reset state
    bot.state.status = BotStatus.STOPPED
    bot.state.started_at = None
    bot._task = None

    # Clear singleton to get fresh instance next time
    auto_trader_module._auto_trader = None

    return {"message": "Bot reset successfully", "status": "stopped"}


@router.post("/pause")
async def pause_bot():
    """Pause trading (monitoring continues)."""
    bot = get_auto_trader()

    if bot.state.status != BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is not running")

    await bot.pause()
    return {"message": "Bot paused", "status": bot.state.status.value}


@router.post("/resume")
async def resume_bot():
    """Resume trading after pause."""
    bot = get_auto_trader()

    if bot.state.status != BotStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Bot is not paused")

    await bot.resume()
    return {"message": "Bot resumed", "status": bot.state.status.value}


@router.put("/config")
async def update_config(config: BotConfigRequest, db: AsyncSession = Depends(get_db)):
    """Update bot configuration. Persists to database."""
    bot = get_auto_trader()
    current_config = bot.config

    # Update only provided fields
    if config.symbols is not None:
        current_config.symbols = config.symbols

    if config.analysis_mode is not None:
        try:
            current_config.analysis_mode = AnalysisMode(config.analysis_mode)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid analysis mode: {config.analysis_mode}")

    if config.analysis_interval_seconds is not None:
        if config.analysis_interval_seconds < 60:
            raise HTTPException(status_code=400, detail="Interval must be at least 60 seconds")
        current_config.analysis_interval_seconds = config.analysis_interval_seconds

    if config.min_confidence is not None:
        if not 0 <= config.min_confidence <= 100:
            raise HTTPException(status_code=400, detail="Confidence must be between 0 and 100")
        current_config.min_confidence = config.min_confidence

    if config.min_models_agree is not None:
        current_config.min_models_agree = config.min_models_agree

    if config.min_confluence is not None:
        if not 0 <= config.min_confluence <= 100:
            raise HTTPException(status_code=400, detail="Confluence must be between 0 and 100")
        current_config.min_confluence = config.min_confluence

    if config.risk_per_trade_percent is not None:
        if not 0 < config.risk_per_trade_percent <= 10:
            raise HTTPException(status_code=400, detail="Risk per trade must be between 0.1% and 10%")
        current_config.risk_per_trade_percent = config.risk_per_trade_percent

    if config.max_open_positions is not None:
        current_config.max_open_positions = config.max_open_positions

    if config.max_daily_trades is not None:
        current_config.max_daily_trades = config.max_daily_trades

    if config.max_daily_loss_percent is not None:
        current_config.max_daily_loss_percent = config.max_daily_loss_percent

    if config.trading_start_hour is not None:
        if not 0 <= config.trading_start_hour <= 23:
            raise HTTPException(status_code=400, detail="Trading start hour must be between 0 and 23")
        current_config.trading_start_hour = config.trading_start_hour

    if config.trading_end_hour is not None:
        if not 0 <= config.trading_end_hour <= 23:
            raise HTTPException(status_code=400, detail="Trading end hour must be between 0 and 23")
        current_config.trading_end_hour = config.trading_end_hour

    if config.trade_on_weekends is not None:
        current_config.trade_on_weekends = config.trade_on_weekends

    if config.telegram_enabled is not None:
        current_config.telegram_enabled = config.telegram_enabled

    if config.discord_enabled is not None:
        current_config.discord_enabled = config.discord_enabled

    # Autonomous Analysis settings
    if config.use_autonomous_analysis is not None:
        current_config.use_autonomous_analysis = config.use_autonomous_analysis

    if config.autonomous_timeframe is not None:
        valid_timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        if config.autonomous_timeframe not in valid_timeframes:
            raise HTTPException(status_code=400, detail=f"Invalid timeframe. Valid options: {valid_timeframes}")
        current_config.autonomous_timeframe = config.autonomous_timeframe

    # TradingView AI Agent settings
    if config.use_tradingview_agent is not None:
        current_config.use_tradingview_agent = config.use_tradingview_agent

    if config.tradingview_headless is not None:
        current_config.tradingview_headless = config.tradingview_headless

    if config.tradingview_max_indicators is not None:
        if not 1 <= config.tradingview_max_indicators <= 25:
            raise HTTPException(status_code=400, detail="Max indicators must be between 1 and 25")
        current_config.tradingview_max_indicators = config.tradingview_max_indicators

    # News Filter settings
    if config.news_filter_enabled is not None:
        current_config.news_filter_enabled = config.news_filter_enabled

    if config.news_filter_high_impact is not None:
        current_config.news_filter_high_impact = config.news_filter_high_impact

    if config.news_filter_medium_impact is not None:
        current_config.news_filter_medium_impact = config.news_filter_medium_impact

    if config.news_filter_low_impact is not None:
        current_config.news_filter_low_impact = config.news_filter_low_impact

    if config.news_minutes_before is not None:
        if not 0 <= config.news_minutes_before <= 120:
            raise HTTPException(status_code=400, detail="Minutes before must be between 0 and 120")
        current_config.news_minutes_before = config.news_minutes_before

    if config.news_minutes_after is not None:
        if not 0 <= config.news_minutes_after <= 120:
            raise HTTPException(status_code=400, detail="Minutes after must be between 0 and 120")
        current_config.news_minutes_after = config.news_minutes_after

    # AI Models toggle
    if config.enabled_models is not None:
        valid_models = ["chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"]
        enabled = [m for m in config.enabled_models if m in valid_models]
        if enabled:
            current_config.enabled_models = enabled

    bot.configure(current_config)

    # Save to database for persistence
    config_dict = {
        "symbols": current_config.symbols,
        "analysis_mode": current_config.analysis_mode.value,
        "analysis_interval_seconds": current_config.analysis_interval_seconds,
        "min_confidence": current_config.min_confidence,
        "min_models_agree": current_config.min_models_agree,
        "min_confluence": current_config.min_confluence,
        "risk_per_trade_percent": current_config.risk_per_trade_percent,
        "max_open_positions": current_config.max_open_positions,
        "max_daily_trades": current_config.max_daily_trades,
        "max_daily_loss_percent": current_config.max_daily_loss_percent,
        "trading_start_hour": current_config.trading_start_hour,
        "trading_end_hour": current_config.trading_end_hour,
        "trade_on_weekends": current_config.trade_on_weekends,
        "telegram_enabled": current_config.telegram_enabled,
        "discord_enabled": current_config.discord_enabled,
        "use_autonomous_analysis": current_config.use_autonomous_analysis,
        "autonomous_timeframe": current_config.autonomous_timeframe,
        "use_tradingview_agent": current_config.use_tradingview_agent,
        "tradingview_headless": current_config.tradingview_headless,
        "tradingview_max_indicators": current_config.tradingview_max_indicators,
        # AI Models
        "enabled_models": current_config.enabled_models,
        # News Filter settings
        "news_filter_enabled": current_config.news_filter_enabled,
        "news_filter_high_impact": current_config.news_filter_high_impact,
        "news_filter_medium_impact": current_config.news_filter_medium_impact,
        "news_filter_low_impact": current_config.news_filter_low_impact,
        "news_minutes_before": current_config.news_minutes_before,
        "news_minutes_after": current_config.news_minutes_after,
    }
    await save_bot_config_to_db(db, config_dict)

    return {
        "message": "Configuration updated and saved",
        "config": bot.get_status()["config"]
    }


@router.get("/config")
async def get_config():
    """Get current bot configuration."""
    bot = get_auto_trader()
    config = bot.config

    return {
        "symbols": config.symbols,
        "analysis_mode": config.analysis_mode.value,
        "analysis_interval_seconds": config.analysis_interval_seconds,
        "min_confidence": config.min_confidence,
        "min_models_agree": config.min_models_agree,
        "min_confluence": config.min_confluence,
        "risk_per_trade_percent": config.risk_per_trade_percent,
        "max_open_positions": config.max_open_positions,
        "max_daily_trades": config.max_daily_trades,
        "max_daily_loss_percent": config.max_daily_loss_percent,
        "trading_start_hour": config.trading_start_hour,
        "trading_end_hour": config.trading_end_hour,
        "trade_on_weekends": config.trade_on_weekends,
        "telegram_enabled": config.telegram_enabled,
        "discord_enabled": config.discord_enabled,
        # Autonomous Analysis settings
        "use_autonomous_analysis": config.use_autonomous_analysis,
        "autonomous_timeframe": config.autonomous_timeframe,
        # TradingView AI Agent settings
        "use_tradingview_agent": config.use_tradingview_agent,
        "tradingview_headless": config.tradingview_headless,
        "tradingview_max_indicators": config.tradingview_max_indicators,
        # AI Models
        "enabled_models": config.enabled_models,
        # News Filter settings
        "news_filter_enabled": config.news_filter_enabled,
        "news_filter_high_impact": config.news_filter_high_impact,
        "news_filter_medium_impact": config.news_filter_medium_impact,
        "news_filter_low_impact": config.news_filter_low_impact,
        "news_minutes_before": config.news_minutes_before,
        "news_minutes_after": config.news_minutes_after,
    }


@router.get("/trades")
async def get_trades(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get trade history from bot memory + broker deal history + database."""
    bot = get_auto_trader()

    # 1. Get in-memory bot trades
    trades = []
    seen_ids = set()
    for t in bot.state.trade_history:
        trades.append({
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "units": t.units,
            "timestamp": t.timestamp.isoformat(),
            "exit_timestamp": t.exit_timestamp.isoformat() if t.exit_timestamp else None,
            "confidence": t.confidence,
            "status": t.status,
            "profit_loss": t.profit_loss,
        })
        seen_ids.add(t.id)

    # 2. Load saved trades from database (persisted across restarts)
    try:
        db_trades = await _load_trade_history_from_db(db)
        for t in db_trades:
            tid = t.get("id", "")
            if tid and tid not in seen_ids:
                trades.append(t)
                seen_ids.add(tid)
    except Exception as e:
        print(f"[Bot/trades] Error loading DB trades: {e}")

    # 3. Also fetch broker deal history (last 30 days) for complete picture
    try:
        from src.services.trading_service import get_trading_service
        service = await get_trading_service()
        if hasattr(service._broker, 'get_deals_history'):
            from datetime import datetime as dt
            from datetime import timedelta
            start = dt.now(UTC) - timedelta(days=30)
            deals = await service._broker.get_deals_history(start.isoformat())
            for deal in deals:
                deal_id = str(deal.get("id", deal.get("dealId", "")))
                if not deal_id or deal_id in seen_ids:
                    continue
                profit = float(deal.get("profit", 0))
                swap = float(deal.get("swap", 0))
                commission = float(deal.get("commission", 0))
                total_pnl = profit + swap + commission
                # Skip balance/credit operations and zero-profit entries without a type
                deal_type = deal.get("type", "")
                if total_pnl == 0 and deal_type not in ("DEAL_TYPE_SELL", "DEAL_TYPE_BUY"):
                    continue
                direction = "LONG" if "BUY" in deal_type else "SHORT" if "SELL" in deal_type else deal_type
                deal_time = deal.get("time", deal.get("brokerTime", ""))
                if not isinstance(deal_time, str):
                    deal_time = str(deal_time)
                trades.append({
                    "id": deal_id,
                    "symbol": deal.get("symbol", "UNKNOWN"),
                    "direction": direction,
                    "entry_price": float(deal.get("price", 0)),
                    "exit_price": float(deal.get("price", 0)),
                    "stop_loss": 0,
                    "take_profit": 0,
                    "units": float(deal.get("volume", 0)),
                    "timestamp": deal_time,
                    "exit_timestamp": deal_time,
                    "confidence": 0,
                    "status": "filled",
                    "profit_loss": total_pnl,
                })
                seen_ids.add(deal_id)
    except Exception as e:
        print(f"[Bot/trades] Error fetching broker deals: {e}")

    # Sort by timestamp descending (most recent first)
    trades.sort(key=lambda t: t.get("timestamp", ""), reverse=True)

    # Save current trade history to DB for persistence
    try:
        await _save_trade_history_to_db(db, trades)
    except Exception as e:
        print(f"[Bot/trades] Error saving trades to DB: {e}")

    total = len(trades)
    return {"trades": trades[:limit], "total": total}


@router.get("/positions")
async def get_open_positions():
    """Get current open positions."""
    bot = get_auto_trader()

    positions = []
    for p in bot.state.open_positions:
        positions.append({
            "id": p.id,
            "symbol": p.symbol,
            "direction": p.direction,
            "entry_price": p.entry_price,
            "stop_loss": p.stop_loss,
            "take_profit": p.take_profit,
            "units": p.units,
            "timestamp": p.timestamp.isoformat(),
            "confidence": p.confidence,
            "timeframes": p.timeframes_analyzed,
        })

    return {"positions": positions}


@router.get("/logs")
async def get_analysis_logs(limit: int = 30):
    """Get recent AI analysis logs from the bot."""
    bot = get_auto_trader()
    logs = bot.state.analysis_logs[-limit:]
    return {
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "symbol": log.symbol,
                "type": log.log_type,
                "message": log.message,
                "details": log.details,
            }
            for log in logs
        ],
        "total": len(bot.state.analysis_logs),
        "bot_status": bot.state.status.value,
    }


@router.get("/news/upcoming")
async def get_upcoming_news(hours: int = 24, impact: str | None = None):
    """
    Get upcoming economic news events.

    Args:
        hours: How many hours to look ahead (default: 24)
        impact: Filter by impact level ("high", "medium", "low", or None for all)
    """
    from src.services.economic_calendar_service import (
        NewsImpact,
        get_economic_calendar_service,
    )

    service = get_economic_calendar_service()

    # Refresh if needed
    await service.fetch_events()

    # Filter by impact if specified
    impact_filter = None
    if impact:
        impact_map = {
            "high": [NewsImpact.HIGH],
            "medium": [NewsImpact.MEDIUM],
            "low": [NewsImpact.LOW],
            "high_medium": [NewsImpact.HIGH, NewsImpact.MEDIUM],
        }
        impact_filter = impact_map.get(impact.lower())

    events = service.get_upcoming_events(hours_ahead=hours, impact_filter=impact_filter)

    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "hours_ahead": hours,
        "filter_config": {
            "enabled": service.config.enabled,
            "filter_high": service.config.filter_high_impact,
            "filter_medium": service.config.filter_medium_impact,
            "minutes_before": service.config.minutes_before,
            "minutes_after": service.config.minutes_after,
        }
    }


@router.get("/news/check/{symbol}")
async def check_news_for_symbol(symbol: str):
    """
    Check if a symbol is blocked by news.

    Returns whether trading should be avoided and the causing event if any.
    """
    from src.services.economic_calendar_service import get_economic_calendar_service

    service = get_economic_calendar_service()
    await service.fetch_events()

    should_avoid, event = service.should_avoid_trading(symbol)

    return {
        "symbol": symbol,
        "blocked": should_avoid,
        "reason": event.to_dict() if event else None,
    }
