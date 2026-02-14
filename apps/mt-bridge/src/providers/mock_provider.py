import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from .base import BaseTerminalProvider


class MockTerminalProvider(BaseTerminalProvider):
    """
    In-memory provider for local development/testing.
    """

    def __init__(self):
        self._connected = False
        self._login = ""
        self._server = ""
        self._platform = "mt5"
        self._balance = 10000.0
        self._equity = 10000.0
        self._positions: list[dict[str, Any]] = []
        self._open_orders: list[dict[str, Any]] = []
        self._rng = random.Random()

    @property
    def name(self) -> str:
        return "mock"

    async def connect(
        self,
        *,
        login: str,
        password: str,
        server: str | None,
        platform: str,
        terminal_path: str | None = None,
        data_path: str | None = None,
        workspace_id: str | None = None,
        server_candidates: list[str] | None = None,
    ) -> None:
        _ = password, terminal_path, data_path, workspace_id, server_candidates
        self._login = login
        self._server = str(server or "").strip()
        self._platform = platform
        self._rng.seed(f"{login}:{self._server}:{platform}")
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    def _base_price(self, symbol: str) -> float:
        normalized = symbol.upper().replace("/", "").replace("_", "")
        defaults = {
            "EURUSD": 1.08,
            "GBPUSD": 1.26,
            "USDJPY": 153.20,
            "XAUUSD": 2650.0,
            "US30": 42100.0,
        }
        return defaults.get(normalized, 100.0)

    def _tick(self, symbol: str) -> tuple[float, float]:
        base = self._base_price(symbol)
        variance = 0.0008 if base < 10 else 0.2
        mid = base + self._rng.uniform(-variance, variance)
        spread = 0.0001 if base < 10 else 0.1
        bid = round(mid - spread / 2, 6 if base < 10 else 3)
        ask = round(mid + spread / 2, 6 if base < 10 else 3)
        return bid, ask

    async def get_account_info(self) -> dict[str, Any]:
        floating = sum(float(p.get("profit", 0.0) or 0.0) for p in self._positions)
        self._equity = self._balance + floating
        margin = sum(abs(float(p.get("volume", 0.0) or 0.0)) * 30 for p in self._positions)
        free_margin = max(0.0, self._equity - margin)
        return {
            "accountId": self._login,
            "login": self._login,
            "balance": round(self._balance, 2),
            "equity": round(self._equity, 2),
            "margin": round(margin, 2),
            "freeMargin": round(free_margin, 2),
            "profit": round(floating, 2),
            "currency": "USD",
            "leverage": 100,
            "platform": self._platform,
            "server": self._server,
        }

    async def get_positions(self) -> list[dict[str, Any]]:
        return list(self._positions)

    async def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = str(payload.get("symbol", "")).upper()
        side = str(payload.get("side", "buy")).lower()
        volume = float(payload.get("volume", payload.get("size", 0.0)) or 0.0)
        if not symbol or volume <= 0:
            return {"status": "rejected", "message": "Invalid symbol/volume"}

        bid, ask = self._tick(symbol)
        fill_price = ask if side == "buy" else bid
        order_id = str(uuid.uuid4())
        position_id = str(uuid.uuid4())

        position = {
            "position_id": position_id,
            "symbol": symbol,
            "side": side,
            "volume": volume,
            "open_price": fill_price,
            "current_price": fill_price,
            "profit": 0.0,
            "margin": round(volume * 30, 2),
            "stop_loss": payload.get("stop_loss"),
            "take_profit": payload.get("take_profit"),
            "opened_at": datetime.now(UTC).isoformat(),
            "ticket": position_id,
        }
        self._positions.append(position)
        return {
            "status": "filled",
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "fill_price": fill_price,
            "volume": volume,
            "position_id": position_id,
        }

    async def get_open_orders(self) -> list[dict[str, Any]]:
        return list(self._open_orders)

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        for order in self._open_orders:
            if str(order.get("order_id")) == str(order_id):
                return order
        return None

    async def cancel_order(self, order_id: str) -> bool:
        before = len(self._open_orders)
        self._open_orders = [o for o in self._open_orders if str(o.get("order_id")) != str(order_id)]
        return len(self._open_orders) < before

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        symbol = str(payload.get("symbol", "")).upper()
        volume = payload.get("volume")
        if not symbol:
            return {"status": "rejected", "message": "Missing symbol"}

        candidate = next((p for p in self._positions if str(p.get("symbol")) == symbol), None)
        if not candidate:
            return {"status": "rejected", "message": f"No open position for {symbol}"}

        close_volume = float(volume) if volume is not None else float(candidate.get("volume", 0.0))
        close_volume = min(close_volume, float(candidate.get("volume", 0.0)))
        bid, ask = self._tick(symbol)
        close_price = bid if str(candidate.get("side")) == "buy" else ask
        entry = float(candidate.get("open_price", close_price))
        pnl = (close_price - entry) * close_volume if str(candidate.get("side")) == "buy" else (entry - close_price) * close_volume
        self._balance += pnl

        if close_volume >= float(candidate.get("volume", 0.0)):
            self._positions.remove(candidate)
        else:
            candidate["volume"] = round(float(candidate.get("volume", 0.0)) - close_volume, 4)

        return {
            "status": "filled",
            "order_id": str(uuid.uuid4()),
            "symbol": symbol,
            "side": "sell" if str(candidate.get("side")) == "buy" else "buy",
            "fill_price": close_price,
            "volume": close_volume,
            "pnl": round(pnl, 2),
        }

    async def modify_position(self, payload: dict[str, Any]) -> bool:
        symbol = str(payload.get("symbol", "")).upper()
        position = next((p for p in self._positions if str(p.get("symbol")) == symbol), None)
        if not position:
            return False
        if "stop_loss" in payload:
            position["stop_loss"] = payload.get("stop_loss")
        if "take_profit" in payload:
            position["take_profit"] = payload.get("take_profit")
        return True

    async def get_price(self, symbol: str) -> dict[str, Any]:
        bid, ask = self._tick(symbol)
        return {
            "symbol": symbol.upper(),
            "bid": bid,
            "ask": ask,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        count: int,
        from_time: str | None = None,
        to_time: str | None = None,
    ) -> list[dict[str, Any]]:
        _ = from_time, to_time
        safe_count = max(1, min(int(count or 100), 2000))
        now = datetime.now(UTC)
        tf_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D": 1440}
        minutes = tf_map.get(str(timeframe).upper(), 5)

        bars: list[dict[str, Any]] = []
        base = self._base_price(symbol)
        for i in range(safe_count):
            ts = now - timedelta(minutes=(safe_count - i) * minutes)
            open_px = base + self._rng.uniform(-0.002, 0.002) * base / 100
            high_px = open_px + abs(self._rng.uniform(0.0002, 0.0012) * base / 100)
            low_px = open_px - abs(self._rng.uniform(0.0002, 0.0012) * base / 100)
            close_px = low_px + (high_px - low_px) * self._rng.random()
            bars.append(
                {
                    "symbol": symbol.upper(),
                    "timestamp": ts.isoformat(),
                    "open": round(open_px, 6 if base < 10 else 3),
                    "high": round(high_px, 6 if base < 10 else 3),
                    "low": round(low_px, 6 if base < 10 else 3),
                    "close": round(close_px, 6 if base < 10 else 3),
                    "volume": int(abs(self._rng.gauss(1500, 350))),
                    "timeframe": timeframe,
                }
            )
        return bars
