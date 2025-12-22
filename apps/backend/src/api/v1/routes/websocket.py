"""
WebSocket routes for real-time data streaming.
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe connection to channel."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(channel)

    async def unsubscribe(self, websocket: WebSocket, channel: str):
        """Unsubscribe connection from channel."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].discard(channel)

    async def broadcast(self, channel: str, message: dict):
        """Send message to all subscribers of a channel."""
        for websocket, channels in self.subscriptions.items():
            if channel in channels:
                try:
                    await websocket.send_json(message)
                except Exception:
                    # Connection might be closed
                    pass

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass


manager = ConnectionManager()


class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time updates.

    Supports the following message types:

    Subscribe to prices:
    {"action": "subscribe", "channel": "prices", "symbols": ["EUR_USD", "GBP_USD"]}

    Subscribe to account updates:
    {"action": "subscribe", "channel": "account"}

    Subscribe to positions:
    {"action": "subscribe", "channel": "positions"}

    Subscribe to signals:
    {"action": "subscribe", "channel": "signals"}

    Unsubscribe:
    {"action": "unsubscribe", "channel": "prices"}
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            action = data.get("action")
            channel = data.get("channel")

            if action == "subscribe" and channel:
                await manager.subscribe(websocket, channel)
                await manager.send_personal(websocket, {
                    "type": "subscribed",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                # If subscribing to prices, start streaming
                if channel == "prices":
                    symbols = data.get("symbols", [])
                    # TODO: Start price streaming task
                    await manager.send_personal(websocket, {
                        "type": "info",
                        "message": f"Subscribed to prices for {symbols}",
                    })

            elif action == "unsubscribe" and channel:
                await manager.unsubscribe(websocket, channel)
                await manager.send_personal(websocket, {
                    "type": "unsubscribed",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                })

            elif action == "ping":
                await manager.send_personal(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat(),
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)
        raise e


async def broadcast_price_update(symbol: str, bid: Decimal, ask: Decimal):
    """Broadcast price update to all subscribers."""
    await manager.broadcast("prices", {
        "type": "price",
        "symbol": symbol,
        "bid": str(bid),
        "ask": str(ask),
        "mid": str((bid + ask) / 2),
        "spread": str(ask - bid),
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_position_update(position_data: dict):
    """Broadcast position update to all subscribers."""
    await manager.broadcast("positions", {
        "type": "position",
        "data": position_data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_account_update(account_data: dict):
    """Broadcast account update to all subscribers."""
    await manager.broadcast("account", {
        "type": "account",
        "data": account_data,
        "timestamp": datetime.utcnow().isoformat(),
    })


async def broadcast_signal(signal_data: dict):
    """Broadcast AI trading signal."""
    await manager.broadcast("signals", {
        "type": "signal",
        "data": signal_data,
        "timestamp": datetime.utcnow().isoformat(),
    })
