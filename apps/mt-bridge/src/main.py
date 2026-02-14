from datetime import datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from src.config import BridgeSettings, get_settings
from src.providers import BridgeProviderError
from src.schemas import (
    ClosePositionRequest,
    ConnectSessionRequest,
    ConnectSessionResponse,
    GenericStatusResponse,
    ModifyPositionRequest,
    PlaceOrderRequest,
    SessionSnapshot,
)
from src.security import verify_bridge_api_key
from src.session_manager import SessionManager


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        candidate = (value or "").strip()
        if candidate:
            return candidate
    return None


settings: BridgeSettings = get_settings()
session_manager = SessionManager(settings=settings)

app = FastAPI(
    title="Prometheus MT Bridge",
    version="0.1.0",
    description="Session bridge for MT4/MT5 terminal nodes.",
)


@app.on_event("shutdown")
async def _on_shutdown():
    await session_manager.shutdown_all()


def _not_found(session_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Session not found: {session_id}")


@app.get("/api/v1/health")
async def health():
    sessions = await session_manager.list_sessions()
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "provider_mode": settings.MT_BRIDGE_PROVIDER_MODE,
        "sessions": len(sessions),
        "max_sessions": settings.MT_BRIDGE_MAX_SESSIONS,
        "terminal_auto_launch": settings.MT_BRIDGE_TERMINAL_AUTO_LAUNCH,
        "mt4_adapter_configured": bool((settings.MT_BRIDGE_MT4_ADAPTER_BASE_URL or "").strip()),
    }


@app.get("/api/v1/sessions", response_model=list[SessionSnapshot], dependencies=[Depends(verify_bridge_api_key)])
async def list_sessions():
    raw = await session_manager.list_sessions()
    return [SessionSnapshot(**item) for item in raw]


@app.post("/api/v1/sessions/connect", response_model=ConnectSessionResponse, dependencies=[Depends(verify_bridge_api_key)])
async def connect_session(data: ConnectSessionRequest):
    login = _first_non_empty(data.login, data.account_number)
    server = _first_non_empty(data.server, data.server_name)
    platform = (data.platform or settings.MT_BRIDGE_DEFAULT_PLATFORM or "mt5").strip().lower()
    if platform not in {"mt4", "mt5"}:
        platform = settings.MT_BRIDGE_DEFAULT_PLATFORM
    if not login or not server:
        raise HTTPException(status_code=400, detail="login/account_number and server/server_name are required")

    try:
        session = await session_manager.create_session(
            platform=platform,
            login=login,
            password=data.password,
            server=server,
            terminal_path=data.terminal_path,
            data_path=data.data_path,
            workspace_id=data.workspace_id,
        )
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Session connect failed: {exc}")

    return ConnectSessionResponse(
        session_id=session.session_id,
        platform=session.platform,
        login=session.login,
        server=session.server,
        connected_at=session.connected_at,
    )


@app.post("/api/v1/sessions/{session_id}/disconnect", response_model=GenericStatusResponse, dependencies=[Depends(verify_bridge_api_key)])
async def disconnect_session(session_id: str):
    ok = await session_manager.disconnect_session(session_id)
    if not ok:
        raise _not_found(session_id)
    return GenericStatusResponse(status="success", detail="Session disconnected")


@app.get("/api/v1/sessions/{session_id}/account", dependencies=[Depends(verify_bridge_api_key)])
async def get_account(session_id: str):
    try:
        session = await session_manager.get_session(session_id)
        return await session.provider.get_account_info()
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sessions/{session_id}/positions", dependencies=[Depends(verify_bridge_api_key)])
async def get_positions(session_id: str):
    try:
        session = await session_manager.get_session(session_id)
        return await session.provider.get_positions()
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/sessions/{session_id}/orders", dependencies=[Depends(verify_bridge_api_key)])
async def place_order(session_id: str, data: PlaceOrderRequest):
    try:
        session = await session_manager.get_session(session_id)
        payload = data.model_dump()
        return await session.provider.place_order(payload)
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sessions/{session_id}/orders/open", dependencies=[Depends(verify_bridge_api_key)])
async def get_open_orders(session_id: str):
    try:
        session = await session_manager.get_session(session_id)
        return await session.provider.get_open_orders()
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sessions/{session_id}/orders/{order_id}", dependencies=[Depends(verify_bridge_api_key)])
async def get_order(session_id: str, order_id: str):
    try:
        session = await session_manager.get_session(session_id)
        order = await session.provider.get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
        return order
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/v1/sessions/{session_id}/orders/{order_id}", response_model=GenericStatusResponse, dependencies=[Depends(verify_bridge_api_key)])
async def cancel_order(session_id: str, order_id: str):
    try:
        session = await session_manager.get_session(session_id)
        ok = await session.provider.cancel_order(order_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Order not found/cancellable: {order_id}")
        return GenericStatusResponse(status="success", detail="Order cancelled")
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/sessions/{session_id}/positions/close", dependencies=[Depends(verify_bridge_api_key)])
async def close_position(session_id: str, data: ClosePositionRequest):
    try:
        session = await session_manager.get_session(session_id)
        payload = data.model_dump(exclude_none=True)
        return await session.provider.close_position(payload)
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/v1/sessions/{session_id}/positions/modify", response_model=GenericStatusResponse, dependencies=[Depends(verify_bridge_api_key)])
async def modify_position(session_id: str, data: ModifyPositionRequest):
    try:
        session = await session_manager.get_session(session_id)
        payload = data.model_dump(exclude_none=True)
        ok = await session.provider.modify_position(payload)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Position not found for symbol: {data.symbol}")
        return GenericStatusResponse(status="success", detail="Position modified")
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sessions/{session_id}/prices/{symbol}", dependencies=[Depends(verify_bridge_api_key)])
async def get_price(session_id: str, symbol: str):
    try:
        session = await session_manager.get_session(session_id)
        return await session.provider.get_price(symbol)
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sessions/{session_id}/prices", dependencies=[Depends(verify_bridge_api_key)])
async def get_prices(
    session_id: str,
    symbols: str | None = Query(default=None, description="comma-separated symbols"),
):
    try:
        session = await session_manager.get_session(session_id)
        selected = [s.strip() for s in (symbols or "").split(",") if s.strip()]
        if not selected:
            raise HTTPException(status_code=400, detail="symbols query parameter is required")
        prices: dict[str, Any] = {}
        for symbol in selected:
            prices[symbol] = await session.provider.get_price(symbol)
        return {"prices": prices}
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/v1/sessions/{session_id}/candles/{symbol}", dependencies=[Depends(verify_bridge_api_key)])
async def get_candles(
    session_id: str,
    symbol: str,
    timeframe: str = Query(default="M5"),
    count: int = Query(default=100, ge=1, le=2000),
    from_param: str | None = Query(default=None, alias="from"),
    to_param: str | None = Query(default=None, alias="to"),
    from_time: str | None = Query(default=None),
    to_time: str | None = Query(default=None),
):
    try:
        session = await session_manager.get_session(session_id)
        resolved_from = _first_non_empty(from_param, from_time)
        resolved_to = _first_non_empty(to_param, to_time)
        return await session.provider.get_candles(
            symbol=symbol,
            timeframe=timeframe,
            count=count,
            from_time=resolved_from,
            to_time=resolved_to,
        )
    except KeyError:
        raise _not_found(session_id)
    except BridgeProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.exception_handler(BridgeProviderError)
async def _provider_error_handler(_, exc: BridgeProviderError):
    return JSONResponse(
        status_code=400,
        content={"status": "error", "detail": str(exc)},
    )
