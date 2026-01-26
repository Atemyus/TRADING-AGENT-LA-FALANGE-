"""
WebSocket routes for real-time data streaming.

Provides live price updates from broker (when connected) or simulated data.
"""

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, Set, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections and price streaming."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.subscriptions: Dict[WebSocket, Set[str]] = {}
        self.price_subscriptions: Dict[WebSocket, Set[str]] = {}  # Symbol subscriptions
        self._streaming_task = None
        self._price_service = None

    async def connect(self, websocket: WebSocket):
        """Accept new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        self.subscriptions[websocket] = set()
        self.price_subscriptions[websocket] = set()

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)
        self.subscriptions.pop(websocket, None)
        self.price_subscriptions.pop(websocket, None)

    async def subscribe(self, websocket: WebSocket, channel: str):
        """Subscribe connection to channel."""
        if websocket in self.subscriptions:
            self.subscriptions[websocket].add(channel)

    async def subscribe_prices(self, websocket: WebSocket, symbols: List[str]):
        """Subscribe to price updates for specific symbols."""
        if websocket in self.price_subscriptions:
            self.price_subscriptions[websocket].update(symbols)

            # Start streaming if not already running
            if self._streaming_task is None or self._streaming_task.done():
                self._streaming_task = asyncio.create_task(self._stream_prices())

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
                    pass

    async def broadcast_price(self, symbol: str, price_data: dict):
        """Send price update to all subscribers of this symbol."""
        for websocket, symbols in self.price_subscriptions.items():
            if symbol in symbols or "all" in symbols:
                try:
                    await websocket.send_json(price_data)
                except Exception:
                    pass

    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception:
            pass

    async def _stream_prices(self):
        """Stream prices to all connected clients."""
        from src.services.price_streaming_service import get_price_streaming_service

        try:
            self._price_service = await get_price_streaming_service()
            subscribed_symbols: Set[str] = set()

            print(f"[WebSocket] Starting price streaming. Broker connected: {self._price_service.is_broker_connected}")
            print(f"[WebSocket] Data source: {self._price_service.data_source}")

            # Keep running while there are subscribers - dynamically add new symbols
            while any(self.price_subscriptions.values()):
                # Collect all subscribed symbols from all clients
                all_symbols: Set[str] = set()
                for symbols in self.price_subscriptions.values():
                    all_symbols.update(symbols)

                # If "all" is requested, use ALL available symbols
                if "all" in all_symbols:
                    all_symbols = set(self._price_service._base_prices.keys())

                # Subscribe to new symbols that aren't already subscribed
                new_symbols = all_symbols - subscribed_symbols
                if new_symbols:
                    print(f"[WebSocket] Subscribing to {len(new_symbols)} new symbols: {list(new_symbols)[:5]}...")
                    for symbol in new_symbols:
                        await self._price_service.subscribe(
                            symbol,
                            lambda tick, s=symbol: asyncio.create_task(
                                self._handle_tick(tick)
                            )
                        )
                        subscribed_symbols.add(symbol)

                await asyncio.sleep(1)

        except Exception as e:
            print(f"Price streaming error: {e}")
            import traceback
            traceback.print_exc()

    async def _handle_tick(self, tick):
        """Handle incoming tick and broadcast to clients."""
        price_data = {
            "type": "price",
            "symbol": tick.symbol,
            "bid": str(tick.bid),
            "ask": str(tick.ask),
            "mid": str(tick.mid),
            "spread": str(tick.spread),
            "timestamp": tick.timestamp.isoformat(),
            "source": self._price_service.data_source if self._price_service else "unknown",
        }
        await self.broadcast_price(tick.symbol, price_data)


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

    Subscribe to prices (real-time from broker):
    {"action": "subscribe", "channel": "prices", "symbols": ["EUR_USD", "GBP_USD"]}
    {"action": "subscribe", "channel": "prices", "symbols": ["all"]}  # All symbols

    Subscribe to account updates:
    {"action": "subscribe", "channel": "account"}

    Subscribe to positions:
    {"action": "subscribe", "channel": "positions"}

    Subscribe to signals:
    {"action": "subscribe", "channel": "signals"}

    Unsubscribe:
    {"action": "unsubscribe", "channel": "prices"}

    Ping/Pong for keepalive:
    {"action": "ping"}
    """
    await manager.connect(websocket)

    # Send initial connection info
    from src.services.price_streaming_service import get_price_streaming_service
    try:
        price_service = await get_price_streaming_service()
        source = price_service.data_source
        broker_connected = price_service.is_broker_connected
    except:
        source = "unknown"
        broker_connected = False

    await manager.send_personal(websocket, {
        "type": "connected",
        "data_source": source,
        "broker_connected": broker_connected,
        "timestamp": datetime.utcnow().isoformat(),
    })

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            action = data.get("action")
            channel = data.get("channel")

            if action == "subscribe" and channel:
                await manager.subscribe(websocket, channel)

                if channel == "prices":
                    symbols = data.get("symbols", ["all"])
                    await manager.subscribe_prices(websocket, symbols)
                    await manager.send_personal(websocket, {
                        "type": "subscribed",
                        "channel": channel,
                        "symbols": symbols,
                        "data_source": source,
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                else:
                    await manager.send_personal(websocket, {
                        "type": "subscribed",
                        "channel": channel,
                        "timestamp": datetime.utcnow().isoformat(),
                    })

            elif action == "unsubscribe" and channel:
                await manager.unsubscribe(websocket, channel)
                if channel == "prices":
                    manager.price_subscriptions[websocket] = set()
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

            elif action == "get_prices":
                # Get current snapshot of all prices
                try:
                    price_service = await get_price_streaming_service()
                    prices = price_service.get_all_prices()
                    await manager.send_personal(websocket, {
                        "type": "prices_snapshot",
                        "prices": {
                            symbol: {
                                "bid": str(tick.bid),
                                "ask": str(tick.ask),
                                "mid": str(tick.mid),
                                "spread": str(tick.spread),
                            }
                            for symbol, tick in prices.items()
                        },
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                except Exception as e:
                    await manager.send_personal(websocket, {
                        "type": "error",
                        "message": str(e),
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
