"""
Broker Accounts API - Endpoints for managing multiple broker accounts.
Each broker account runs independently with its own trading configuration.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.models import BrokerAccount


router = APIRouter(prefix="/brokers", tags=["Broker Accounts"])


# ============ Pydantic Models ============

class BrokerAccountCreate(BaseModel):
    """Request model for creating a broker account."""
    name: str
    broker_type: str = "metaapi"
    # MetaApi credentials
    metaapi_account_id: Optional[str] = None
    metaapi_token: Optional[str] = None
    # Status
    is_enabled: bool = True
    # Trading configuration
    symbols: Optional[List[str]] = None
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
    enabled_models: Optional[List[str]] = None
    # Trading hours
    trading_start_hour: int = 7
    trading_end_hour: int = 21
    trade_on_weekends: bool = False


class BrokerAccountUpdate(BaseModel):
    """Request model for updating a broker account."""
    name: Optional[str] = None
    broker_type: Optional[str] = None
    # MetaApi credentials
    metaapi_account_id: Optional[str] = None
    metaapi_token: Optional[str] = None
    # Status
    is_enabled: Optional[bool] = None
    # Trading configuration
    symbols: Optional[List[str]] = None
    # Risk settings
    risk_per_trade_percent: Optional[float] = None
    max_open_positions: Optional[int] = None
    max_daily_trades: Optional[int] = None
    max_daily_loss_percent: Optional[float] = None
    # Analysis settings
    analysis_mode: Optional[str] = None
    analysis_interval_seconds: Optional[int] = None
    min_confidence: Optional[float] = None
    min_models_agree: Optional[int] = None
    # AI models
    enabled_models: Optional[List[str]] = None
    # Trading hours
    trading_start_hour: Optional[int] = None
    trading_end_hour: Optional[int] = None
    trade_on_weekends: Optional[bool] = None


class BrokerAccountResponse(BaseModel):
    """Response model for broker account."""
    id: int
    name: str
    broker_type: str
    metaapi_account_id: Optional[str] = None
    metaapi_token: Optional[str] = None  # Will be masked
    is_enabled: bool
    is_connected: bool
    last_connected_at: Optional[str] = None
    symbols: List[str]
    risk_per_trade_percent: float
    max_open_positions: int
    max_daily_trades: int
    max_daily_loss_percent: float
    analysis_mode: str
    analysis_interval_seconds: int
    min_confidence: float
    min_models_agree: int
    enabled_models: List[str]
    trading_start_hour: int
    trading_end_hour: int
    trade_on_weekends: bool
    created_at: str
    updated_at: str


# ============ Helper Functions ============

def mask_key(key: Optional[str]) -> Optional[str]:
    """Mask sensitive data - show only last 4 chars."""
    if key and len(key) > 4:
        return "***" + key[-4:]
    return key


def preserve_if_masked(new_val: Optional[str], old_val: Optional[str]) -> Optional[str]:
    """Don't overwrite with masked values."""
    if new_val and new_val.startswith("***"):
        return old_val
    return new_val


def broker_to_response(broker: BrokerAccount) -> dict:
    """Convert BrokerAccount model to response dict with masked credentials."""
    return {
        "id": broker.id,
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


# ============ API Routes ============

@router.get("", response_model=List[BrokerAccountResponse])
async def list_brokers(db: AsyncSession = Depends(get_db)):
    """Get all broker accounts."""
    result = await db.execute(select(BrokerAccount).order_by(BrokerAccount.id))
    brokers = result.scalars().all()
    return [broker_to_response(b) for b in brokers]


@router.get("/{broker_id}", response_model=BrokerAccountResponse)
async def get_broker(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific broker account by ID."""
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

    return broker_to_response(broker)


@router.post("", response_model=BrokerAccountResponse)
async def create_broker(data: BrokerAccountCreate, db: AsyncSession = Depends(get_db)):
    """Create a new broker account."""
    broker = BrokerAccount(
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
    db: AsyncSession = Depends(get_db)
):
    """Update a broker account."""
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

    # Update fields if provided
    if data.name is not None:
        broker.name = data.name
    if data.broker_type is not None:
        broker.broker_type = data.broker_type
    if data.metaapi_account_id is not None:
        broker.metaapi_account_id = data.metaapi_account_id
    if data.metaapi_token is not None:
        # Preserve masked values
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
async def delete_broker(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a broker account."""
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

    await db.delete(broker)
    await db.flush()

    return {"status": "success", "message": f"Broker '{broker.name}' deleted"}


@router.post("/{broker_id}/test")
async def test_broker_connection(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Test connection to a broker account."""
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

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
                    # Update connection status
                    from datetime import datetime, timezone
                    broker.is_connected = True
                    broker.last_connected_at = datetime.now(timezone.utc)
                    await db.flush()

                    return {
                        "status": "success",
                        "message": "Connected successfully",
                        "account_name": account_info.get("name", "Unknown"),
                        "platform": account_info.get("platform", "mt5"),
                        "state": account_info.get("state", "Unknown"),
                        "broker": account_info.get("broker", "Unknown"),
                    }
                elif response.status_code == 404:
                    raise HTTPException(status_code=400, detail="Account not found. Check MetaApi Account ID.")
                elif response.status_code == 401:
                    raise HTTPException(status_code=400, detail="Invalid MetaApi Access Token")
                else:
                    raise HTTPException(status_code=400, detail=f"MetaApi error ({response.status_code})")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
    else:
        return {"status": "success", "message": f"Broker type '{broker.broker_type}' connection test not implemented"}


@router.post("/{broker_id}/toggle")
async def toggle_broker(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Enable or disable a broker account."""
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

    broker.is_enabled = not broker.is_enabled
    await db.flush()

    return {
        "status": "success",
        "broker_id": broker.id,
        "is_enabled": broker.is_enabled,
        "message": f"Broker '{broker.name}' {'enabled' if broker.is_enabled else 'disabled'}"
    }


# ============ Bot Control Endpoints ============

@router.post("/{broker_id}/start")
async def start_broker_bot(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Start the auto trading bot for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    manager = get_multi_broker_manager()
    result = await manager.start_broker(broker_id, db)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.post("/{broker_id}/stop")
async def stop_broker_bot(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Stop the auto trading bot for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    manager = get_multi_broker_manager()
    result = await manager.stop_broker(broker_id, db)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.get("/{broker_id}/status")
async def get_broker_bot_status(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Get the auto trading bot status for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    # Verify broker exists
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

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
async def refresh_broker_config(broker_id: int, db: AsyncSession = Depends(get_db)):
    """Refresh broker configuration from database without restart."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    manager = get_multi_broker_manager()
    result = await manager.refresh_broker_config(broker_id, db)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.get("/{broker_id}/logs")
async def get_broker_logs(broker_id: int, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get AI analysis logs for a specific broker."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    # Verify broker exists
    result = await db.execute(
        select(BrokerAccount).where(BrokerAccount.id == broker_id)
    )
    broker = result.scalar_one_or_none()

    if not broker:
        raise HTTPException(status_code=404, detail="Broker account not found")

    manager = get_multi_broker_manager()
    logs = manager.get_broker_logs(broker_id, limit)

    if not logs:
        return {
            "broker_id": broker_id,
            "name": broker.name,
            "logs": [],
            "total": 0,
            "message": "Broker not running or no logs available"
        }

    return logs


# ============ Global Control Endpoints ============

@router.post("/control/start-all")
async def start_all_brokers(db: AsyncSession = Depends(get_db)):
    """Start all enabled broker bots."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    manager = get_multi_broker_manager()
    result = await manager.start_all_enabled(db)

    return result


@router.post("/control/stop-all")
async def stop_all_brokers(db: AsyncSession = Depends(get_db)):
    """Stop all running broker bots."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    manager = get_multi_broker_manager()
    result = await manager.stop_all(db)

    return result


@router.get("/control/status-all")
async def get_all_broker_statuses(db: AsyncSession = Depends(get_db)):
    """Get status of all broker instances."""
    from src.engines.trading.multi_broker_manager import get_multi_broker_manager

    # Load all brokers from DB
    result = await db.execute(select(BrokerAccount).order_by(BrokerAccount.id))
    brokers = result.scalars().all()

    manager = get_multi_broker_manager()
    statuses = []

    for broker in brokers:
        bot_status = manager.get_broker_status(broker.id)
        if bot_status:
            statuses.append({
                **bot_status,
                "is_enabled": broker.is_enabled,
            })
        else:
            statuses.append({
                "broker_id": broker.id,
                "name": broker.name,
                "status": "not_initialized",
                "is_enabled": broker.is_enabled,
                "is_connected": broker.is_connected,
            })

    return {
        "total_brokers": len(brokers),
        "enabled": len([b for b in brokers if b.is_enabled]),
        "running": len([s for s in statuses if s.get("status") == "running"]),
        "brokers": statuses
    }
