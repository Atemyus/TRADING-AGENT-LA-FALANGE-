"""
Multi-Broker Manager - Manages multiple AutoTrader instances for different brokers.

Each broker account runs independently with its own:
- TradingView AI Agent analysis
- Trading configuration (symbols, risk, hours)
- Broker connection (MetaApi or Bridge/API credentials)
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import BrokerAccount
from src.engines.trading.auto_trader import AnalysisMode, AutoTrader, BotConfig, BotStatus
from src.engines.trading.broker_factory import BrokerFactory, NoBrokerConfiguredError
from src.services.broker_credentials_service import (
    normalize_credentials,
    resolve_alpaca_runtime_credentials,
    resolve_ctrader_runtime_credentials,
    resolve_dxtrade_runtime_credentials,
    resolve_ig_runtime_credentials,
    resolve_matchtrader_runtime_credentials,
    resolve_mt_bridge_runtime_credentials,
    resolve_metaapi_runtime_credentials,
    resolve_oanda_runtime_credentials,
    should_use_mt_bridge,
)


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
    symbols: list[str]
    runtime_credentials: dict[str, str]

    # AutoTrader instance
    trader: AutoTrader

    # Status tracking
    status: str = "stopped"
    started_at: datetime | None = None
    last_error: str | None = None


class MultiBrokerManager:
    """
    Manages multiple AutoTrader instances, one per broker account.

    Each broker runs completely independently:
    - Own broker connection (MetaApi, Bridge or direct API credentials)
    - Own symbol list
    - Own risk settings
    - Own analysis interval
    - Own AI model selection
    """

    def __init__(self):
        self._instances: dict[int, BrokerInstance] = {}
        self._lock = asyncio.Lock()

    async def load_brokers(self, db: AsyncSession) -> list[BrokerAccount]:
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
                runtime_credentials=dict(config.broker_credentials or {}),
                trader=trader,
                status="initialized"
            )

            self._instances[broker_account.id] = instance
            return instance

    def _extract_runtime_credentials(self, account: BrokerAccount) -> dict[str, str]:
        broker_type = (account.broker_type or "metaapi").lower()
        credentials = normalize_credentials(account.credentials)

        if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
            runtime: dict[str, str] = {}
            metaapi_token = (account.metaapi_token or credentials.get("metaapi_token") or "").strip()
            metaapi_account_id = (account.metaapi_account_id or credentials.get("metaapi_account_id") or "").strip()
            if metaapi_token:
                runtime["access_token"] = metaapi_token
            if metaapi_account_id:
                runtime["account_id"] = metaapi_account_id
            default_platform = "mt4" if broker_type == "mt4" else "mt5"
            platform = (account.platform_id or credentials.get("platform") or default_platform).strip().lower()
            if platform not in {"mt4", "mt5"}:
                platform = default_platform
            runtime["platform"] = platform
            runtime["connection_mode"] = "metaapi"
            return runtime

        if broker_type == "oanda":
            runtime: dict[str, str] = {}
            api_key = (credentials.get("oanda_api_key") or credentials.get("api_key") or "").strip()
            account_id = (credentials.get("oanda_account_id") or credentials.get("account_id") or "").strip()
            environment = (credentials.get("oanda_environment") or credentials.get("environment") or "practice").strip()
            if api_key:
                runtime["api_key"] = api_key
            if account_id:
                runtime["account_id"] = account_id
            runtime["environment"] = environment or "practice"
            return runtime

        if broker_type == "ig":
            runtime: dict[str, str] = {}
            api_key = (credentials.get("ig_api_key") or credentials.get("api_key") or "").strip()
            username = (credentials.get("ig_username") or credentials.get("username") or "").strip()
            password = (credentials.get("ig_password") or credentials.get("password") or "").strip()
            account_id = (credentials.get("ig_account_id") or credentials.get("account_id") or "").strip()
            environment = (credentials.get("ig_environment") or credentials.get("environment") or "demo").strip()
            if api_key:
                runtime["api_key"] = api_key
            if username:
                runtime["username"] = username
            if password:
                runtime["password"] = password
            if account_id:
                runtime["account_id"] = account_id
            runtime["environment"] = environment or "demo"
            return runtime

        if broker_type == "alpaca":
            runtime: dict[str, str] = {}
            api_key = (credentials.get("alpaca_api_key") or credentials.get("api_key") or "").strip()
            secret_key = (
                credentials.get("alpaca_secret_key")
                or credentials.get("secret_key")
                or credentials.get("password")
                or ""
            ).strip()
            paper = (credentials.get("alpaca_paper") or credentials.get("paper") or "true").strip()
            if api_key:
                runtime["api_key"] = api_key
            if secret_key:
                runtime["secret_key"] = secret_key
            runtime["paper"] = paper.lower() if paper else "true"
            return runtime

        if broker_type in {"ctrader", "dxtrade", "matchtrader"}:
            runtime: dict[str, str] = {}
            account_id = (
                credentials.get("account_id")
                or credentials.get("account_number")
                or credentials.get("login")
                or ""
            ).strip()
            password = (
                credentials.get("account_password")
                or credentials.get("password")
                or ""
            ).strip()
            server_name = (credentials.get("server_name") or credentials.get("server") or "").strip()
            api_base_url = (credentials.get("api_base_url") or credentials.get("base_url") or "").strip()
            login_endpoint = (credentials.get("login_endpoint") or credentials.get("auth_endpoint") or "").strip()
            health_endpoint = (credentials.get("health_endpoint") or credentials.get("ping_endpoint") or "").strip()
            if account_id:
                runtime["account_id"] = account_id
            if password:
                runtime["password"] = password
            if server_name:
                runtime["server_name"] = server_name
            if api_base_url:
                runtime["api_base_url"] = api_base_url
            if login_endpoint:
                runtime["login_endpoint"] = login_endpoint
            if health_endpoint:
                runtime["health_endpoint"] = health_endpoint
            return runtime

        return credentials

    def _create_config_from_account(self, account: BrokerAccount) -> BotConfig:
        """Create BotConfig from BrokerAccount database model."""
        runtime_credentials = self._extract_runtime_credentials(account)

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
            metaapi_token=runtime_credentials.get("access_token"),
            metaapi_account_id=runtime_credentials.get("account_id"),
            broker_credentials=runtime_credentials,
        )

    async def start_broker(self, broker_id: int, db: AsyncSession) -> dict:
        """Start a specific broker's AutoTrader instance.

        IMPORTANT: Always reloads config from DB before starting to pick up any
        changes made in settings (enabled_models, symbols, risk, etc.)
        """
        # Load fresh broker data from DB
        result = await db.execute(
            select(BrokerAccount).where(BrokerAccount.id == broker_id)
        )
        broker_account = result.scalar_one_or_none()

        if not broker_account:
            return {"status": "error", "message": "Broker not found"}

        if not broker_account.is_enabled:
            return {"status": "error", "message": "Broker is disabled"}

        broker_type = (broker_account.broker_type or "metaapi").lower()

        runtime_credentials: dict[str, str] = {}
        try:
            if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
                if should_use_mt_bridge(broker_account):
                    runtime_credentials = resolve_mt_bridge_runtime_credentials(broker_account)
                else:
                    runtime_credentials = await resolve_metaapi_runtime_credentials(broker_account)
            elif broker_type == "oanda":
                runtime_credentials = resolve_oanda_runtime_credentials(broker_account)
            elif broker_type == "ig":
                runtime_credentials = resolve_ig_runtime_credentials(broker_account)
            elif broker_type == "alpaca":
                runtime_credentials = resolve_alpaca_runtime_credentials(broker_account)
            elif broker_type == "ctrader":
                runtime_credentials = resolve_ctrader_runtime_credentials(broker_account)
            elif broker_type == "dxtrade":
                runtime_credentials = resolve_dxtrade_runtime_credentials(broker_account)
            elif broker_type == "matchtrader":
                runtime_credentials = resolve_matchtrader_runtime_credentials(broker_account)
            else:
                runtime_credentials = normalize_credentials(broker_account.credentials)
        except HTTPException as exc:
            return {"status": "error", "message": str(exc.detail)}
        except Exception as exc:
            return {"status": "error", "message": f"Credential resolution failed: {exc}"}

        # Initialize if not exists, OR refresh config if exists
        if broker_id in self._instances:
            # Instance exists - refresh config from DB before starting
            instance = self._instances[broker_id]
            new_config = self._create_config_from_account(broker_account)
            if runtime_credentials:
                new_config.broker_credentials = dict(runtime_credentials)
                new_config.metaapi_token = runtime_credentials.get("access_token")
                new_config.metaapi_account_id = runtime_credentials.get("account_id")
            instance.trader.configure(new_config)

            # Update plain data fields
            instance.broker_name = broker_account.name
            instance.broker_type = broker_account.broker_type
            instance.symbols = list(broker_account.symbols)
            instance.runtime_credentials = dict(runtime_credentials)

            print(f"[MultiBrokerManager] Refreshed config for broker '{broker_account.name}' - enabled_models: {new_config.enabled_models}")
        else:
            # New instance
            instance = await self.initialize_broker(broker_account)
            if runtime_credentials:
                instance.runtime_credentials = dict(runtime_credentials)
                instance.trader.config.broker_credentials = dict(runtime_credentials)
                instance.trader.config.metaapi_token = runtime_credentials.get("access_token")
                instance.trader.config.metaapi_account_id = runtime_credentials.get("account_id")

        # Check if already running
        if instance.trader.state.status == BotStatus.RUNNING:
            return {"status": "already_running", "message": f"Broker '{broker_account.name}' is already running"}

        try:
            # Credentials are now passed via BotConfig - no need to set env vars!
            # This ensures each broker instance uses its OWN credentials
            runtime_account_id = (
                runtime_credentials.get("account_id")
                or runtime_credentials.get("account_number")
                or ""
            )
            print(
                f"[MultiBrokerManager] Starting broker '{broker_account.name}' with account "
                f"...{runtime_account_id[-4:] if runtime_account_id else 'N/A'}"
            )
            print(f"[MultiBrokerManager] Enabled models: {instance.trader.config.enabled_models}")

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
                "symbols": broker_account.symbols,
                "enabled_models": instance.trader.config.enabled_models
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

    async def pause_broker(self, broker_id: int) -> dict:
        """Pause a specific broker's AutoTrader instance (stops new trades but keeps monitoring)."""
        if broker_id not in self._instances:
            return {"status": "error", "message": "Broker instance not found"}

        instance = self._instances[broker_id]

        if instance.trader.state.status != BotStatus.RUNNING:
            return {"status": "error", "message": "Broker must be running to pause"}

        try:
            await instance.trader.pause()
            instance.status = "paused"

            return {
                "status": "success",
                "message": f"Broker '{instance.broker_name}' paused",
                "broker_id": broker_id
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to pause: {str(e)}"}

    async def resume_broker(self, broker_id: int) -> dict:
        """Resume a paused broker's AutoTrader instance."""
        if broker_id not in self._instances:
            return {"status": "error", "message": "Broker instance not found"}

        instance = self._instances[broker_id]

        if instance.trader.state.status != BotStatus.PAUSED:
            return {"status": "error", "message": "Broker must be paused to resume"}

        try:
            await instance.trader.resume()
            instance.status = "running"

            return {
                "status": "success",
                "message": f"Broker '{instance.broker_name}' resumed",
                "broker_id": broker_id
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to resume: {str(e)}"}

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

    def get_broker_status(self, broker_id: int) -> dict | None:
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

    async def _ensure_broker_connection(
        self,
        broker_id: int,
        broker_account: BrokerAccount | None = None,
    ):
        """Ensure a broker connection exists for a workspace, even if bot is stopped."""
        instance = self._instances.get(broker_id)
        if instance is None:
            if broker_account is None:
                return None
            instance = await self.initialize_broker(broker_account)

        if instance.trader.broker and getattr(instance.trader.broker, "is_connected", False):
            return instance.trader.broker

        if instance.trader.broker and not getattr(instance.trader.broker, "is_connected", False):
            try:
                await instance.trader.broker.connect()
                return instance.trader.broker
            except Exception:
                instance.trader.broker = None

        broker_type = (instance.broker_type or "metaapi").lower()
        runtime_credentials = dict(instance.runtime_credentials or {})
        if broker_account is not None:
            try:
                if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
                    if should_use_mt_bridge(broker_account):
                        runtime_credentials = resolve_mt_bridge_runtime_credentials(broker_account)
                    else:
                        runtime_credentials = await resolve_metaapi_runtime_credentials(broker_account)
                elif broker_type == "oanda":
                    runtime_credentials = resolve_oanda_runtime_credentials(broker_account)
                elif broker_type == "ig":
                    runtime_credentials = resolve_ig_runtime_credentials(broker_account)
                elif broker_type == "alpaca":
                    runtime_credentials = resolve_alpaca_runtime_credentials(broker_account)
                elif broker_type == "ctrader":
                    runtime_credentials = resolve_ctrader_runtime_credentials(broker_account)
                elif broker_type == "dxtrade":
                    runtime_credentials = resolve_dxtrade_runtime_credentials(broker_account)
                elif broker_type == "matchtrader":
                    runtime_credentials = resolve_matchtrader_runtime_credentials(broker_account)
                else:
                    runtime_credentials = normalize_credentials(broker_account.credentials)
                instance.runtime_credentials = dict(runtime_credentials)
            except HTTPException:
                return None
            except Exception:
                return None

        broker_kwargs: dict[str, Any] = {}
        if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
            if (runtime_credentials.get("connection_mode") or "").lower() == "bridge":
                account_number = (
                    runtime_credentials.get("account_number")
                    or runtime_credentials.get("login")
                )
                password = runtime_credentials.get("password")
                platform = (
                    runtime_credentials.get("platform")
                    or ("mt4" if broker_type == "mt4" else "mt5")
                )
                safe_platform = str(platform or "mt5").strip().lower()
                if safe_platform not in {"mt4", "mt5"}:
                    safe_platform = "mt4" if broker_type == "mt4" else "mt5"
                server_name = runtime_credentials.get("server_name") or runtime_credentials.get("server")
                if not account_number or not password:
                    return None
                if safe_platform == "mt4" and not server_name:
                    return None
                broker_kwargs = dict(runtime_credentials)
                broker_kwargs["account_number"] = account_number
                broker_kwargs["password"] = password
                if server_name:
                    broker_kwargs["server_name"] = server_name
                broker_kwargs["connection_mode"] = "bridge"
                broker_kwargs["platform"] = safe_platform
            else:
                access_token = runtime_credentials.get("access_token")
                account_id = runtime_credentials.get("account_id")
                if not access_token or not account_id:
                    return None
                broker_kwargs = {
                    "access_token": access_token,
                    "account_id": account_id,
                }
        elif broker_type == "oanda":
            api_key = runtime_credentials.get("api_key")
            account_id = runtime_credentials.get("account_id")
            environment = runtime_credentials.get("environment") or "practice"
            if not api_key or not account_id:
                return None
            broker_kwargs = {
                "api_key": api_key,
                "account_id": account_id,
                "environment": environment,
            }
        elif broker_type == "ig":
            api_key = runtime_credentials.get("api_key")
            username = runtime_credentials.get("username")
            password = runtime_credentials.get("password")
            environment = runtime_credentials.get("environment") or "demo"
            if not api_key or not username or not password:
                return None
            broker_kwargs = {
                "api_key": api_key,
                "username": username,
                "password": password,
                "environment": environment,
            }
            if runtime_credentials.get("account_id"):
                broker_kwargs["account_id"] = runtime_credentials["account_id"]
        elif broker_type == "alpaca":
            api_key = runtime_credentials.get("api_key")
            secret_key = runtime_credentials.get("secret_key")
            if not api_key or not secret_key:
                return None
            paper = (runtime_credentials.get("paper") or "true").lower() == "true"
            broker_kwargs = {
                "api_key": api_key,
                "secret_key": secret_key,
                "paper": paper,
            }
        else:
            broker_kwargs = runtime_credentials

        try:
            broker = BrokerFactory.create(
                broker_type=instance.broker_type,
                **broker_kwargs,
            )
        except (NoBrokerConfiguredError, NotImplementedError):
            return None

        try:
            await broker.connect()
        except Exception:
            return None
        instance.trader.broker = broker
        return broker

    async def get_broker_account_info(
        self,
        broker_id: int,
        broker_account: BrokerAccount | None = None,
    ) -> dict | None:
        """Get account info (balance, equity) for a specific broker."""
        broker = await self._ensure_broker_connection(broker_id, broker_account=broker_account)
        if not broker:
            return None

        try:
            account_info = await broker.get_account_info()
            open_positions = await broker.get_positions()
            return {
                "broker_id": broker_id,
                "balance": float(account_info.balance),
                "equity": float(account_info.equity),
                "margin_used": float(account_info.margin_used),
                "margin_available": float(account_info.margin_available),
                "unrealized_pnl": float(account_info.unrealized_pnl),
                "realized_pnl_today": float(getattr(account_info, "realized_pnl_today", 0) or 0),
                "open_positions": len(open_positions or []),
                "currency": account_info.currency,
            }
        except Exception as e:
            return {
                "broker_id": broker_id,
                "error": str(e)
            }

    async def get_broker_positions(
        self,
        broker_id: int,
        broker_account: BrokerAccount | None = None,
    ) -> list | None:
        """Get open positions for a specific broker."""
        instance = self._instances.get(broker_id)
        broker = await self._ensure_broker_connection(broker_id, broker_account=broker_account)
        if not broker or not instance:
            return None

        try:
            positions = await broker.get_positions()
            return [
                {
                    "position_id": p.position_id,
                    "symbol": p.symbol,
                    "side": p.side,
                    "size": float(p.size),
                    "entry_price": float(p.entry_price),
                    "current_price": float(p.current_price),
                    "unrealized_pnl": str(p.unrealized_pnl),
                    "unrealized_pnl_percent": str(
                        float(
                            getattr(
                                p,
                                "pnl_percent",
                                getattr(p, "unrealized_pnl_percent", 0),
                            )
                            or 0
                        )
                    ),
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
        except Exception:
            return []

    def get_all_statuses(self) -> list[dict]:
        """Get status of all broker instances."""
        return [
            self.get_broker_status(broker_id)
            for broker_id in self._instances
        ]

    def get_instance(self, broker_id: int) -> BrokerInstance | None:
        """Get a specific broker instance."""
        return self._instances.get(broker_id)

    def get_broker_logs(self, broker_id: int, limit: int = 50) -> dict | None:
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
        broker_type = (broker_account.broker_type or "metaapi").lower()
        runtime_credentials: dict[str, str] = {}
        try:
            if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
                if should_use_mt_bridge(broker_account):
                    runtime_credentials = resolve_mt_bridge_runtime_credentials(broker_account)
                else:
                    runtime_credentials = await resolve_metaapi_runtime_credentials(broker_account)
            elif broker_type == "oanda":
                runtime_credentials = resolve_oanda_runtime_credentials(broker_account)
            elif broker_type == "ig":
                runtime_credentials = resolve_ig_runtime_credentials(broker_account)
            elif broker_type == "alpaca":
                runtime_credentials = resolve_alpaca_runtime_credentials(broker_account)
            elif broker_type == "ctrader":
                runtime_credentials = resolve_ctrader_runtime_credentials(broker_account)
            elif broker_type == "dxtrade":
                runtime_credentials = resolve_dxtrade_runtime_credentials(broker_account)
            elif broker_type == "matchtrader":
                runtime_credentials = resolve_matchtrader_runtime_credentials(broker_account)
            else:
                runtime_credentials = normalize_credentials(broker_account.credentials)
        except HTTPException as exc:
            return {"status": "error", "message": str(exc.detail)}
        except Exception as exc:
            return {"status": "error", "message": f"Credential resolution failed: {exc}"}

        if runtime_credentials:
            new_config.broker_credentials = dict(runtime_credentials)
            new_config.metaapi_token = runtime_credentials.get("access_token")
            new_config.metaapi_account_id = runtime_credentials.get("account_id")
        instance.trader.configure(new_config)

        # Update plain data fields (avoids DetachedInstanceError)
        instance.broker_name = broker_account.name
        instance.broker_type = broker_account.broker_type
        instance.symbols = list(broker_account.symbols)
        instance.runtime_credentials = dict(runtime_credentials)

        return {
            "status": "success",
            "message": f"Configuration refreshed for '{broker_account.name}'",
            "config": {
                "symbols": new_config.symbols,
                "analysis_mode": new_config.analysis_mode.value,
            }
        }


# Singleton instance
_multi_broker_manager: MultiBrokerManager | None = None


def get_multi_broker_manager() -> MultiBrokerManager:
    """Get or create the multi-broker manager singleton."""
    global _multi_broker_manager
    if _multi_broker_manager is None:
        _multi_broker_manager = MultiBrokerManager()
    return _multi_broker_manager
