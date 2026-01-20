"""
Auto Trader Bot - Fully autonomous trading system.

This bot:
1. Runs continuously in the background
2. Analyzes configured assets at specified intervals
3. Uses multi-timeframe + visual AI analysis
4. Executes trades automatically when consensus is strong
5. Manages positions with stop-loss and take-profit
6. Sends notifications on trades
"""

import asyncio
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from src.engines.ai.multi_timeframe_analyzer import (
    MultiTimeframeAnalyzer,
    MultiTimeframeResult,
    AnalysisMode,
    get_multi_timeframe_analyzer,
)
from src.engines.trading.broker_factory import BrokerFactory
from src.engines.trading.base_broker import BaseBroker, OrderRequest, OrderType, OrderSide
from src.core.config import settings


class BotStatus(str, Enum):
    """Bot status states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class TradeRecord:
    """Record of an executed trade."""
    id: str
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    units: float
    timestamp: datetime
    confidence: float
    timeframes_analyzed: List[str]
    models_agreed: int
    total_models: int
    status: str = "open"  # open, closed_tp, closed_sl, closed_manual
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    profit_loss: Optional[float] = None


@dataclass
class BotConfig:
    """Configuration for the auto trading bot."""
    # Assets to trade
    symbols: List[str] = field(default_factory=lambda: ["EUR/USD", "GBP/USD", "XAU/USD"])

    # Analysis settings
    analysis_mode: AnalysisMode = AnalysisMode.PREMIUM
    analysis_interval_seconds: int = 300  # 5 minutes

    # Entry requirements
    min_confidence: float = 70.0  # Minimum consensus confidence to enter
    min_models_agree: int = 4     # Minimum models agreeing on direction (4 out of 6)
    min_confluence: float = 65.0  # Minimum timeframe confluence score

    # Risk management
    risk_per_trade_percent: float = 1.0  # Risk 1% of account per trade
    max_open_positions: int = 3
    max_daily_trades: int = 10
    max_daily_loss_percent: float = 5.0  # Stop trading if daily loss exceeds this

    # Trading hours (UTC)
    trading_start_hour: int = 7   # Start trading at 7 UTC
    trading_end_hour: int = 21    # Stop trading at 21 UTC
    trade_on_weekends: bool = False

    # Notifications
    telegram_enabled: bool = False
    discord_enabled: bool = False


@dataclass
class BotState:
    """Current state of the bot."""
    status: BotStatus = BotStatus.STOPPED
    started_at: Optional[datetime] = None
    last_analysis_at: Optional[datetime] = None
    analyses_today: int = 0
    trades_today: int = 0
    daily_pnl: float = 0.0
    open_positions: List[TradeRecord] = field(default_factory=list)
    trade_history: List[TradeRecord] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)


class AutoTrader:
    """
    Autonomous trading bot that runs 24/7.

    Usage:
        bot = AutoTrader()
        bot.configure(BotConfig(...))
        await bot.start()
        # ... bot runs in background ...
        await bot.stop()
    """

    def __init__(self):
        self.config = BotConfig()
        self.state = BotState()
        self.analyzer: Optional[MultiTimeframeAnalyzer] = None
        self.broker: Optional[BaseBroker] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._callbacks: List[Callable] = []

    def configure(self, config: BotConfig):
        """Update bot configuration."""
        self.config = config

    def add_callback(self, callback: Callable):
        """Add a callback for trade notifications."""
        self._callbacks.append(callback)

    async def start(self):
        """Start the trading bot."""
        if self.state.status == BotStatus.RUNNING:
            return

        self.state.status = BotStatus.STARTING
        self.state.started_at = datetime.utcnow()
        self.state.errors = []

        try:
            # Initialize analyzer
            self.analyzer = get_multi_timeframe_analyzer()
            await self.analyzer.initialize()

            # Initialize broker
            self.broker = await BrokerFactory.create_broker()
            await self.broker.connect()

            # Start main loop
            self._stop_event.clear()
            self._task = asyncio.create_task(self._main_loop())
            self.state.status = BotStatus.RUNNING

            await self._notify(f"🤖 Bot started. Monitoring: {', '.join(self.config.symbols)}")

        except Exception as e:
            self.state.status = BotStatus.ERROR
            self.state.errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            })
            raise

    async def stop(self):
        """Stop the trading bot."""
        self._stop_event.set()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self.state.status = BotStatus.STOPPED
        await self._notify("🛑 Bot stopped.")

    async def pause(self):
        """Pause trading (continues monitoring but no new trades)."""
        self.state.status = BotStatus.PAUSED
        await self._notify("⏸️ Bot paused. Monitoring continues, no new trades.")

    async def resume(self):
        """Resume trading after pause."""
        self.state.status = BotStatus.RUNNING
        await self._notify("▶️ Bot resumed. Trading active.")

    def get_status(self) -> Dict[str, Any]:
        """Get current bot status and statistics."""
        return {
            "status": self.state.status.value,
            "started_at": self.state.started_at.isoformat() if self.state.started_at else None,
            "last_analysis_at": self.state.last_analysis_at.isoformat() if self.state.last_analysis_at else None,
            "config": {
                "symbols": self.config.symbols,
                "analysis_mode": self.config.analysis_mode.value,
                "min_confidence": self.config.min_confidence,
                "risk_per_trade": self.config.risk_per_trade_percent,
                "max_positions": self.config.max_open_positions,
            },
            "statistics": {
                "analyses_today": self.state.analyses_today,
                "trades_today": self.state.trades_today,
                "daily_pnl": self.state.daily_pnl,
                "open_positions": len(self.state.open_positions),
            },
            "open_positions": [
                {
                    "symbol": p.symbol,
                    "direction": p.direction,
                    "entry": p.entry_price,
                    "sl": p.stop_loss,
                    "tp": p.take_profit,
                    "confidence": p.confidence,
                }
                for p in self.state.open_positions
            ],
            "recent_errors": self.state.errors[-5:],
        }

    async def _main_loop(self):
        """Main trading loop."""
        while not self._stop_event.is_set():
            try:
                # Check trading hours
                if not self._is_trading_hours():
                    await asyncio.sleep(60)  # Check every minute
                    continue

                # Check daily limits
                if self._daily_limits_reached():
                    await asyncio.sleep(300)  # Check every 5 minutes
                    continue

                # Only trade if running (not paused)
                if self.state.status == BotStatus.RUNNING:
                    await self._analyze_and_trade()

                self.state.last_analysis_at = datetime.utcnow()
                self.state.analyses_today += 1

                # Wait for next interval
                await asyncio.sleep(self.config.analysis_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.state.errors.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e)
                })
                await asyncio.sleep(60)  # Wait before retrying

    async def _analyze_and_trade(self):
        """Analyze all symbols and execute trades if conditions met."""
        for symbol in self.config.symbols:
            try:
                # Skip if max positions reached
                if len(self.state.open_positions) >= self.config.max_open_positions:
                    continue

                # Skip if already have position in this symbol
                if any(p.symbol == symbol for p in self.state.open_positions):
                    continue

                # Run analysis
                result = await self.analyzer.analyze(
                    symbol=symbol,
                    mode=self.config.analysis_mode
                )

                # Check if trade conditions are met
                if self._should_enter_trade(result):
                    await self._execute_trade(result)

            except Exception as e:
                self.state.errors.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "error": str(e)
                })

    def _should_enter_trade(self, result: MultiTimeframeResult) -> bool:
        """Check if analysis result meets trading criteria."""
        # Must have a direction (not HOLD)
        if result.final_direction == "HOLD":
            return False

        # Confidence check
        if result.final_confidence < self.config.min_confidence:
            return False

        # Model agreement check
        if result.total_models_used < self.config.min_models_agree:
            return False

        # Confluence check
        if result.confluence_score < self.config.min_confluence:
            return False

        # Must have stop loss and take profit
        if not result.stop_loss or not result.take_profit:
            return False

        return True

    async def _execute_trade(self, result: MultiTimeframeResult):
        """Execute a trade based on analysis result."""
        try:
            # Get current price
            price = await self.broker.get_price(result.symbol)
            current_price = (price["bid"] + price["ask"]) / 2

            # Calculate position size
            account_info = await self.broker.get_account_info()
            account_balance = account_info.get("balance", 10000)

            risk_amount = account_balance * (self.config.risk_per_trade_percent / 100)
            sl_distance = abs(current_price - result.stop_loss)

            if sl_distance == 0:
                return

            # Units = risk amount / stop loss distance
            units = risk_amount / sl_distance

            # Determine order side
            side = OrderSide.BUY if result.final_direction == "LONG" else OrderSide.SELL

            # Create order
            order = OrderRequest(
                symbol=result.symbol,
                side=side,
                order_type=OrderType.MARKET,
                units=units,
                stop_loss=result.stop_loss,
                take_profit=result.take_profit[0] if result.take_profit else None,
            )

            # Execute order
            order_result = await self.broker.place_order(order)

            if order_result.success:
                # Record trade
                trade = TradeRecord(
                    id=order_result.order_id,
                    symbol=result.symbol,
                    direction=result.final_direction,
                    entry_price=order_result.fill_price or current_price,
                    stop_loss=result.stop_loss,
                    take_profit=result.take_profit[0] if result.take_profit else 0,
                    units=units,
                    timestamp=datetime.utcnow(),
                    confidence=result.final_confidence,
                    timeframes_analyzed=list(result.timeframe_analyses.keys()),
                    models_agreed=result.total_models_used,
                    total_models=result.total_models_used,
                )

                self.state.open_positions.append(trade)
                self.state.trades_today += 1

                # Send notification
                await self._notify_trade(trade, result)

        except Exception as e:
            self.state.errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "action": "execute_trade",
                "symbol": result.symbol,
                "error": str(e)
            })

    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours."""
        now = datetime.utcnow()

        # Weekend check
        if not self.config.trade_on_weekends and now.weekday() >= 5:
            return False

        # Hour check
        if not (self.config.trading_start_hour <= now.hour < self.config.trading_end_hour):
            return False

        return True

    def _daily_limits_reached(self) -> bool:
        """Check if daily trading limits are reached."""
        # Max trades check
        if self.state.trades_today >= self.config.max_daily_trades:
            return True

        # Max loss check
        if self.state.daily_pnl < -(self.config.max_daily_loss_percent):
            return True

        return False

    async def _notify(self, message: str):
        """Send notification to all channels."""
        for callback in self._callbacks:
            try:
                await callback(message)
            except Exception:
                pass

        # Telegram notification
        if self.config.telegram_enabled and settings.TELEGRAM_BOT_TOKEN:
            await self._send_telegram(message)

        # Discord notification
        if self.config.discord_enabled and settings.DISCORD_WEBHOOK_URL:
            await self._send_discord(message)

    async def _notify_trade(self, trade: TradeRecord, result: MultiTimeframeResult):
        """Send detailed trade notification."""
        direction_emoji = "🟢" if trade.direction == "LONG" else "🔴"

        message = f"""
{direction_emoji} **NEW TRADE EXECUTED**

**Symbol:** {trade.symbol}
**Direction:** {trade.direction}
**Entry:** {trade.entry_price:.5f}
**Stop Loss:** {trade.stop_loss:.5f}
**Take Profit:** {trade.take_profit:.5f}
**Units:** {trade.units:.2f}

**Analysis:**
- Confidence: {trade.confidence:.1f}%
- Timeframes: {', '.join(trade.timeframes_analyzed)}
- Models agreed: {trade.models_agreed}
- Confluence: {result.confluence_score:.1f}%

_Trade ID: {trade.id}_
"""
        await self._notify(message)

    async def _send_telegram(self, message: str):
        """Send Telegram notification."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                    json={
                        "chat_id": settings.TELEGRAM_CHAT_ID,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                )
        except Exception:
            pass

    async def _send_discord(self, message: str):
        """Send Discord notification."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    settings.DISCORD_WEBHOOK_URL,
                    json={"content": message}
                )
        except Exception:
            pass


# Global bot instance
_auto_trader: Optional[AutoTrader] = None


def get_auto_trader() -> AutoTrader:
    """Get or create the auto trader singleton."""
    global _auto_trader
    if _auto_trader is None:
        _auto_trader = AutoTrader()
    return _auto_trader
