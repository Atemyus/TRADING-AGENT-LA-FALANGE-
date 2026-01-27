"""
Bot Control API - Endpoints to manage the auto trading bot.
Bot configuration is persisted to database.
"""

import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import AppSettings
from src.engines.trading.auto_trader import (
    get_auto_trader,
    BotConfig,
    BotStatus,
    AnalysisMode,
)


router = APIRouter(prefix="/bot", tags=["Bot Control"])


# ============ Database Helper Functions ============

async def get_bot_config_from_db(db: AsyncSession) -> Optional[dict]:
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
    if "tradingview_headless" in config_dict:
        bot.config.tradingview_headless = config_dict["tradingview_headless"]
    if "tradingview_max_indicators" in config_dict:
        bot.config.tradingview_max_indicators = config_dict["tradingview_max_indicators"]


class BotConfigRequest(BaseModel):
    """Request model for bot configuration."""
    symbols: Optional[List[str]] = None
    analysis_mode: Optional[str] = None
    analysis_interval_seconds: Optional[int] = None
    min_confidence: Optional[float] = None
    min_models_agree: Optional[int] = None
    min_confluence: Optional[float] = None
    risk_per_trade_percent: Optional[float] = None
    max_open_positions: Optional[int] = None
    max_daily_trades: Optional[int] = None
    max_daily_loss_percent: Optional[float] = None
    trading_start_hour: Optional[int] = None
    trading_end_hour: Optional[int] = None
    trade_on_weekends: Optional[bool] = None
    telegram_enabled: Optional[bool] = None
    discord_enabled: Optional[bool] = None
    # TradingView AI Agent settings
    tradingview_headless: Optional[bool] = None
    tradingview_max_indicators: Optional[int] = None


class BotStatusResponse(BaseModel):
    """Response model for bot status."""
    status: str
    started_at: Optional[str]
    last_analysis_at: Optional[str]
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
    bot = get_auto_trader()

    if bot.state.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is already running")

    try:
        await bot.start()
        return {"message": "Bot started successfully", "status": bot.state.status.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start bot: {str(e)}")


@router.post("/stop")
async def stop_bot():
    """Stop the auto trading bot."""
    bot = get_auto_trader()

    if bot.state.status == BotStatus.STOPPED:
        raise HTTPException(status_code=400, detail="Bot is already stopped")

    await bot.stop()
    return {"message": "Bot stopped successfully", "status": bot.state.status.value}


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

    # TradingView AI Agent settings
    if config.tradingview_headless is not None:
        current_config.tradingview_headless = config.tradingview_headless

    if config.tradingview_max_indicators is not None:
        if not 1 <= config.tradingview_max_indicators <= 25:
            raise HTTPException(status_code=400, detail="Max indicators must be between 1 and 25")
        current_config.tradingview_max_indicators = config.tradingview_max_indicators

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
        "tradingview_headless": current_config.tradingview_headless,
        "tradingview_max_indicators": current_config.tradingview_max_indicators,
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
        # TradingView AI Agent settings
        "tradingview_headless": config.tradingview_headless,
        "tradingview_max_indicators": config.tradingview_max_indicators,
    }


@router.get("/trades")
async def get_trades(limit: int = 50):
    """Get trade history."""
    bot = get_auto_trader()

    trades = []
    for t in bot.state.trade_history[-limit:]:
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

    return {"trades": trades, "total": len(bot.state.trade_history)}


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
