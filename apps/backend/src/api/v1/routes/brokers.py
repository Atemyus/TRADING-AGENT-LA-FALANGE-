"""
Broker Accounts API - Endpoints for managing multiple broker accounts.
Each broker account runs independently with its own trading configuration.
"""

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.routes.auth import get_licensed_user
from src.core.database import get_db
from src.core.models import BrokerAccount, User

router = APIRouter(prefix="/brokers", tags=["Broker Accounts"])


# ============ Pydantic Models ============

class BrokerAccountCreate(BaseModel):
    """Request model for creating a broker account."""

    name: str
    broker_type: str = "metaapi"
    slot_index: int | None = Field(None, ge=1, le=100)
    # MetaApi credentials
    metaapi_account_id: str | None = None
    metaapi_token: str | None = None
    # Status
    is_enabled: bool = True
    # Trading configuration
    symbols: list[str] | None = None
    # Risk settings
    risk_per_trade_percent: float = 1.0
    max_open_positions: int = 3
    max_daily_trades: int = 10
    max_daily_loss_percent: float = 5.0
    # Analysis settings
    analysis_mode: str = "standard"
    analysis_interval_seconds: int = 300
    min_confidence: float = 75.0
    min_models_agree: int = 4
    # AI models
    enabled_models: list[str] | None = None
    # Trading hours
    trading_start_hour: int = 7
    trading_end_hour: int = 21
    trade_on_weekends: bool = False


class BrokerAccountUpdate(BaseModel):
    """Request model for updating a broker account."""

    name: str | None = None
    broker_type: str | None = None
    slot_index: int | None = Field(None, ge=1, le=100)
    # MetaApi credentials
    metaapi_account_id: str | None = None
    metaapi_token: str | None = None
    # Status
    is_enabled: bool | None = None
    # Trading configuration
    symbols: list[str] | None = None
    # Risk settings
    risk_per_trade_percent: float | None = None
    max_open_positions: int | None = None
    max_daily_trades: int | None = None
    max_daily_loss_percent: float | None = None
    # Analysis settings
    analysis_mode: str | None = None
    analysis_interval_seconds: int | None = None
    min_confidence: float | None = None
    min_models_agree: int | None = None
    # AI models
    enabled_models: list[str] | None = None
    # Trading hours
    trading_start_hour: int | None = None
    trading_end_hour: int | None = None
    trade_on_weekends: bool | None = None


class BrokerAccountResponse(BaseModel):
    """Response model for broker account."""

    id: int
    user_id: int | None = None
    slot_index: int | None = None
    name: str
    broker_type: str
    metaapi_account_id: str | None = None
    metaapi_token: str | None = None  # Will be masked
    is_enabled: bool
    is_connected: bool
    last_connected_at: str | None = None
    symbols: list[str]
    risk_per_trade_percent: float
    max_open_positions: int
    max_daily_trades: int
    max_daily_loss_percent: float
    analysis_mode: str
    analysis_interval_seconds: int
    min_confidence: float
    min_models_agree: int
    enabled_models: list[str]
    trading_start_hour: int
    trading_end_hour: int
    trade_on_weekends: bool
    created_at: str
    updated_at: str


# ============ Helper Functions ============

def mask_key(key: str | None) -> str | None:
    """Mask sensitive data - show only last 4 chars."""
    if key and len(key) > 4:
        return "***" + key[-4:]
    return key


def preserve_if_masked(new_val: str | None, old_val: str | None) -> str | None:
    """Don't overwrite with masked values."""
    if new_val and new_val.startswith("***"):
        return old_val
    return new_val


def broker_to_response(broker: BrokerAccount) -> dict:
    """Convert BrokerAccount model to response dict with masked credentials."""
    return {
        "id": broker.id,
        "user_id": broker.user_id,
        "slot_index": broker.slot_index,
        "name": broker.name,
        "broker_type": broker.broker_type,
        "metaapi_account_id": broker.metaapi_account_id,
        "metaapi_token": mask_key(broker.metaapi_token),
        "is_enabled": broker.is_enabled,
        "is_connected": broker.is_connected,
        "last_connected_at": broker.last_connected_at.isoformat() if broker.last_connected_at else None,
        "symbols": broker.symbols,
        "risk_per_trade_percent": broker.risk_per_trade_percent,
        "max_open_positions": broker.max_open_positions,
        "max_daily_trades": broker.max_daily_trades,
        "max_daily_loss_percent": broker.max_daily_loss_percent,
        "analysis_mode": broker.analysis_mode,
        "analysis_interval_seconds": broker.analysis_interval_seconds,
        "min_confidence": broker.min_confidence,
        "min_models_agree": broker.min_models_agree,
        "enabled_models": broker.enabled_models,
        "trading_start_hour": broker.trading_start_hour,
        "trading_end_hour": broker.trading_end_hour,
        "trade_on_weekends": broker.trade_on_weekends,
        "created_at": broker.created_at.isoformat(),
        "updated_at": broker.updated_at.isoformat(),
    }


def _sorted_brokers_query(current_user: User):
    query = select(BrokerAccount)
    if not current_user.is_superuser:
        query = query.where(BrokerAccount.user_id == current_user.id)
    return query.order_by(BrokerAccount.slot_index.is_(None), BrokerAccount.slot_index, BrokerAccount.id)


async def _get_user_broker_or_404(
    db: AsyncSession,
    broker_id: int,
    current_user: User,
) -> BrokerAccount:
    query = select(BrokerAccount).where(BrokerAccount.id == broker_id)
    if not current_user.is_superuser:
        query = query.where(BrokerAccount.user_id == current_user.id)

    result = await db.execute(query)
    broker = result.scalar_one_or_none()
    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")
    return broker


async def _get_slot_limit_and_used(
    db: AsyncSession,
    current_user: User,
    exclude_broker_id: int | None = None,
) -> tuple[int, set[int], int]:
    if current_user.is_superuser:
        return 100, set(), 0

    if not current_user.license:
        raise HTTPException(status_code=403, detail="No valid license associated with this account")

    max_slots = max(1, int(current_user.license.broker_slots or 1))
    query = select(BrokerAccount.slot_index).where(BrokerAccount.user_id == current_user.id)
    if exclude_broker_id is not None:
        query = query.where(BrokerAccount.id != exclude_broker_id)
    result = await db.execute(query)
    slot_rows = result.all()
    used_slots = {int(slot) for (slot,) in slot_rows if slot is not None}
    return max_slots, used_slots, len(slot_rows)


async def _resolve_create_slot_index(
    db: AsyncSession,
    current_user: User,
    requested_slot: int | None,
) -> int | None:
    if current_user.is_superuser:
        return requested_slot

    max_slots, used_slots, total_accounts = await _get_slot_limit_and_used(db, current_user)
    if total_accounts >= max_slots:
        raise HTTPException(
            status_code=400,
            detail=f"No available broker slots. Your license allows {max_slots} broker workspace(s).",
        )

    if requested_slot is not None:
        if requested_slot < 1 or requested_slot > max_slots:
            raise HTTPException(
                status_code=400,
                detail=f"Requested slot {requested_slot} is outside your license limit (1-{max_slots})",
            )
        if requested_slot in used_slots:
            raise HTTPException(
                status_code=400,
                detail=f"Slot {requested_slot} is already occupied by another broker",
            )
        return requested_slot

    for slot in range(1, max_slots + 1):
        if slot not in used_slots:
            return slot

    raise HTTPException(
        status_code=400,
        detail=f"No available broker slots. Your license allows {max_slots} broker workspace(s).",
    )


async def _validate_update_slot_index(
    db: AsyncSession,
    current_user: User,
    broker: BrokerAccount,
    requested_slot: int,
) -> int:
    if current_user.is_superuser:
        return requested_slot

    max_slots, used_slots, _ = await _get_slot_limit_and_used(db, current_user, exclude_broker_id=broker.id)
    if requested_slot < 1 or requested_slot > max_slots:
        raise HTTPException(
            status_code=400,
            detail=f"Requested slot {requested_slot} is outside your license limit (1-{max_slots})",
        )
    if requested_slot in used_slots:
        raise HTTPException(
            status_code=400,
            detail=f"Slot {requested_slot} is already occupied by another broker",
        )
    return requested_slot


# ============ API Routes ============

@router.get("", response_model=list[BrokerAccountResponse])
async def list_brokers(
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get broker accounts visible to current user."""
    result = await db.execute(_sorted_brokers_query(current_user))
    brokers = result.scalars().all()
    return [broker_to_response(b) for b in brokers]


@router.get("/{broker_id}", response_model=BrokerAccountResponse)
async def get_broker(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific broker account by ID."""
    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    return broker_to_response(broker)


@router.post("", response_model=BrokerAccountResponse)
async def create_broker(
    data: BrokerAccountCreate,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new broker account."""
    slot_index = await _resolve_create_slot_index(db, current_user, data.slot_index)

    broker = BrokerAccount(
        user_id=None if current_user.is_superuser else current_user.id,
        slot_index=slot_index,
        name=data.name,
        broker_type=data.broker_type,
        metaapi_account_id=data.metaapi_account_id,
        metaapi_token=data.metaapi_token,
        is_enabled=data.is_enabled,
        risk_per_trade_percent=data.risk_per_trade_percent,
        max_open_positions=data.max_open_positions,
        max_daily_trades=data.max_daily_trades,
        max_daily_loss_percent=data.max_daily_loss_percent,
        analysis_mode=data.analysis_mode,
        analysis_interval_seconds=data.analysis_interval_seconds,
        min_confidence=data.min_confidence,
        min_models_agree=data.min_models_agree,
        trading_start_hour=data.trading_start_hour,
        trading_end_hour=data.trading_end_hour,
        trade_on_weekends=data.trade_on_weekends,
    )

    # Set list properties via setters
    if data.symbols:
        broker.symbols = data.symbols
    if data.enabled_models:
        broker.enabled_models = data.enabled_models

    db.add(broker)
    await db.flush()
    await db.refresh(broker)

    return broker_to_response(broker)


@router.put("/{broker_id}", response_model=BrokerAccountResponse)
async def update_broker(
    broker_id: int,
    data: BrokerAccountUpdate,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a broker account."""
    broker = await _get_user_broker_or_404(db, broker_id, current_user)

    # Update fields if provided
    if data.name is not None:
        broker.name = data.name
    if data.broker_type is not None:
        broker.broker_type = data.broker_type
    if data.slot_index is not None:
        broker.slot_index = await _validate_update_slot_index(db, current_user, broker, data.slot_index)
    if data.metaapi_account_id is not None:
        broker.metaapi_account_id = data.metaapi_account_id
    if data.metaapi_token is not None:
        broker.metaapi_token = preserve_if_masked(data.metaapi_token, broker.metaapi_token)
    if data.is_enabled is not None:
        broker.is_enabled = data.is_enabled
    if data.symbols is not None:
        broker.symbols = data.symbols
    if data.risk_per_trade_percent is not None:
        broker.risk_per_trade_percent = data.risk_per_trade_percent
    if data.max_open_positions is not None:
        broker.max_open_positions = data.max_open_positions
    if data.max_daily_trades is not None:
        broker.max_daily_trades = data.max_daily_trades
    if data.max_daily_loss_percent is not None:
        broker.max_daily_loss_percent = data.max_daily_loss_percent
    if data.analysis_mode is not None:
        broker.analysis_mode = data.analysis_mode
    if data.analysis_interval_seconds is not None:
        broker.analysis_interval_seconds = data.analysis_interval_seconds
    if data.min_confidence is not None:
        broker.min_confidence = data.min_confidence
    if data.min_models_agree is not None:
        broker.min_models_agree = data.min_models_agree
    if data.enabled_models is not None:
        broker.enabled_models = data.enabled_models
    if data.trading_start_hour is not None:
        broker.trading_start_hour = data.trading_start_hour
    if data.trading_end_hour is not None:
        broker.trading_end_hour = data.trading_end_hour
    if data.trade_on_weekends is not None:
        broker.trade_on_weekends = data.trade_on_weekends

    await db.flush()
    await db.refresh(broker)

    return broker_to_response(broker)


@router.delete("/{broker_id}")
async def delete_broker(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a broker account."""
    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    await db.delete(broker)
    await db.flush()
    return {"status": "success", "message": f"Broker '{broker.name}' deleted"}


@router.post("/{broker_id}/test")
async def test_broker_connection(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Test connection to a broker account."""
    broker = await _get_user_broker_or_404(db, broker_id, current_user)

    if broker.broker_type == "metaapi":
        if not broker.metaapi_token or not broker.metaapi_account_id:
            raise HTTPException(status_code=400, detail="MetaApi credentials not configured")

        try:
            import httpx

            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                response = await client.get(
                    f"https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/{broker.metaapi_account_id}",
                    headers={"auth-token": broker.metaapi_token},
                )
                if response.status_code == 200:
                    account_info = response.json()
                    from datetime import datetime

                    broker.is_connected = True
                    broker.last_connected_at = datetime.now(UTC)
                    await db.flush()
                    return {
                        "status": "success",
                        "message": "Connected successfully",
                        "account_name": account_info.get("name", "Unknown"),
                        "platform": account_info.get("platform", "mt5"),
                        "state": account_info.get("state", "Unknown"),
                        "broker": account_info.get("broker", "Unknown"),
                    }
                if response.status_code == 404:
                    raise HTTPException(status_code=400, detail="Account not found. Check MetaApi Account ID.")
                if response.status_code == 401:
                    raise HTTPException(status_code=400, detail="Invalid MetaApi Access Token")
                raise HTTPException(status_code=400, detail=f"MetaApi error ({response.status_code})")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connection test failed: {e}")

    return {"status": "success", "message": f"Broker type '{broker.broker_type}' connection test not implemented"}


@router.post("/{broker_id}/toggle")
async def toggle_broker(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Enable or disable a broker account."""
    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    broker.is_enabled = not broker.is_enabled
    await db.flush()
    return {
        "status": "success",
        "broker_id": broker.id,
        "is_enabled": broker.is_enabled,
        "message": f"Broker '{broker.name}' {'enabled' if broker.is_enabled else 'disabled'}",
    }


# ============ Bot Control Endpoints ============

@router.post("/{broker_id}/start")
async def start_broker_bot(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Start the auto trading bot for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    result = await manager.start_broker(broker_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/{broker_id}/stop")
async def stop_broker_bot(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop the auto trading bot for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    result = await manager.stop_broker(broker_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/{broker_id}/pause")
async def pause_broker_bot(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Pause the auto trading bot for a specific broker (stops new trades, keeps monitoring)."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    result = await manager.pause_broker(broker_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.post("/{broker_id}/resume")
async def resume_broker_bot(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Resume the auto trading bot for a specific broker after pause."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    result = await manager.resume_broker(broker_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/{broker_id}/status")
async def get_broker_bot_status(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the auto trading bot status for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    status = manager.get_broker_status(broker_id)

    if not status:
        return {
            "broker_id": broker_id,
            "name": broker.name,
            "status": "not_initialized",
            "is_enabled": broker.is_enabled,
            "is_connected": broker.is_connected,
        }

    return {**status, "is_enabled": broker.is_enabled}


@router.post("/{broker_id}/refresh-config")
async def refresh_broker_config(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Refresh broker configuration from database without restart."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    result = await manager.refresh_broker_config(broker_id, db)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result


@router.get("/{broker_id}/logs")
async def get_broker_logs(
    broker_id: int,
    limit: int = 50,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI analysis logs for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    logs = manager.get_broker_logs(broker_id, limit)

    if not logs:
        return {
            "broker_id": broker_id,
            "name": broker.name,
            "logs": [],
            "total": 0,
            "message": "Broker not running or no logs available",
        }

    return logs


@router.get("/{broker_id}/account")
async def get_broker_account_info(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get account info (balance, equity) for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    account_info = await manager.get_broker_account_info(broker_id)

    if not account_info:
        return {
            "broker_id": broker_id,
            "name": broker.name,
            "balance": None,
            "equity": None,
            "message": "Broker not running or not connected",
        }

    return {**account_info, "name": broker.name}


@router.get("/{broker_id}/positions")
async def get_broker_positions(
    broker_id: int,
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get open positions for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    broker = await _get_user_broker_or_404(db, broker_id, current_user)
    manager = get_multi_broker_manager()
    positions = await manager.get_broker_positions(broker_id)

    if positions is None:
        return {
            "broker_id": broker_id,
            "name": broker.name,
            "positions": [],
            "message": "Broker not running or not connected",
        }

    return {
        "broker_id": broker_id,
        "name": broker.name,
        "positions": positions,
    }


# ============ Global Control Endpoints ============

@router.post("/control/start-all")
async def start_all_brokers(
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Start all enabled broker bots visible to the current user."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    result = await db.execute(_sorted_brokers_query(current_user))
    brokers = result.scalars().all()

    manager = get_multi_broker_manager()
    results = []
    for broker in brokers:
        if broker.is_enabled:
            broker_result = await manager.start_broker(broker.id, db)
            results.append(
                {
                    "broker_id": broker.id,
                    "name": broker.name,
                    **broker_result,
                }
            )

    return {
        "status": "success",
        "started": len([r for r in results if r.get("status") == "success"]),
        "total_enabled": len([b for b in brokers if b.is_enabled]),
        "results": results,
    }


@router.post("/control/stop-all")
async def stop_all_brokers(
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop all running broker bots visible to the current user."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    result = await db.execute(_sorted_brokers_query(current_user))
    brokers = result.scalars().all()

    manager = get_multi_broker_manager()
    results = []
    for broker in brokers:
        status = manager.get_broker_status(broker.id)
        if status and status.get("status") in {"running", "paused"}:
            broker_result = await manager.stop_broker(broker.id, db)
            results.append(
                {
                    "broker_id": broker.id,
                    "name": broker.name,
                    **broker_result,
                }
            )

    return {
        "status": "success",
        "stopped": len([r for r in results if r.get("status") == "success"]),
        "results": results,
    }


@router.get("/control/positions-all")
async def get_all_broker_positions(
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get open positions from all running brokers visible to current user."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    result = await db.execute(_sorted_brokers_query(current_user))
    brokers = result.scalars().all()

    manager = get_multi_broker_manager()
    all_positions = []
    for broker in brokers:
        positions = await manager.get_broker_positions(broker.id)
        if positions:
            all_positions.extend(positions)

    return {
        "total_positions": len(all_positions),
        "positions": all_positions,
    }


@router.get("/control/account-summary")
async def get_aggregated_account_summary(
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated account summary from brokers visible to current user."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    result = await db.execute(_sorted_brokers_query(current_user))
    brokers = result.scalars().all()

    manager = get_multi_broker_manager()

    total_balance = 0.0
    total_equity = 0.0
    total_unrealized_pnl = 0.0
    total_margin_used = 0.0
    broker_count = 0
    currency = "USD"
    broker_details = []

    for broker in brokers:
        account_info = await manager.get_broker_account_info(broker.id)
        if account_info and "balance" in account_info and account_info["balance"] is not None:
            total_balance += account_info["balance"]
            total_equity += account_info.get("equity", 0) or 0
            total_unrealized_pnl += account_info.get("unrealized_pnl", 0) or 0
            total_margin_used += account_info.get("margin_used", 0) or 0
            currency = account_info.get("currency", "USD")
            broker_count += 1
            broker_details.append(
                {
                    "broker_id": broker.id,
                    "name": broker.name,
                    "balance": account_info["balance"],
                    "equity": account_info.get("equity"),
                    "unrealized_pnl": account_info.get("unrealized_pnl"),
                }
            )

    total_positions = 0
    for broker in brokers:
        positions = await manager.get_broker_positions(broker.id)
        if positions:
            total_positions += len(positions)

    return {
        "total_balance": total_balance,
        "total_equity": total_equity,
        "total_unrealized_pnl": total_unrealized_pnl,
        "total_margin_used": total_margin_used,
        "total_open_positions": total_positions,
        "broker_count": broker_count,
        "currency": currency,
        "brokers": broker_details,
    }


@router.get("/control/status-all")
async def get_all_broker_statuses(
    current_user: User = Depends(get_licensed_user),
    db: AsyncSession = Depends(get_db),
):
    """Get status of broker instances visible to current user."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    result = await db.execute(_sorted_brokers_query(current_user))
    brokers = result.scalars().all()

    manager = get_multi_broker_manager()
    statuses = []

    for broker in brokers:
        bot_status = manager.get_broker_status(broker.id)
        if bot_status:
            statuses.append({**bot_status, "is_enabled": broker.is_enabled})
        else:
            statuses.append(
                {
                    "broker_id": broker.id,
                    "name": broker.name,
                    "status": "not_initialized",
                    "is_enabled": broker.is_enabled,
                    "is_connected": broker.is_connected,
                }
            )

    return {
        "total_brokers": len(brokers),
        "enabled": len([b for b in brokers if b.is_enabled]),
        "running": len([s for s in statuses if s.get("status") == "running"]),
        "brokers": statuses,
    }
