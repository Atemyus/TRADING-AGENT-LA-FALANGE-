"""
Multi-Broker Manager - Manages multiple AutoTrader instances for different brokers.

Each broker account runs independently with its own:
- TradingView AI Agent analysis
- Trading configuration (symbols, risk, hours)
- Broker connection (MetaApi credentials)
"""

import asyncio
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import BrokerAccount
from src.engines.trading.auto_trader import AutoTrader, BotConfig, BotStatus, AnalysisMode


@dataclass
class BrokerInstance:
    """Represents a running broker instance.

    IMPORTANT: Stores plain data instead of SQLAlchemy objects to avoid
    DetachedInstanceError when accessing data outside of session context.
    """
    # Plain data copied from BrokerAccount (avoids DetachedInstanceError)
    broker_id: int
    broker_name: str
    broker_type: str
    symbols: List[str]
    metaapi_account_id: str

    # AutoTrader instance
    trader: AutoTrader

    # Status tracking
    status: str = "stopped"
    started_at: Optional[datetime] = None
    last_error: Optional[str] = None


class MultiBrokerManager:
    """
    Manages multiple AutoTrader instances, one per broker account.

    Each broker runs completely independently:
    - Own broker connection (MetaApi credentials)
    - Own symbol list
    - Own risk settings
    - Own analysis interval
    - Own AI model selection
    """

    def __init__(self):
        self._instances: Dict[int, BrokerInstance] = {}
        self._lock = asyncio.Lock()

    async def load_brokers(self, db: AsyncSession) -> List[BrokerAccount]:
        """Load all broker accounts from database."""
        result = await db.execute(select(BrokerAccount).order_by(BrokerAccount.id))
        return list(result.scalars().all())

    async def initialize_broker(self, broker_account: BrokerAccount) -> BrokerInstance:
        """Initialize an AutoTrader instance for a specific broker account.

        IMPORTANT: Copies data from BrokerAccount to plain fields to avoid
        DetachedInstanceError when accessing data outside of session context.
        """
        async with self._lock:
            # Check if already exists
            if broker_account.id in self._instances:
                return self._instances[broker_account.id]

            # Create AutoTrader with broker-specific config
            trader = AutoTrader()
            config = self._create_config_from_account(broker_account)
            trader.configure(config)

            # Copy plain data from SQLAlchemy object (avoids DetachedInstanceError)
            instance = BrokerInstance(
                broker_id=broker_account.id,
                broker_name=broker_account.name,
                broker_type=broker_account.broker_type,
                symbols=list(broker_account.symbols),  # Copy the list
                metaapi_account_id=broker_account.metaapi_account_id or "",
                trader=trader,
                status="initialized"
            )

            self._instances[broker_account.id] = instance
            return instance

    def _create_config_from_account(self, account: BrokerAccount) -> BotConfig:
        """Create BotConfig from BrokerAccount database model."""
        # Parse analysis mode
        try:
            analysis_mode = AnalysisMode(account.analysis_mode)
        except ValueError:
            analysis_mode = AnalysisMode.STANDARD

        return BotConfig(
            symbols=account.symbols,
            analysis_mode=analysis_mode,
            analysis_interval_seconds=account.analysis_interval_seconds,
            min_confidence=account.min_confidence,
            min_models_agree=account.min_models_agree,
            risk_per_trade_percent=account.risk_per_trade_percent,
            max_open_positions=account.max_open_positions,
            max_daily_trades=account.max_daily_trades,
            max_daily_loss_percent=account.max_daily_loss_percent,
            trading_start_hour=account.trading_start_hour,
            trading_end_hour=account.trading_end_hour,
            trade_on_weekends=account.trade_on_weekends,
            enabled_models=account.enabled_models,
            # Broker credentials - CRITICAL for multi-broker isolation
            broker_type=account.broker_type,
            metaapi_token=account.metaapi_token,
            metaapi_account_id=account.metaapi_account_id,
        )

    async def start_broker(self, broker_id: int, db: AsyncSession) -> dict:
        """Start a specific broker's AutoTrader instance."""
        # Load fresh broker data from DB
        result = await db.execute(
            select(BrokerAccount).where(BrokerAccount.id == broker_id)
        )
        broker_account = result.scalar_one_or_none()

        if not broker_account:
            return {"status": "error", "message": "Broker not found"}

        if not broker_account.is_enabled:
            return {"status": "error", "message": "Broker is disabled"}

        if not broker_account.metaapi_token or not broker_account.metaapi_account_id:
            return {"status": "error", "message": "MetaApi credentials not configured"}

        # Initialize if not exists
        instance = await self.initialize_broker(broker_account)

        # Check if already running
        if instance.trader.state.status == BotStatus.RUNNING:
            return {"status": "already_running", "message": f"Broker '{broker_account.name}' is already running"}

        try:
            # Credentials are now passed via BotConfig - no need to set env vars!
            # This ensures each broker instance uses its OWN credentials
            print(f"[MultiBrokerManager] Starting broker '{broker_account.name}' with account ...{broker_account.metaapi_account_id[-4:] if broker_account.metaapi_account_id else 'N/A'}")

            # Start the trader
            await instance.trader.start()
            instance.status = "running"
            instance.started_at = datetime.utcnow()
            instance.last_error = None

            # Update DB connection status
            broker_account.is_connected = True
            broker_account.last_connected_at = datetime.utcnow()
            await db.flush()

            return {
                "status": "success",
                "message": f"Broker '{broker_account.name}' started successfully",
                "broker_id": broker_id,
                "symbols": broker_account.symbols
            }
        except Exception as e:
            instance.status = "error"
            instance.last_error = str(e)
            return {"status": "error", "message": f"Failed to start: {str(e)}"}

    async def stop_broker(self, broker_id: int, db: AsyncSession) -> dict:
        """Stop a specific broker's AutoTrader instance."""
        if broker_id not in self._instances:
            return {"status": "error", "message": "Broker instance not found"}

        instance = self._instances[broker_id]

        if instance.trader.state.status == BotStatus.STOPPED:
            return {"status": "already_stopped", "message": "Broker is already stopped"}

        try:
            await instance.trader.stop()
            instance.status = "stopped"

            # Update DB connection status
            result = await db.execute(
                select(BrokerAccount).where(BrokerAccount.id == broker_id)
            )
            broker_account = result.scalar_one_or_none()
            if broker_account:
                broker_account.is_connected = False
                await db.flush()

            return {
                "status": "success",
                "message": f"Broker '{instance.broker_name}' stopped",
                "broker_id": broker_id
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to stop: {str(e)}"}

    async def start_all_enabled(self, db: AsyncSession) -> dict:
        """Start all enabled broker accounts."""
        brokers = await self.load_brokers(db)
        results = []

        for broker in brokers:
            if broker.is_enabled:
                result = await self.start_broker(broker.id, db)
                results.append({
                    "broker_id": broker.id,
                    "name": broker.name,
                    **result
                })

        return {
            "status": "success",
            "started": len([r for r in results if r.get("status") == "success"]),
            "total_enabled": len([b for b in brokers if b.is_enabled]),
            "results": results
        }

    async def stop_all(self, db: AsyncSession) -> dict:
        """Stop all running broker instances."""
        results = []

        for broker_id, instance in list(self._instances.items()):
            if instance.trader.state.status == BotStatus.RUNNING:
                result = await self.stop_broker(broker_id, db)
                results.append({
                    "broker_id": broker_id,
                    "name": instance.broker_name,
                    **result
                })

        return {
            "status": "success",
            "stopped": len([r for r in results if r.get("status") == "success"]),
            "results": results
        }

    def get_broker_status(self, broker_id: int) -> Optional[dict]:
        """Get status of a specific broker instance."""
        if broker_id not in self._instances:
            return None

        instance = self._instances[broker_id]
        trader = instance.trader

        return {
            "broker_id": broker_id,
            "name": instance.broker_name,
            "status": trader.state.status.value,
            "started_at": instance.started_at.isoformat() if instance.started_at else None,
            "last_error": instance.last_error,
            "statistics": {
                "analyses_today": trader.state.analyses_today,
                "trades_today": trader.state.trades_today,
                "daily_pnl": trader.state.daily_pnl,
                "open_positions": len(trader.state.open_positions),
            },
            "config": {
                "symbols": trader.config.symbols,
                "analysis_mode": trader.config.analysis_mode.value,
                "analysis_interval": trader.config.analysis_interval_seconds,
                "enabled_models": trader.config.enabled_models,
            }
        }

    async def get_broker_account_info(self, broker_id: int) -> Optional[dict]:
        """Get account info (balance, equity) for a specific broker."""
        if broker_id not in self._instances:
            return None

        instance = self._instances[broker_id]
        trader = instance.trader

        # Check if broker is connected
        if not trader.broker:
            return None

        try:
            account_info = await trader.broker.get_account_info()
            return {
                "broker_id": broker_id,
                "balance": float(account_info.balance),
                "equity": float(account_info.equity),
                "margin_used": float(account_info.margin_used),
                "margin_available": float(account_info.margin_available),
                "unrealized_pnl": float(account_info.unrealized_pnl),
                "currency": account_info.currency,
            }
        except Exception as e:
            return {
                "broker_id": broker_id,
                "error": str(e)
            }

    async def get_broker_positions(self, broker_id: int) -> Optional[list]:
        """Get open positions for a specific broker."""
        if broker_id not in self._instances:
            return None

        instance = self._instances[broker_id]
        trader = instance.trader

        # Check if broker is connected
        if not trader.broker:
            return None

        try:
            positions = await trader.broker.get_positions()
            return [
                {
                    "position_id": p.position_id,
                    "symbol": p.symbol,
                    "side": p.side,
                    "size": float(p.size),
                    "entry_price": float(p.entry_price),
                    "current_price": float(p.current_price),
                    "unrealized_pnl": str(p.unrealized_pnl),
                    "unrealized_pnl_percent": str(getattr(p, 'unrealized_pnl_percent', '0')),
                    "stop_loss": float(p.stop_loss) if p.stop_loss else None,
                    "take_profit": float(p.take_profit) if p.take_profit else None,
                    "leverage": getattr(p, 'leverage', 1),
                    "margin_used": float(getattr(p, 'margin_used', 0)),
                    "opened_at": p.opened_at.isoformat() if hasattr(p, 'opened_at') and p.opened_at else None,
                    "broker_id": broker_id,
                    "broker_name": instance.broker_name,
                }
                for p in positions
            ]
        except Exception as e:
            return []

    def get_all_statuses(self) -> List[dict]:
        """Get status of all broker instances."""
        return [
            self.get_broker_status(broker_id)
            for broker_id in self._instances
        ]

    def get_instance(self, broker_id: int) -> Optional[BrokerInstance]:
        """Get a specific broker instance."""
        return self._instances.get(broker_id)

    def get_broker_logs(self, broker_id: int, limit: int = 50) -> Optional[dict]:
        """Get analysis logs for a specific broker."""
        if broker_id not in self._instances:
            return None

        instance = self._instances[broker_id]
        trader = instance.trader
        logs = trader.state.analysis_logs[-limit:]

        return {
            "broker_id": broker_id,
            "name": instance.broker_name,
            "logs": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "symbol": log.symbol,
                    "type": log.log_type,
                    "message": log.message,
                    "details": log.details
                }
                for log in logs
            ],
            "total": len(trader.state.analysis_logs)
        }

    async def refresh_broker_config(self, broker_id: int, db: AsyncSession) -> dict:
        """Refresh a broker's configuration from database (without restart)."""
        result = await db.execute(
            select(BrokerAccount).where(BrokerAccount.id == broker_id)
        )
        broker_account = result.scalar_one_or_none()

        if not broker_account:
            return {"status": "error", "message": "Broker not found"}

        if broker_id not in self._instances:
            return {"status": "error", "message": "Broker instance not initialized"}

        instance = self._instances[broker_id]
        new_config = self._create_config_from_account(broker_account)
        instance.trader.configure(new_config)

        # Update plain data fields (avoids DetachedInstanceError)
        instance.broker_name = broker_account.name
        instance.broker_type = broker_account.broker_type
        instance.symbols = list(broker_account.symbols)
        instance.metaapi_account_id = broker_account.metaapi_account_id or ""

        return {
            "status": "success",
            "message": f"Configuration refreshed for '{broker_account.name}'",
            "config": {
                "symbols": new_config.symbols,
                "analysis_mode": new_config.analysis_mode.value,
            }
        }


# Singleton instance
_multi_broker_manager: Optional[MultiBrokerManager] = None


def get_multi_broker_manager() -> MultiBrokerManager:
    """Get or create the multi-broker manager singleton."""
    global _multi_broker_manager
    if _multi_broker_manager is None:
        _multi_broker_manager = MultiBrokerManager()
    return _multi_broker_manager
