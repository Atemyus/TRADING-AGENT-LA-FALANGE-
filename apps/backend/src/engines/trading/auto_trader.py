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
from typing import Optional, List, Dict, Any, Callable, Tuple
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
from src.engines.ai.autonomous_analyst import (
    AutonomousAnalyst,
    AutonomousAnalysisResult,
    get_autonomous_analyst,
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
from src.engines.trading.broker_factory import BrokerFactory
from src.engines.trading.base_broker import BaseBroker, OrderRequest, OrderType, OrderSide
from src.core.config import settings
from src.services.economic_calendar_service import (
    EconomicCalendarService,
    NewsFilterConfig,
    get_economic_calendar_service,
    EconomicEvent,
    NewsImpact,
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
    timeframes_analyzed: List[str]
    models_agreed: int
    total_models: int
    status: str = "open"  # open, closed_tp, closed_sl, closed_manual, closed_be
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    profit_loss: Optional[float] = None

    # Advanced trade management
    break_even_trigger: Optional[float] = None  # Move SL to entry when price hits this
    trailing_stop_pips: Optional[float] = None  # Trail SL by this many pips
    partial_tp_percent: Optional[float] = None  # Close this % at TP1
    is_break_even: bool = False  # Has SL been moved to entry?
    current_trailing_sl: Optional[float] = None  # Current trailing SL level


@dataclass
class BotConfig:
    """Configuration for the auto trading bot."""
    # Assets to trade
    symbols: List[str] = field(default_factory=lambda: ["EUR/USD", "GBP/USD", "XAU/USD"])

    # Analysis settings
    analysis_mode: AnalysisMode = AnalysisMode.PREMIUM
    analysis_interval_seconds: int = 300  # 5 minutes

    # TradingView AI Agent - UNICO motore di analisi
    # Usa Playwright per aprire TradingView.com reale e fare screenshot
    # Ogni AI analizza i grafici reali e dà il suo verdetto
    tradingview_headless: bool = True     # Run browser in headless mode
    tradingview_max_indicators: int = 3   # Max indicators (3=Basic, 5=Essential, 10=Plus, 25=Premium)

    # AI Models - abilita/disabilita singoli modelli
    enabled_models: List[str] = field(default_factory=lambda: [
        "chatgpt", "gemini", "grok", "qwen", "llama", "ernie"
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


@dataclass
class AnalysisLogEntry:
    """Log entry for AI analysis activity."""
    timestamp: datetime
    symbol: str
    log_type: str  # "info", "analysis", "trade", "skip", "error", "news"
    message: str
    details: Optional[Dict[str, Any]] = None


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
    analysis_logs: List[AnalysisLogEntry] = field(default_factory=list)  # AI reasoning logs


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
        self.autonomous_analyst: Optional[AutonomousAnalyst] = None
        self.tradingview_agent: Optional[TradingViewAIAgent] = None
        self.broker: Optional[BaseBroker] = None
        self.calendar_service: Optional[EconomicCalendarService] = None
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._callbacks: List[Callable] = []
        self._last_news_refresh: Optional[datetime] = None

    def configure(self, config: BotConfig):
        """Update bot configuration."""
        self.config = config

    def _log_analysis(self, symbol: str, log_type: str, message: str, details: Optional[Dict[str, Any]] = None):
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

    def _get_pip_size(self, symbol: str) -> float:
        """Restituisce la dimensione di 1 pip per lo strumento."""
        sym = symbol.upper().replace("/", "").replace("_", "")

        # JPY pairs: 1 pip = 0.01
        if "JPY" in sym:
            return 0.01
        # Oro: 1 pip = 0.10 ($)
        if "XAU" in sym or "GOLD" in sym:
            return 0.10
        # Indici: 1 pip = 1.0 punto
        if any(idx in sym for idx in ["US30", "US500", "NAS100", "DE40", "UK100", "JP225", "FR40", "EU50"]):
            return 1.0
        # Forex standard: 1 pip = 0.0001
        return 0.0001

    def _calculate_pip_info(self, symbol: str, current_price: float, sl_distance: float) -> tuple:
        """
        Calcola la distanza SL in pips e il valore di 1 pip per 1 lotto standard.
        Restituisce (sl_pips, pip_value_per_lot).
        """
        sym = symbol.upper().replace("/", "").replace("_", "")
        pip_size = self._get_pip_size(symbol)
        sl_pips = sl_distance / pip_size

        # Valore pip per 1 lotto standard
        if "XAU" in sym or "GOLD" in sym:
            # Oro: 1 lotto = 100 oz, 1 pip ($0.10) × 100 oz = $10 per pip/lotto
            pip_value = 10.0
        elif any(idx in sym for idx in ["US30", "US500", "NAS100", "DE40", "UK100", "JP225", "FR40", "EU50"]):
            # Indici: 1 lotto = 1 contratto, 1 punto = $1 (varia, usiamo approssimazione)
            if "US30" in sym:
                pip_value = 1.0  # $1 per punto per contratto
            elif "US500" in sym or "NAS100" in sym:
                pip_value = 1.0
            elif "DE40" in sym or "EU50" in sym or "FR40" in sym:
                pip_value = 1.0  # €1 per punto ≈ $1
            elif "UK100" in sym:
                pip_value = 1.0  # £1 per punto ≈ $1.25
            else:
                pip_value = 1.0
        elif "JPY" in sym:
            # JPY pairs: 1 pip (0.01) × 100,000 unità / prezzo ≈ $6.7 (varia)
            pip_value = (0.01 * 100000) / current_price if current_price > 0 else 6.7
        else:
            # Forex standard (EUR/USD, GBP/USD, ecc.):
            # 1 pip (0.0001) × 100,000 unità = $10 per pip/lotto (coppie con USD come quote)
            # Per coppie come EUR/GBP dove USD non è quote, sarebbe diverso
            # Ma la maggior parte dei broker converte automaticamente in USD
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
            print(f"[AutoTrader] Bot started successfully with TradingView AI Agent")

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
        """Manage open positions: Break Even, Trailing Stop, Partial TP."""
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
                    pip_value = 0.0001 if "JPY" not in trade.symbol else 0.01
                    trail_distance = trade.trailing_stop_pips * pip_value

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

    def _is_news_blocked(self, symbol: str) -> Tuple[bool, Optional[EconomicEvent]]:
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

    def _should_enter_tradingview_trade(self, consensus: Dict[str, Any]) -> bool:
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
        consensus: Dict[str, Any],
        results: List[TradingViewAnalysisResult]
    ):
        """Execute a trade based on TradingView AI agent consensus."""
        try:
            from decimal import Decimal
            import traceback

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
            MAX_RR_RATIO = 3.0  # Max Risk:Reward ratio (1:3) — TP non oltre 3x la distanza SL

            if direction == "LONG":
                # LONG: SL deve essere SOTTO il prezzo, TP deve essere SOPRA
                if stop_loss >= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ SL ({stop_loss}) >= prezzo ({current_price}) per LONG — SL invertito/invalido, correggo...")
                    stop_loss = round(current_price * 0.995, 5)
                    self._log_analysis(symbol, "info", f"SL corretto a: {stop_loss} (0.5% sotto prezzo)")

                sl_dist = current_price - stop_loss

                if take_profit <= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ TP ({take_profit}) <= prezzo ({current_price}) per LONG — TP invertito/invalido, correggo...")
                    take_profit = round(current_price + (sl_dist * MAX_RR_RATIO), 5)
                    self._log_analysis(symbol, "info", f"TP corretto a: {take_profit} (R:R 1:{MAX_RR_RATIO})")
                else:
                    # Cap TP: se il TP è troppo lontano (oltre MAX_RR_RATIO x SL), limitalo
                    tp_dist = take_profit - current_price
                    actual_rr = tp_dist / sl_dist if sl_dist > 0 else 0
                    if actual_rr > MAX_RR_RATIO:
                        old_tp = take_profit
                        take_profit = round(current_price + (sl_dist * MAX_RR_RATIO), 5)
                        self._log_analysis(symbol, "info", f"📏 TP troppo lontano ({old_tp}, R:R 1:{actual_rr:.1f}) → cappato a {take_profit} (R:R 1:{MAX_RR_RATIO})")

            elif direction == "SHORT":
                # SHORT: SL deve essere SOPRA il prezzo, TP deve essere SOTTO
                if stop_loss <= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ SL ({stop_loss}) <= prezzo ({current_price}) per SHORT — SL invertito/invalido, correggo...")
                    stop_loss = round(current_price * 1.005, 5)
                    self._log_analysis(symbol, "info", f"SL corretto a: {stop_loss} (0.5% sopra prezzo)")

                sl_dist = stop_loss - current_price

                if take_profit >= current_price:
                    self._log_analysis(symbol, "error", f"⚠️ TP ({take_profit}) >= prezzo ({current_price}) per SHORT — TP invertito/invalido, correggo...")
                    take_profit = round(current_price - (sl_dist * MAX_RR_RATIO), 5)
                    self._log_analysis(symbol, "info", f"TP corretto a: {take_profit} (R:R 1:{MAX_RR_RATIO})")
                else:
                    # Cap TP: se il TP è troppo lontano (oltre MAX_RR_RATIO x SL), limitalo
                    tp_dist = current_price - take_profit
                    actual_rr = tp_dist / sl_dist if sl_dist > 0 else 0
                    if actual_rr > MAX_RR_RATIO:
                        old_tp = take_profit
                        take_profit = round(current_price - (sl_dist * MAX_RR_RATIO), 5)
                        self._log_analysis(symbol, "info", f"📏 TP troppo lontano ({old_tp}, R:R 1:{actual_rr:.1f}) → cappato a {take_profit} (R:R 1:{MAX_RR_RATIO})")

            # ====== CALCOLO POSIZIONE (basato su valore pip) ======
            account_info = await self.broker.get_account_info()
            account_balance = float(account_info.balance)

            risk_amount = account_balance * (self.config.risk_per_trade_percent / 100)
            sl_distance = abs(current_price - stop_loss)

            if sl_distance == 0:
                self._log_analysis(symbol, "error", f"❌ Trade annullato: distanza SL = 0 (prezzo={current_price}, SL={stop_loss})")
                return

            # Calcola distanza SL in pips e valore pip per 1 lotto standard
            sl_pips, pip_value = self._calculate_pip_info(symbol, current_price, sl_distance)

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
                    stop_loss = round(current_price - new_sl_distance, 5)
                    # Ricalcola TP con R:R 1:2
                    take_profit = round(current_price + (new_sl_distance * 2), 5)
                else:
                    stop_loss = round(current_price + new_sl_distance, 5)
                    take_profit = round(current_price - (new_sl_distance * 2), 5)

                lot_size = MIN_LOT
                sl_pips = max_sl_pips

                self._log_analysis(symbol, "info", f"✅ SL/TP ricalcolati — SL: {stop_loss} ({sl_pips:.1f} pips) | TP: {take_profit} | Size: {lot_size} lotti")
            else:
                lot_size = max(MIN_LOT, lot_size)

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
                        be_trigger = round(fill_price + (tp_distance * 0.5), 5)
                    else:
                        be_trigger = round(fill_price - (tp_distance * 0.5), 5)
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
                self._log_analysis(symbol, "error", f"❌ ORDINE RIFIUTATO dal broker: {order_result.error_message or 'motivo sconosciuto'}")
                self._log_analysis(symbol, "error", f"📋 Dettagli: {side.value} {lot_size} lotti {symbol} | SL: {stop_loss} | TP: {take_profit}")
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
        consensus: Dict[str, Any],
        results: List[TradingViewAnalysisResult]
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

    def _should_enter_autonomous_trade(self, consensus: Dict[str, Any]) -> bool:
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
        consensus: Dict[str, Any],
        results: List[AutonomousAnalysisResult]
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
        consensus: Dict[str, Any],
        results: List[AutonomousAnalysisResult]
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
_auto_trader: Optional[AutoTrader] = None


def get_auto_trader() -> AutoTrader:
    """Get or create the auto trader singleton."""
    global _auto_trader
    if _auto_trader is None:
        _auto_trader = AutoTrader()
    return _auto_trader
