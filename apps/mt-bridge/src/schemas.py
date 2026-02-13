from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConnectSessionRequest(BaseModel):
    platform: str | None = None
    login: str | None = None
    account_number: str | None = None
    password: str
    server: str | None = None
    server_name: str | None = None
    terminal_path: str | None = None
    data_path: str | None = None
    workspace_id: str | None = None


class ConnectSessionResponse(BaseModel):
    session_id: str
    platform: str
    login: str
    server: str
    connected_at: datetime


class SessionSnapshot(BaseModel):
    session_id: str
    platform: str
    login: str
    server: str
    connected_at: datetime
    last_seen_at: datetime
    provider: str


class PlaceOrderRequest(BaseModel):
    symbol: str
    side: str
    order_type: str = "market"
    volume: float = Field(gt=0)
    time_in_force: str | None = "gtc"
    stop_loss: float | None = None
    take_profit: float | None = None
    price: float | None = None
    stop_price: float | None = None
    client_order_id: str | None = None


class ClosePositionRequest(BaseModel):
    symbol: str
    volume: float | None = None


class ModifyPositionRequest(BaseModel):
    symbol: str
    stop_loss: float | None = None
    take_profit: float | None = None


class GenericStatusResponse(BaseModel):
    status: str = "success"
    detail: str | None = None
    data: dict[str, Any] | None = None
