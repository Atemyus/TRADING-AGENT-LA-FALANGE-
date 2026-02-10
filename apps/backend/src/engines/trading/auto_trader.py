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
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from src.engines.ai.autonomous_analyst import (
    AutonomousAnalysisResult,
    AutonomousAnalyst,
)
from src.engines.ai.multi_timeframe_analyzer import (
    AnalysisMode,
    MultiTimeframeAnalyzer,
    MultiTimeframeResult,
    get_multi_timeframe_analyzer,
)

try:
    from src.engines.ai.tradingview_agent import (
        TradingViewAIAgent,
        TradingViewAnalysisResult,
        get_tradingview_agent,
    )
    TRADINGVIEW_AGENT_AVAILABLE = True
except ImportError:
    TRADINGVIEW_AGENT_AVAILABLE = False
    TradingViewAIAgent = None
from src.core.config import settings
from src.engines.trading.base_broker import BaseBroker, OrderRequest, OrderSide, OrderType
from src.engines.trading.broker_factory import BrokerFactory
from src.services.economic_calendar_service import (
    EconomicCalendarService,
    EconomicEvent,
    NewsFilterConfig,
    get_economic_calendar_service,
)


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
    timeframes_analyzed: list[str]
    models_agreed: int
    total_models: int
    status: str = "open"  # open, closed_tp, closed_sl, closed_manual, closed_be
    exit_price: float | None = None
    exit_timestamp: datetime | None = None
    profit_loss: float | None = None

    # Advanced trade management
    break_even_trigger: float | None = None  # Move SL to entry when price hits this
    trailing_stop_pips: float | None = None  # Trail SL by this many pips
    partial_tp_percent: float | None = None  # Close this % at TP1
    is_break_even: bool = False  # Has SL been moved to entry?
    current_trailing_sl: float | None = None  # Current trailing SL level


@dataclass
class BotConfig:
    """Configuration for the auto trading bot."""
    # Assets to trade
    symbols: list[str] = field(default_factory=lambda: ["EUR/USD", "GBP/USD", "XAU/USD"])

    # Analysis settings
    analysis_mode: AnalysisMode = AnalysisMode.PREMIUM
    analysis_interval_seconds: int = 300  # 5 minutes

    # TradingView AI Agent - UNICO motore di analisi
    # Usa Playwright per aprire TradingView.com reale e fare screenshot
    # Ogni AI analizza i grafici reali e dà il suo verdetto
    tradingview_headless: bool = True     # Run browser in headless mode
    tradingview_max_indicators: int = 3   # Max indicators (3=Basic, 5=Essential, 10=Plus, 25=Premium)

    # AI Models - abilita/disabilita singoli modelli
    enabled_models: list[str] = field(default_factory=lambda: [
        "chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"
    ])

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

    # News Filter - Avoid trading during high-impact economic events
    news_filter_enabled: bool = True
    news_filter_high_impact: bool = True   # Filter high impact news
    news_filter_medium_impact: bool = True  # Filter medium impact news
    news_filter_low_impact: bool = False    # Filter low impact news (usually False)
    news_minutes_before: int = 30  # Don't trade X minutes before news
    news_minutes_after: int = 30   # Don't trade X minutes after news

    # Notifications
    telegram_enabled: bool = False
    discord_enabled: bool = False

    # Broker credentials (optional - for multi-broker support)
    # If set, these override environment variables
    broker_type: str | None = None
    metaapi_token: str | None = None
    metaapi_account_id: str | None = None


@dataclass
class AnalysisLogEntry:
    """Log entry for AI analysis activity."""
    timestamp: datetime
    symbol: str
    log_type: str  # "info", "analysis", "trade", "skip", "error", "news"
    message: str
    details: dict[str, Any] | None = None


@dataclass
class BotState:
    """Current state of the bot."""
    status: BotStatus = BotStatus.STOPPED
    started_at: datetime | None = None
    last_analysis_at: datetime | None = None
    analyses_today: int = 0
    trades_today: int = 0
    daily_pnl: float = 0.0
    open_positions: list[TradeRecord] = field(default_factory=list)
    trade_history: list[TradeRecord] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    analysis_logs: list[AnalysisLogEntry] = field(default_factory=list)  # AI reasoning logs


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
        self.analyzer: MultiTimeframeAnalyzer | None = None
        self.autonomous_analyst: AutonomousAnalyst | None = None
        self.tradingview_agent: TradingViewAIAgent | None = None
        self.broker: BaseBroker | None = None
        self.calendar_service: EconomicCalendarService | None = None
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._callbacks: list[Callable] = []
        self._last_news_refresh: datetime | None = None

    def configure(self, config: BotConfig):
        """Update bot configuration."""
        self.config = config

    def _log_analysis(self, symbol: str, log_type: str, message: str, details: dict[str, Any] | None = None):
        """Add an analysis log entry visible from the frontend."""
        entry = AnalysisLogEntry(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            log_type=log_type,
            message=message,
            details=details,
        )
        self.state.analysis_logs.append(entry)
        # Keep last 500 entries
        if len(self.state.analysis_logs) > 500:
            self.state.analysis_logs = self.state.analysis_logs[-500:]

    def _get_price_decimals(self, symbol: str) -> int:
        """Restituisce il numero di decimali corretto per il prezzo dello strumento."""
        sym = symbol.upper().replace("/", "").replace("_", "")
        if "JPY" in sym:
            return 3  # Es: 153.581
        if "XAU" in sym or "GOLD" in sym:
            return 2  # Es: 2650.50
        if any(idx in sym for idx in ["US30", "US500", "NAS100", "DE40", "UK100", "JP225", "FR40", "EU50"]):
            return 1  # Es: 42150.5
        return 5  # Forex standard: Es: 1.08542

    def _round_price(self, symbol: str, price: float) -> float:
        """Arrotonda il prezzo al numero di decimali corretto per lo strumento."""
        return round(price, self._get_price_decimals(symbol))

    def _get_pip_size(self, symbol: str) -> float:
        """Restituisce la dimensione di 1 pip per lo strumento."""
        sym = symbol.upper().replace("/", "").replace("_", "")

        # JPY pairs: 1 pip = 0.01
        if "JPY" in sym:
            return 0.01
        # Oro: 1 pip = 0.10 ($)
        if "XAU" in sym or "GOLD" in sym:
            return 0.10
        # Argento: 1 pip = 0.01
        if "XAG" in sym or "SILVER" in sym:
            return 0.01
        # Indici: 1 pip = 1.0 punto
        if any(idx in sym for idx in ["US30", "US500", "NAS100", "DE40", "UK100", "JP225", "FR40", "EU50"]):
            return 1.0
        # Petrolio: 1 pip = 0.01
        if any(oil in sym for oil in ["WTI", "BRENT", "OIL", "USOIL", "UKOIL"]):
            return 0.01
        # Forex standard: 1 pip = 0.0001
        return 0.0001

    def _calculate_pip_info(self, symbol: str, current_price: float, sl_distance: float, broker_spec: dict[str, Any] | None = None) -> tuple:
        """
        Calcola la distanza SL in pips e il valore di 1 pip per 1 lotto standard.
        Restituisce (sl_pips, pip_value_per_lot).

        Se broker_spec è fornito (da broker.get_symbol_specification()), usa i valori reali
        del broker per calcolare il pip value corretto.
        """
        sym = symbol.upper().replace("/", "").replace("_", "")
        pip_size = self._get_pip_size(symbol)
        sl_pips = sl_distance / pip_size

        # Se abbiamo le specifiche dal broker, usiamo tickValue per calcolo preciso
        if broker_spec:
            tick_value = broker_spec.get("tickValue")
            tick_size = broker_spec.get("tickSize")
            contract_size = broker_spec.get("contractSize")

            if tick_value and tick_size and tick_size > 0:
                # pip_value = tickValue * (pipSize / tickSize)
                # Questo ci dà il valore di 1 pip per 1 lotto
                pip_value = tick_value * (pip_size / tick_size)
                self._log_analysis(symbol, "info", f"📊 Broker spec: tickValue={tick_value}, tickSize={tick_size}, contractSize={contract_size} → pip_value=${pip_value:.2f}/lotto")
                return (sl_pips, pip_value)

        # Fallback: valori stimati per tipo di strumento
        # NOTA: I valori per gli indici CFD dipendono MOLTO dal broker
        # La maggior parte dei broker MT usa contract size elevati (10-100)

        if "XAU" in sym or "GOLD" in sym:
            # Oro: 1 lotto = 100 oz, 1 pip ($0.10) × 100 oz = $10 per pip/lotto
            pip_value = 10.0
        elif "XAG" in sym or "SILVER" in sym:
            # Argento: 1 lotto = 5000 oz, 1 pip ($0.01) × 5000 oz = $50 per pip/lotto
            pip_value = 50.0
        elif any(oil in sym for oil in ["WTI", "BRENT", "OIL", "USOIL", "UKOIL"]):
            # Petrolio: 1 lotto = 1000 barili, 1 pip ($0.01) × 1000 = $10 per pip/lotto
            pip_value = 10.0
        elif any(idx in sym for idx in ["US30", "US500", "NAS100", "DE40", "UK100", "JP225", "FR40", "EU50"]):
            # INDICI CFD: La maggior parte dei broker MetaTrader usa contract size alti
            # Tipicamente: 1 punto = $1-$10 per 0.01 lotti → $100-$1000 per 1 lotto
            # Usiamo valori conservativi basati su broker comuni (IC Markets, Pepperstone, etc.)
            if "US30" in sym:
                # DJ30: tipicamente $5-$10 per punto per 1 lotto
                pip_value = 5.0
            elif "NAS100" in sym:
                # NAS100: tipicamente $1-$2 per punto per 0.1 lotti → $10-$20 per 1 lotto
                pip_value = 10.0
            elif "US500" in sym:
                # S&P500: tipicamente $10-$50 per punto per 1 lotto
                pip_value = 10.0
            elif "DE40" in sym:
                # DAX: tipicamente €25 per punto per 1 lotto
                pip_value = 25.0
            elif "EU50" in sym or "FR40" in sym:
                pip_value = 10.0
            elif "UK100" in sym:
                # FTSE: tipicamente £10 per punto per 1 lotto
                pip_value = 12.0
            elif "JP225" in sym:
                # Nikkei: tipicamente ¥100 per punto → ~$0.7 per 1 lotto
                pip_value = 5.0
            else:
                pip_value = 10.0
        elif "JPY" in sym:
            # JPY pairs: 1 pip (0.01) × 100,000 unità / prezzo ≈ $6.7 (varia)
            pip_value = (0.01 * 100000) / current_price if current_price > 0 else 6.7
        else:
            # Forex standard (EUR/USD, GBP/USD, ecc.):
            # 1 pip (0.0001) × 100,000 unità = $10 per pip/lotto (coppie con USD come quote)
            pip_value = 10.0

        return (sl_pips, pip_value)

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
            print("[AutoTrader] Starting bot initialization...")

            # Initialize analyzer (standard multi-timeframe - kept for potential future use)
            print("[AutoTrader] Initializing multi-timeframe analyzer...")
            self.analyzer = get_multi_timeframe_analyzer()
            await self.analyzer.initialize()
            print("[AutoTrader] Multi-timeframe analyzer ready")

            # Initialize TradingView Agent - UNICO motore di analisi
            print("[AutoTrader] Initializing TradingView Agent (Playwright browser)...")
            self._log_analysis("SYSTEM", "info", "🌐 Avvio TradingView Agent con browser Playwright...")

            if not TRADINGVIEW_AGENT_AVAILABLE:
                error_msg = "❌ Playwright non disponibile. Installa con: pip install playwright && playwright install chromium"
                self._log_analysis("SYSTEM", "error", error_msg)
                print(f"[AutoTrader] FATAL: {error_msg}")
                raise RuntimeError(error_msg)

            self.tradingview_agent = await get_tradingview_agent(
                headless=self.config.tradingview_headless,
                max_indicators=self.config.tradingview_max_indicators
            )
            self._log_analysis("SYSTEM", "info", "✅ TradingView Agent pronto - analisi su dati reali TradingView")
            print("[AutoTrader] TradingView Agent ready")

            # Initialize broker
            print("[AutoTrader] Initializing broker connection...")
            # Use config credentials if available (multi-broker support)
            # Otherwise fall back to environment variables
            if self.config.metaapi_token and self.config.metaapi_account_id:
                print(f"[AutoTrader] Using broker credentials from config (account: ...{self.config.metaapi_account_id[-4:] if self.config.metaapi_account_id else 'N/A'})")
                self.broker = BrokerFactory.create(
                    broker_type=self.config.broker_type or "metatrader",
                    access_token=self.config.metaapi_token,
                    account_id=self.config.metaapi_account_id,
                )
            else:
                print("[AutoTrader] Using broker credentials from environment variables")
                self.broker = BrokerFactory.create()
            await self.broker.connect()
            print("[AutoTrader] Broker connected")

            # Initialize economic calendar service (news filter)
            if self.config.news_filter_enabled:
                print("[AutoTrader] Initializing news filter...")
                self.calendar_service = get_economic_calendar_service()
                self.calendar_service.configure(NewsFilterConfig(
                    enabled=self.config.news_filter_enabled,
                    filter_high_impact=self.config.news_filter_high_impact,
                    filter_medium_impact=self.config.news_filter_medium_impact,
                    filter_low_impact=self.config.news_filter_low_impact,
                    minutes_before=self.config.news_minutes_before,
                    minutes_after=self.config.news_minutes_after,
                ))
                try:
                    await self.calendar_service.fetch_events()
                    print(f"[AutoTrader] News filter enabled: {self.config.news_minutes_before}min before, {self.config.news_minutes_after}min after")
                except Exception as news_err:
                    # Non-critical error - continue without news filter
                    print(f"[AutoTrader] Warning: Could not fetch news events: {news_err}")

            # Check API key configuration and warn in logs
            if not settings.AIML_API_KEY:
                warning_msg = "⚠️ AIML_API_KEY NON CONFIGURATA! Le analisi AI NON faranno chiamate API reali. I crediti API non scaleranno. Configura AIML_API_KEY nelle variabili d'ambiente."
                print(f"[AutoTrader] {warning_msg}")
                self._log_analysis("SYSTEM", "error", warning_msg)
            else:
                key_preview = settings.AIML_API_KEY[:8] + "..." if len(settings.AIML_API_KEY) > 8 else "***"
                self._log_analysis("SYSTEM", "info", f"✅ AIML API Key configurata ({key_preview}) - Le chiamate AI saranno reali")
                print(f"[AutoTrader] AIML API key configured: {key_preview}")

            # Start main loop
            print("[AutoTrader] Starting main trading loop...")
            self._stop_event.clear()
            self._task = asyncio.create_task(self._main_loop())
            self.state.status = BotStatus.RUNNING

            await self._notify(f"🤖 Bot started (TradingView AI Agent). Monitoring: {', '.join(self.config.symbols)}")
            print("[AutoTrader] Bot started successfully with TradingView AI Agent")

        except Exception as e:
            import traceback
            print(f"[AutoTrader] ERROR during start: {str(e)}")
            print(f"[AutoTrader] Full traceback:\n{traceback.format_exc()}")
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

    def get_status(self) -> dict[str, Any]:
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
                "analysis_engine": "TradingView AI Agent",
                "enabled_models": self.config.enabled_models,
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
            "analysis_logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "symbol": log.symbol,
                    "type": log.log_type,
                    "message": log.message,
                    "details": log.details,
                }
                for log in self.state.analysis_logs[-30:]  # Last 30 entries
            ],
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

    async def _manage_open_positions(self):
        """Manage open positions: sync with broker, Break Even, Trailing Stop."""
        # ====== SYNC: rimuovi posizioni chiuse dal broker ======
        try:
            broker_positions = await self.broker.get_positions()
            broker_symbols = {p.symbol for p in broker_positions}
            # Also map symbols without suffix (e.g., EURUSDm -> EURUSD)
            broker_symbols_clean = set()
            for s in broker_symbols:
                broker_symbols_clean.add(s)
                # Remove common broker suffixes
                for suffix in ('m', '.a', '.b', '.c', '.i', '.e', '_SB', '.pro', '.raw'):
                    if s.endswith(suffix):
                        broker_symbols_clean.add(s[:-len(suffix)])

            closed_trades = []
            for trade in self.state.open_positions:
                # Normalize trade symbol for comparison
                trade_symbol_variants = {trade.symbol}
                normalized = trade.symbol.replace("_", "").replace("/", "")
                trade_symbol_variants.add(normalized)

                # Check if any variant exists in broker positions
                is_still_open = bool(trade_symbol_variants & broker_symbols_clean)

                if not is_still_open:
                    # Position closed by broker (SL/TP hit or manual close)
                    trade.status = "closed"
                    trade.exit_timestamp = datetime.utcnow()

                    # Try to get final P&L from current price
                    try:
                        tick = await self.broker.get_current_price(trade.symbol)
                        exit_price = float(tick.mid)
                        trade.exit_price = exit_price
                        if trade.direction == "LONG":
                            trade.profit_loss = (exit_price - trade.entry_price) * trade.units
                        else:
                            trade.profit_loss = (trade.entry_price - exit_price) * trade.units
                    except Exception:
                        trade.exit_price = None
                        trade.profit_loss = None

                    closed_trades.append(trade)
                    self.state.trade_history.append(trade)
                    self._log_analysis(trade.symbol, "trade",
                        f"📕 Posizione CHIUSA (rilevata dal broker) | P&L: {trade.profit_loss or 'N/A'}")

            # Remove closed trades from open_positions
            if closed_trades:
                self.state.open_positions = [
                    t for t in self.state.open_positions if t not in closed_trades
                ]
                self._log_analysis("ALL", "info",
                    f"🔄 Sync broker: {len(closed_trades)} posizioni chiuse rimosse, {len(self.state.open_positions)} ancora aperte")

        except Exception as e:
            print(f"[AutoTrader] Error syncing positions with broker: {e}")

        # ====== Gestione posizioni aperte: BE, Trailing Stop ======
        for trade in self.state.open_positions:
            try:
                tick = await self.broker.get_current_price(trade.symbol)
                current_price = float(tick.mid)

                # Check Break Even
                if trade.break_even_trigger and not trade.is_break_even:
                    should_move_be = False
                    if trade.direction == "LONG" and current_price >= trade.break_even_trigger:
                        should_move_be = True
                    elif trade.direction == "SHORT" and current_price <= trade.break_even_trigger:
                        should_move_be = True

                    if should_move_be:
                        # Move SL to entry price using modify_position
                        from decimal import Decimal
                        await self.broker.modify_position(
                            symbol=trade.symbol,
                            stop_loss=Decimal(str(trade.entry_price))
                        )
                        trade.stop_loss = trade.entry_price
                        trade.is_break_even = True
                        await self._notify(f"🔒 {trade.symbol} Break Even attivato a {trade.entry_price:.5f}")

                # Check Trailing Stop
                if trade.trailing_stop_pips and trade.is_break_even:
                    pip_size = self._get_pip_size(trade.symbol)
                    trail_distance = trade.trailing_stop_pips * pip_size

                    new_sl = None
                    if trade.direction == "LONG":
                        potential_sl = current_price - trail_distance
                        if potential_sl > trade.stop_loss:
                            new_sl = potential_sl
                    elif trade.direction == "SHORT":
                        potential_sl = current_price + trail_distance
                        if potential_sl < trade.stop_loss:
                            new_sl = potential_sl

                    if new_sl:
                        from decimal import Decimal
                        await self.broker.modify_position(
                            symbol=trade.symbol,
                            stop_loss=Decimal(str(new_sl))
                        )
                        trade.stop_loss = new_sl
                        trade.current_trailing_sl = new_sl
                        await self._notify(f"📈 {trade.symbol} Trailing Stop aggiornato a {new_sl:.5f}")

            except Exception as e:
                self.state.errors.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": trade.symbol,
                    "error": f"Position management failed: {str(e)}"
                })

    async def _refresh_news_calendar(self):
        """Refresh economic calendar periodically."""
        if not self.calendar_service:
            return

        now = datetime.utcnow()
        # Refresh every hour
        if self._last_news_refresh is None or (now - self._last_news_refresh).total_seconds() > 3600:
            await self.calendar_service.fetch_events()
            self._last_news_refresh = now
            print("[AutoTrader] Economic calendar refreshed")

    def _is_news_blocked(self, symbol: str) -> tuple[bool, EconomicEvent | None]:
        """
        Check if trading is blocked due to upcoming/recent news.

        Returns:
            Tuple of (is_blocked, causing_event)
        """
        if not self.config.news_filter_enabled or not self.calendar_service:
            return False, None

        return self.calendar_service.should_avoid_trading(symbol)

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalizza simbolo da formato UI (EUR/USD) a formato interno (EUR_USD)."""
        return symbol.replace("/", "_")

    async def _analyze_and_trade(self):
        """Analyze all symbols and execute trades if conditions met."""
        # First manage existing positions (BE, Trailing Stop)
        await self._manage_open_positions()

        # Refresh news calendar periodically
        await self._refresh_news_calendar()

        # Normalizza simboli da formato UI (EUR/USD) a formato interno (EUR_USD)
        # Il formato interno corrisponde alle chiavi di SYMBOL_ALIASES del broker
        symbols = [self._normalize_symbol(s) for s in self.config.symbols]

        self._log_analysis("ALL", "info", f"Inizio ciclo analisi per {len(symbols)} asset: {', '.join(symbols)}")

        for symbol in symbols:
            try:
                # Skip if max positions reached
                if len(self.state.open_positions) >= self.config.max_open_positions:
                    self._log_analysis(symbol, "skip", f"Max posizioni raggiunte ({self.config.max_open_positions})")
                    continue

                # Skip if already have position in this symbol
                if any(p.symbol == symbol for p in self.state.open_positions):
                    self._log_analysis(symbol, "skip", "Posizione già aperta su questo asset")
                    continue

                # NEWS FILTER: Skip if blocked by upcoming/recent news
                news_blocked, blocking_event = self._is_news_blocked(symbol)
                if news_blocked and blocking_event:
                    self._log_analysis(symbol, "news", f"Bloccato per news: {blocking_event.title} ({blocking_event.currency}, {blocking_event.impact.value})")
                    print(f"[AutoTrader] ⚠️ Skipping {symbol} due to news: {blocking_event.title} ({blocking_event.currency}, {blocking_event.impact.value})")
                    continue

                self._log_analysis(symbol, "info", f"Avvio analisi AI per {symbol}...")

                # TradingView AI Agent - UNICO motore di analisi
                tv_symbol = symbol.replace("/", "").replace("_", "")
                mode_str = self.config.analysis_mode.value.lower()

                self._log_analysis(symbol, "analysis", f"TradingView Agent: analisi {mode_str} su {tv_symbol}")

                consensus = await self.tradingview_agent.analyze_with_mode(
                    symbol=tv_symbol,
                    mode=mode_str,
                    enabled_models=self.config.enabled_models
                )
                results = consensus.get("all_results", [])

                # Log ogni risultato di ciascun modello AI
                for r in results:
                    model_name = getattr(r, 'model_display_name', getattr(r, 'model', 'Unknown'))
                    direction = getattr(r, 'direction', 'N/A')
                    confidence = getattr(r, 'confidence', 0)
                    error = getattr(r, 'error', None)
                    reasoning = getattr(r, 'reasoning', '')
                    display_msg = f"[{model_name}] {direction} ({confidence:.0f}%): {error or reasoning}"
                    log_type = "error" if error else "analysis"
                    self._log_analysis(symbol, log_type, display_msg, {
                        "model": model_name,
                        "direction": direction,
                        "confidence": confidence,
                        "error": error,
                        "reasoning": reasoning,
                    })

                self._log_analysis(symbol, "analysis", f"Consenso: {consensus.get('direction', 'N/A')} - Confidence: {consensus.get('confidence', 0):.1f}% - Modelli: {consensus.get('models_agree', 0)}/{consensus.get('total_models', 0)}", {
                    "direction": consensus.get("direction"),
                    "confidence": consensus.get("confidence", 0),
                    "models_agree": consensus.get("models_agree", 0),
                })

                if self._should_enter_tradingview_trade(consensus):
                    self._log_analysis(symbol, "trade", f"TRADE: {consensus.get('direction')} {symbol} @ confidence {consensus.get('confidence', 0):.1f}%")
                    await self._execute_tradingview_trade(symbol, consensus, results)
                else:
                    self._log_analysis(symbol, "skip", f"Condizioni non soddisfatte (min confidence: {self.config.min_confidence}%)")

            except Exception as e:
                self._log_analysis(symbol, "error", f"Errore: {str(e)}")
                self.state.errors.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "symbol": symbol,
                    "error": str(e)
                })

            # Pausa tra i simboli per evitare rate limit Yahoo Finance
            await asyncio.sleep(2)

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

    def _should_enter_tradingview_trade(self, consensus: dict[str, Any]) -> bool:
        """Check if TradingView AI agent consensus meets trading criteria."""
        # Base checks from autonomous trade
        if not self._should_enter_autonomous_trade(consensus):
            return False

        # Additional check: Multi-timeframe alignment (unique to TradingView agent)
        # If analyzing multiple timeframes, require alignment
        timeframes = consensus.get("timeframes_analyzed", [])
        if len(timeframes) > 1:
            # Require timeframe alignment for multi-TF modes
            if not consensus.get("is_aligned", False):
                print(f"Trade rejected: Timeframe alignment too low ({consensus.get('timeframe_alignment', 0)}%)")
                return False

        return True

    async def _execute_tradingview_trade(
        self,
        symbol: str,
        consensus: dict[str, Any],
        results: list[TradingViewAnalysisResult]
    ):
        """Execute a trade based on TradingView AI agent consensus."""
        try:
            import traceback
            from decimal import Decimal

            direction = consensus.get("direction", "HOLD")
            self._log_analysis(symbol, "trade", f"📋 Esecuzione trade {direction} su {symbol}...")

            # Verifica che stop_loss e take_profit siano presenti
            stop_loss = consensus.get("stop_loss")
            take_profit = consensus.get("take_profit")

            if stop_loss is None or take_profit is None:
                self._log_analysis(symbol, "error", f"❌ Trade annullato: SL={stop_loss}, TP={take_profit} — mancano SL/TP nel consenso")
                return

            stop_loss = float(stop_loss)
            take_profit = float(take_profit)

            # Get current price
            self._log_analysis(symbol, "info", f"Recupero prezzo corrente per {symbol}...")
            tick = await self.broker.get_current_price(symbol)
            current_price = float(tick.mid)
            self._log_analysis(symbol, "info", f"Prezzo corrente: {current_price}")

            # ====== VALIDAZIONE SL/TP rispetto alla direzione ======
            MIN_RR_RATIO = 2.0  # Min Risk:Reward ratio (1:2) — TP almeno 2x la distanza SL
            MAX_RR_RATIO = 3.0  # Max Risk:Reward ratio (1:3) — TP non oltre 3x la distanza SL

            # ====== VALIDAZIONE DISTANZA MASSIMA SL (protezione da valori AI assurdi) ======
            # Percentuale UNIFORME per TUTTI gli asset - stesso comportamento su tutti i broker
            # NOTA: 0.5% è ottimale per day trading (SL raggiungibili in sessione)
            # US30 @ 49000 → 245 pips | US500 @ 6850 → 34 pips | EUR_USD @ 1.08 → 54 pips
            MAX_SL_PERCENT = 0.5  # Max 0.5% di distanza SL per tutti gli asset (indici, forex, oro, etc.)

            max_sl_distance = current_price * (MAX_SL_PERCENT / 100)

            # Round SL/TP from AI to correct decimals for this instrument
            _rp = lambda p: self._round_price(symbol, p)
            stop_loss = _rp(stop_loss)
            take_profit = _rp(take_profit)

            if direction == "LONG":
                # LONG: SL deve essere SOTTO il prezzo, TP deve essere SOPRA
                if stop_loss >= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ SL ({stop_loss}) >= prezzo ({current_price}) per LONG — SL invertito/invalido, correggo...")
                    stop_loss = _rp(current_price - max_sl_distance)
                    self._log_analysis(symbol, "info", f"SL corretto a: {stop_loss} ({MAX_SL_PERCENT}% sotto prezzo)")

                sl_dist = current_price - stop_loss

                # Controllo distanza massima SL (protezione da valori AI assurdi)
                if sl_dist > max_sl_distance:
                    old_sl = stop_loss
                    stop_loss = _rp(current_price - max_sl_distance)
                    sl_dist = max_sl_distance
                    self._log_analysis(symbol, "error", f"⚠️ SL troppo lontano ({old_sl}, {((current_price - old_sl) / current_price * 100):.1f}%) → corretto a {stop_loss} ({MAX_SL_PERCENT}%)")

                if take_profit <= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ TP ({take_profit}) <= prezzo ({current_price}) per LONG — TP invertito/invalido, correggo...")
                    take_profit = _rp(current_price + (sl_dist * MIN_RR_RATIO))
                    self._log_analysis(symbol, "info", f"TP corretto a: {take_profit} (R:R 1:{MIN_RR_RATIO})")
                else:
                    tp_dist = take_profit - current_price
                    actual_rr = tp_dist / sl_dist if sl_dist > 0 else 0

                    # Enforce minimum R:R — se TP troppo vicino, spostalo a MIN_RR_RATIO
                    if actual_rr < MIN_RR_RATIO:
                        old_tp = take_profit
                        take_profit = _rp(current_price + (sl_dist * MIN_RR_RATIO))
                        self._log_analysis(symbol, "info", f"📏 TP troppo vicino ({old_tp}, R:R 1:{actual_rr:.1f}) → spostato a {take_profit} (R:R 1:{MIN_RR_RATIO})")

                    # Cap TP: se il TP è troppo lontano (oltre MAX_RR_RATIO x SL), limitalo
                    elif actual_rr > MAX_RR_RATIO:
                        old_tp = take_profit
                        take_profit = _rp(current_price + (sl_dist * MAX_RR_RATIO))
                        self._log_analysis(symbol, "info", f"📏 TP troppo lontano ({old_tp}, R:R 1:{actual_rr:.1f}) → cappato a {take_profit} (R:R 1:{MAX_RR_RATIO})")

            elif direction == "SHORT":
                # SHORT: SL deve essere SOPRA il prezzo, TP deve essere SOTTO
                if stop_loss <= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ SL ({stop_loss}) <= prezzo ({current_price}) per SHORT — SL invertito/invalido, correggo...")
                    stop_loss = _rp(current_price + max_sl_distance)
                    self._log_analysis(symbol, "info", f"SL corretto a: {stop_loss} ({MAX_SL_PERCENT}% sopra prezzo)")

                sl_dist = stop_loss - current_price

                # Controllo distanza massima SL (protezione da valori AI assurdi)
                if sl_dist > max_sl_distance:
                    old_sl = stop_loss
                    stop_loss = _rp(current_price + max_sl_distance)
                    sl_dist = max_sl_distance
                    self._log_analysis(symbol, "error", f"⚠️ SL troppo lontano ({old_sl}, {((old_sl - current_price) / current_price * 100):.1f}%) → corretto a {stop_loss} ({MAX_SL_PERCENT}%)")

                if take_profit >= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ TP ({take_profit}) >= prezzo ({current_price}) per SHORT — TP invertito/invalido, correggo...")
                    take_profit = _rp(current_price - (sl_dist * MIN_RR_RATIO))
                    self._log_analysis(symbol, "info", f"TP corretto a: {take_profit} (R:R 1:{MIN_RR_RATIO})")
                else:
                    tp_dist = current_price - take_profit
                    actual_rr = tp_dist / sl_dist if sl_dist > 0 else 0

                    # Enforce minimum R:R — se TP troppo vicino, spostalo a MIN_RR_RATIO
                    if actual_rr < MIN_RR_RATIO:
                        old_tp = take_profit
                        take_profit = _rp(current_price - (sl_dist * MIN_RR_RATIO))
                        self._log_analysis(symbol, "info", f"📏 TP troppo vicino ({old_tp}, R:R 1:{actual_rr:.1f}) → spostato a {take_profit} (R:R 1:{MIN_RR_RATIO})")

                    # Cap TP: se il TP è troppo lontano (oltre MAX_RR_RATIO x SL), limitalo
                    elif actual_rr > MAX_RR_RATIO:
                        old_tp = take_profit
                        take_profit = _rp(current_price - (sl_dist * MAX_RR_RATIO))
                        self._log_analysis(symbol, "info", f"📏 TP troppo lontano ({old_tp}, R:R 1:{actual_rr:.1f}) → cappato a {take_profit} (R:R 1:{MAX_RR_RATIO})")

            # ====== CALCOLO POSIZIONE (basato su valore pip) ======
            account_info = await self.broker.get_account_info()
            account_balance = float(account_info.balance)

            risk_amount = account_balance * (self.config.risk_per_trade_percent / 100)
            sl_distance = abs(current_price - stop_loss)

            if sl_distance == 0:
                self._log_analysis(symbol, "error", f"❌ Trade annullato: distanza SL = 0 (prezzo={current_price}, SL={stop_loss})")
                return

            # Recupera specifiche simbolo dal broker per calcolo pip value preciso
            broker_spec = None
            try:
                if hasattr(self.broker, 'get_symbol_specification'):
                    broker_spec = await self.broker.get_symbol_specification(symbol)
                    if broker_spec:
                        self._log_analysis(symbol, "info", f"📋 Specifiche broker: contractSize={broker_spec.get('contractSize')}, tickValue={broker_spec.get('tickValue')}, tickSize={broker_spec.get('tickSize')}")
            except Exception as spec_err:
                self._log_analysis(symbol, "info", f"⚠️ Specifiche broker non disponibili: {spec_err}")

            # Calcola distanza SL in pips e valore pip per 1 lotto standard
            sl_pips, pip_value = self._calculate_pip_info(symbol, current_price, sl_distance, broker_spec)

            self._log_analysis(symbol, "info", f"📐 SL distanza: {sl_pips:.1f} pips | Valore pip/lotto: ${pip_value:.2f} | Rischio max: ${risk_amount:.2f}")

            # Formula: Size = Rischio ($) / (SL pips × Valore pip per 1 lotto)
            lot_size = risk_amount / (sl_pips * pip_value)
            lot_size = round(lot_size, 2)

            MIN_LOT = 0.01

            # Se la size calcolata è sotto il minimo, bisogna stringere lo SL
            if lot_size < MIN_LOT:
                # SL massimo consentito con 0.01 lotti per non superare il rischio
                max_sl_pips = risk_amount / (MIN_LOT * pip_value)
                old_sl_pips = sl_pips

                self._log_analysis(symbol, "info", f"⚠️ Size calcolata ({lot_size}) < minimo (0.01) — riduco SL da {old_sl_pips:.1f} a {max_sl_pips:.1f} pips")

                # Ricalcola SL più stretto
                pip_size = self._get_pip_size(symbol)
                new_sl_distance = max_sl_pips * pip_size

                if direction == "LONG":
                    stop_loss = _rp(current_price - new_sl_distance)
                    # Ricalcola TP con R:R 1:2
                    take_profit = _rp(current_price + (new_sl_distance * 2))
                else:
                    stop_loss = _rp(current_price + new_sl_distance)
                    take_profit = _rp(current_price - (new_sl_distance * 2))

                lot_size = MIN_LOT
                sl_pips = max_sl_pips

                self._log_analysis(symbol, "info", f"✅ SL/TP ricalcolati — SL: {stop_loss} ({sl_pips:.1f} pips) | TP: {take_profit} | Size: {lot_size} lotti")
            else:
                lot_size = max(MIN_LOT, lot_size)

            # ====== CONTROLLO SICUREZZA: Limita lot size massima ======
            # Se il pip_value calcolato è sbagliato (es. tickValue non disponibile dal broker),
            # la size potrebbe essere assurdamente alta. Limitiamo per sicurezza.
            MAX_LOT_SIZE = 5.0  # Max 5 lotti per trade (sicurezza)
            if lot_size > MAX_LOT_SIZE:
                self._log_analysis(symbol, "error", f"⚠️ Size calcolata ({lot_size}) troppo alta! Limitata a {MAX_LOT_SIZE} lotti (possibile errore pip_value)")
                lot_size = MAX_LOT_SIZE

            # Calcolo rischio effettivo
            actual_risk = lot_size * sl_pips * pip_value
            risk_pct = (actual_risk / account_balance) * 100

            side = OrderSide.BUY if direction == "LONG" else OrderSide.SELL

            self._log_analysis(symbol, "trade", f"📊 Ordine: {side.value} {lot_size} lotti | SL: {stop_loss} ({sl_pips:.1f} pips) | TP: {take_profit} | Rischio: ${actual_risk:.2f} ({risk_pct:.2f}%)")

            order = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                size=Decimal(str(lot_size)),
                stop_loss=Decimal(str(stop_loss)),
                take_profit=Decimal(str(take_profit)),
            )

            order_result = await self.broker.place_order(order)

            if order_result.is_filled:
                fill_price = float(order_result.average_fill_price) if order_result.average_fill_price else current_price

                # Break Even: usa il valore AI se disponibile, altrimenti default a 50% della distanza TP
                be_trigger = consensus.get("break_even_trigger")
                trailing_pips = consensus.get("trailing_stop_pips")
                if be_trigger is None:
                    # Default BE: quando il prezzo raggiunge il 50% del TP
                    tp_distance = abs(take_profit - fill_price)
                    if direction == "LONG":
                        be_trigger = _rp(fill_price + (tp_distance * 0.5))
                    else:
                        be_trigger = _rp(fill_price - (tp_distance * 0.5))
                    self._log_analysis(symbol, "info", f"🔒 Break Even auto impostato a {be_trigger} (50% del TP)")
                if trailing_pips is None:
                    # Default trailing: 15 pips dopo il BE
                    trailing_pips = 15.0
                    self._log_analysis(symbol, "info", f"📈 Trailing Stop auto: {trailing_pips} pips dopo BE")

                trade = TradeRecord(
                    id=order_result.order_id,
                    symbol=symbol,
                    direction=direction,
                    entry_price=fill_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    units=lot_size,
                    timestamp=datetime.utcnow(),
                    confidence=consensus["confidence"],
                    timeframes_analyzed=consensus.get("timeframes", ["15"]),
                    models_agreed=consensus["models_agree"],
                    total_models=consensus["total_models"],
                    break_even_trigger=be_trigger,
                    trailing_stop_pips=trailing_pips,
                )

                self.state.open_positions.append(trade)
                self.state.trades_today += 1
                self._log_analysis(symbol, "trade", f"✅ TRADE ESEGUITO: {side.value} {symbol} @ {fill_price} | SL: {stop_loss} | TP: {take_profit} | ID: {order_result.order_id}")

                await self._notify_tradingview_trade(trade, consensus, results)
            elif order_result.is_rejected:
                reject_msg = order_result.error_message or 'motivo sconosciuto'
                self._log_analysis(symbol, "error", f"❌ ORDINE RIFIUTATO: {reject_msg}")
                self._log_analysis(symbol, "error", f"📋 Dettagli: {side.value} {lot_size} lotti {symbol} | SL: {stop_loss} | TP: {take_profit}")
                print(f"[AutoTrader] Order REJECTED for {symbol}: status={order_result.status}, error={reject_msg}, order_id={order_result.order_id}")
            else:
                self._log_analysis(symbol, "info", f"⏳ Ordine in stato: {order_result.status.value} — ID: {order_result.order_id or 'in attesa'}")

        except Exception as e:
            error_detail = traceback.format_exc()
            self._log_analysis(symbol, "error", f"❌ Esecuzione trade fallita: {str(e)}")
            print(f"[AutoTrader] Trade execution error for {symbol}:\n{error_detail}")
            self.state.errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "error": f"TradingView trade execution failed: {str(e)}"
            })

    async def _notify_tradingview_trade(
        self,
        trade: TradeRecord,
        consensus: dict[str, Any],
        results: list[TradingViewAnalysisResult]
    ):
        """Send notification for TradingView AI agent trade."""
        # Get key observations
        observations = consensus.get("key_observations", [])[:5]
        observations_str = "\n".join([f"  • {obs}" for obs in observations]) if observations else "  N/A"

        # Get reasoning from top model
        combined_reasoning = consensus.get("combined_reasoning", "")[:600]

        # Advanced management
        advanced_mgmt = []
        if trade.break_even_trigger:
            advanced_mgmt.append(f"🔒 BE: {trade.break_even_trigger:.5f}")
        if trade.trailing_stop_pips:
            advanced_mgmt.append(f"📈 Trail: {trade.trailing_stop_pips:.1f} pips")
        advanced_str = " | ".join(advanced_mgmt) if advanced_mgmt else "Standard"

        # Indicators and styles
        styles = consensus.get("analysis_styles_used", [])
        indicators = consensus.get("indicators_used", [])[:6]

        message = f"""
🎯 **TRADINGVIEW AI AGENT TRADE**

📊 **{trade.direction}** {trade.symbol}
💰 Entry: {trade.entry_price:.5f}
🛑 SL: {trade.stop_loss:.5f}
🎯 TP: {trade.take_profit:.5f}
⚙️ {advanced_str}

🤖 **AI Consensus**: {consensus['models_agree']}/{consensus['total_models']} ({consensus['confidence']:.1f}%)
📈 **Styles**: {', '.join(styles) if styles else 'Mixed'}
📉 **Indicators**: {', '.join(indicators) if indicators else 'Various'}

🔍 **Key Observations**:
{observations_str}

💭 **AI Reasoning**:
{combined_reasoning}
"""
        await self._notify(message)

    def _should_enter_autonomous_trade(self, consensus: dict[str, Any]) -> bool:
        """Check if autonomous analysis consensus meets trading criteria."""
        # Must have a direction (not HOLD)
        if consensus.get("direction") == "HOLD":
            return False

        # Confidence check
        if consensus.get("confidence", 0) < self.config.min_confidence:
            return False

        # Model agreement check
        if consensus.get("models_agree", 0) < self.config.min_models_agree:
            return False

        # Must be a strong signal
        if not consensus.get("is_strong_signal", False):
            return False

        # Must have stop loss and take profit
        if not consensus.get("stop_loss") or not consensus.get("take_profit"):
            return False

        return True

    async def _execute_autonomous_trade(
        self,
        symbol: str,
        consensus: dict[str, Any],
        results: list[AutonomousAnalysisResult]
    ):
        """Execute a trade based on autonomous AI consensus."""
        try:
            from decimal import Decimal

            # Get current price
            tick = await self.broker.get_current_price(symbol)
            current_price = float(tick.mid)

            # Calculate position size
            account_info = await self.broker.get_account_info()
            account_balance = float(account_info.balance)

            risk_amount = account_balance * (self.config.risk_per_trade_percent / 100)
            sl_distance = abs(current_price - consensus["stop_loss"])

            if sl_distance == 0:
                return

            # Units = risk amount / stop loss distance
            units = risk_amount / sl_distance

            # Determine order side
            side = OrderSide.BUY if consensus["direction"] == "LONG" else OrderSide.SELL

            # Create order
            order = OrderRequest(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                size=Decimal(str(units)),
                stop_loss=Decimal(str(consensus["stop_loss"])),
                take_profit=Decimal(str(consensus["take_profit"])),
            )

            # Execute order
            order_result = await self.broker.place_order(order)

            if order_result.is_filled:
                # Collect analysis styles used by agreeing models
                styles_used = consensus.get("analysis_styles_used", [])
                indicators_used = consensus.get("indicators_considered", [])

                # Record trade with advanced management
                fill_price = float(order_result.average_fill_price) if order_result.average_fill_price else current_price
                trade = TradeRecord(
                    id=order_result.order_id,
                    symbol=symbol,
                    direction=consensus["direction"],
                    entry_price=fill_price,
                    stop_loss=consensus["stop_loss"],
                    take_profit=consensus["take_profit"],
                    units=units,
                    timestamp=datetime.utcnow(),
                    confidence=consensus["confidence"],
                    timeframes_analyzed=consensus.get("timeframes", ["15"]),
                    models_agreed=consensus["models_agree"],
                    total_models=consensus["total_models"],
                    # Advanced trade management
                    break_even_trigger=consensus.get("break_even_trigger"),
                    trailing_stop_pips=consensus.get("trailing_stop_pips"),
                    partial_tp_percent=consensus.get("partial_tp_percent"),
                )

                self.state.open_positions.append(trade)
                self.state.trades_today += 1

                # Send detailed notification with AI reasoning
                await self._notify_autonomous_trade(trade, consensus, results)

        except Exception as e:
            self.state.errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "error": f"Autonomous trade execution failed: {str(e)}"
            })

    async def _notify_autonomous_trade(
        self,
        trade: TradeRecord,
        consensus: dict[str, Any],
        results: list[AutonomousAnalysisResult]
    ):
        """Send notification for autonomous trade with detailed AI analysis."""
        # Get reasoning from the top confident model
        top_reasoning = ""
        for r in sorted(results, key=lambda x: x.confidence, reverse=True):
            if r.direction == consensus["direction"] and r.reasoning:
                top_reasoning = r.reasoning[:500]
                break

        styles = consensus.get("analysis_styles_used", [])
        indicators = consensus.get("indicators_considered", [])[:5]

        # Build advanced management info
        advanced_mgmt = []
        if trade.break_even_trigger:
            advanced_mgmt.append(f"🔒 BE Trigger: {trade.break_even_trigger:.5f}")
        if trade.trailing_stop_pips:
            advanced_mgmt.append(f"📈 Trailing: {trade.trailing_stop_pips:.1f} pips")
        if trade.partial_tp_percent:
            advanced_mgmt.append(f"📊 Partial Close: {trade.partial_tp_percent:.0f}% at TP1")

        advanced_str = "\n".join(advanced_mgmt) if advanced_mgmt else "Standard SL/TP"

        message = f"""
🤖 **AUTONOMOUS AI TRADE**

📈 **{trade.direction}** {trade.symbol}
💰 Entry: {trade.entry_price:.5f}
🛑 SL: {trade.stop_loss:.5f}
🎯 TP: {trade.take_profit:.5f}

⚙️ **Trade Management**:
{advanced_str}

📊 **AI Consensus**: {consensus['models_agree']}/{consensus['total_models']} models agree
🎯 **Confidence**: {consensus['confidence']:.1f}%
📈 **Styles Used**: {', '.join(styles) if styles else 'Mixed'}
📉 **Indicators**: {', '.join(indicators) if indicators else 'Various'}

💭 **Top AI Reasoning**:
{top_reasoning}
"""
        await self._notify(message)

    async def _execute_trade(self, result: MultiTimeframeResult):
        """Execute a trade based on analysis result."""
        try:
            from decimal import Decimal

            # Get current price
            tick = await self.broker.get_current_price(result.symbol)
            current_price = float(tick.mid)

            # Calculate position size
            account_info = await self.broker.get_account_info()
            account_balance = float(account_info.balance)

            risk_amount = account_balance * (self.config.risk_per_trade_percent / 100)
            sl_distance = abs(current_price - result.stop_loss)

            if sl_distance == 0:
                return

            # Units = risk amount / stop loss distance
            units = risk_amount / sl_distance

            # Determine order side
            side = OrderSide.BUY if result.final_direction == "LONG" else OrderSide.SELL

            # Create order
            tp_value = result.take_profit[0] if result.take_profit else None
            order = OrderRequest(
                symbol=result.symbol,
                side=side,
                order_type=OrderType.MARKET,
                size=Decimal(str(units)),
                stop_loss=Decimal(str(result.stop_loss)),
                take_profit=Decimal(str(tp_value)) if tp_value else None,
            )

            # Execute order
            order_result = await self.broker.place_order(order)

            if order_result.is_filled:
                # Record trade
                fill_price = float(order_result.average_fill_price) if order_result.average_fill_price else current_price
                trade = TradeRecord(
                    id=order_result.order_id,
                    symbol=result.symbol,
                    direction=result.final_direction,
                    entry_price=fill_price,
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
_auto_trader: AutoTrader | None = None


def get_auto_trader() -> AutoTrader:
    """Get or create the auto trader singleton."""
    global _auto_trader
    if _auto_trader is None:
        _auto_trader = AutoTrader()
    return _auto_trader
