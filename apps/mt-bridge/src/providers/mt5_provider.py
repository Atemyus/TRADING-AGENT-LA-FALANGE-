import asyncio
import re
from datetime import UTC, datetime
from typing import Any

from src.config import BridgeSettings

from .base import BaseTerminalProvider, BridgeProviderError


class MT5TerminalProvider(BaseTerminalProvider):
    """
    Real MT5 provider using MetaTrader5 Python package on Windows nodes.

    Note:
    - MetaTrader5 package works as a process-global terminal binding.
    - For production multi-account scale use one process/node per active MT5 session
      or a process pool.
    """

    def __init__(self, *, settings: BridgeSettings):
        self._settings = settings
        self._connected = False
        self._login = ""
        self._server = ""
        self._platform = "mt5"
        self._mt5: Any = None

    @property
    def name(self) -> str:
        return "mt5"

    def _require_mt5(self):
        if self._mt5 is not None:
            return
        try:
            import MetaTrader5 as mt5  # type: ignore

            self._mt5 = mt5
        except Exception as exc:
            raise BridgeProviderError(
                "MetaTrader5 package not available. Install on Windows node: pip install MetaTrader5"
            ) from exc

    def _asdict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "_asdict"):
            try:
                return dict(value._asdict())
            except Exception:
                pass
        if isinstance(value, dict):
            return value
        return {}

    def _normalize_server_candidates(self, server_candidates: list[str] | None) -> list[str]:
        merged: list[str] = []
        seen: set[str] = set()

        def _push(raw: Any) -> None:
            candidate = str(raw or "").strip()
            if not candidate:
                return
            key = candidate.lower()
            if key in seen:
                return
            seen.add(key)
            merged.append(candidate)

        for item in server_candidates or []:
            _push(item)

        raw_settings = str(self._settings.MT_BRIDGE_MT5_SERVER_CANDIDATES or "").strip()
        if raw_settings:
            for item in re.split(r"[,\n;|]+", raw_settings):
                _push(item)

        return merged

    def _build_login_attempt_servers(
        self,
        *,
        preferred_server: str,
        allow_auto_discovery: bool,
        server_candidates: list[str],
    ) -> list[str | None]:
        attempts: list[str | None] = []
        seen: set[str] = set()

        def _append(server_value: str | None) -> None:
            normalized = str(server_value or "").strip()
            key = normalized.lower() if normalized else "__auto__"
            if key in seen:
                return
            seen.add(key)
            attempts.append(normalized or None)

        _append(preferred_server)
        if allow_auto_discovery:
            _append(None)
            for candidate in server_candidates:
                _append(candidate)

        if not attempts:
            _append(preferred_server)
        return attempts

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
        _ = data_path, workspace_id
        self._require_mt5()
        mt5 = self._mt5

        try:
            login_int = int(str(login).strip())
        except Exception as exc:
            raise BridgeProviderError("Invalid MT5 login/account number") from exc
        preferred_server = str(server or "").strip()
        allow_auto_discovery = bool(self._settings.MT_BRIDGE_MT5_AUTO_SERVER_DISCOVERY)
        if not preferred_server and not allow_auto_discovery:
            raise BridgeProviderError(
                "MT5 server/server_name is required when MT_BRIDGE_MT5_AUTO_SERVER_DISCOVERY=false"
            )

        normalized_candidates = self._normalize_server_candidates(server_candidates)
        attempt_servers = self._build_login_attempt_servers(
            preferred_server=preferred_server,
            allow_auto_discovery=allow_auto_discovery,
            server_candidates=normalized_candidates,
        )

        attempt_errors: list[str] = []
        for attempt_server in attempt_servers:
            init_kwargs: dict[str, Any] = {
                "login": login_int,
                "password": password,
            }
            if attempt_server:
                init_kwargs["server"] = attempt_server
            if terminal_path:
                init_kwargs["path"] = terminal_path

            connected = await asyncio.to_thread(mt5.initialize, **init_kwargs)
            if not connected:
                code, message = mt5.last_error()
                attempt_errors.append(f"{attempt_server or '<auto>'}: {code} {message}")
                try:
                    await asyncio.to_thread(mt5.shutdown)
                except Exception:
                    pass
                continue

            info = await asyncio.to_thread(mt5.account_info)
            if info is None:
                code, message = mt5.last_error()
                attempt_errors.append(f"{attempt_server or '<auto>'}: {code} {message}")
                await asyncio.to_thread(mt5.shutdown)
                continue

            payload = self._asdict(info)
            resolved_login = str(payload.get("login") or login_int)
            resolved_server = str(
                payload.get("server")
                or payload.get("server_name")
                or attempt_server
                or preferred_server
                or ""
            ).strip()
            self._login = resolved_login
            self._server = resolved_server
            self._platform = platform
            self._connected = True
            return

        if attempt_errors:
            details = " | ".join(attempt_errors[:6])
            raise BridgeProviderError(f"MT5 initialize/login failed. Attempts: {details}")
        raise BridgeProviderError("MT5 initialize/login failed: unknown error")

    async def disconnect(self) -> None:
        if self._mt5 and self._connected:
            await asyncio.to_thread(self._mt5.shutdown)
        self._connected = False

    async def get_account_info(self) -> dict[str, Any]:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        info = await asyncio.to_thread(self._mt5.account_info)
        payload = self._asdict(info)
        if not payload:
            raise BridgeProviderError("MT5 account_info returned empty payload")
        resolved_server = str(payload.get("server") or payload.get("server_name") or self._server).strip()
        if resolved_server:
            self._server = resolved_server
        balance = float(payload.get("balance", 0.0) or 0.0)
        equity = float(payload.get("equity", balance) or balance)
        margin = float(payload.get("margin", 0.0) or 0.0)
        return {
            "accountId": str(payload.get("login") or self._login),
            "login": str(payload.get("login") or self._login),
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "freeMargin": float(payload.get("margin_free", payload.get("freeMargin", 0.0)) or 0.0),
            "profit": float(payload.get("profit", 0.0) or 0.0),
            "currency": str(payload.get("currency", "USD")),
            "leverage": int(payload.get("leverage", 1) or 1),
            "platform": self._platform,
            "server": self._server,
        }

    async def _ensure_symbol(self, symbol: str) -> str:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        normalized = symbol.upper().replace("/", "").replace("_", "")
        selected = await asyncio.to_thread(mt5.symbol_select, normalized, True)
        if not selected:
            # Best effort fallback: check original variant
            original = symbol.upper().replace("_", "/")
            selected = await asyncio.to_thread(mt5.symbol_select, original, True)
            if selected:
                return original
            raise BridgeProviderError(f"MT5 symbol not available/selectable: {symbol}")
        return normalized

    async def get_positions(self) -> list[dict[str, Any]]:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        rows = await asyncio.to_thread(mt5.positions_get)
        if rows is None:
            return []
        result: list[dict[str, Any]] = []
        for row in rows:
            p = self._asdict(row)
            side = "buy" if int(p.get("type", 0) or 0) == int(getattr(mt5, "POSITION_TYPE_BUY", 0)) else "sell"
            result.append(
                {
                    "position_id": str(p.get("ticket", "")),
                    "ticket": str(p.get("ticket", "")),
                    "symbol": str(p.get("symbol", "")),
                    "side": side,
                    "volume": float(p.get("volume", 0.0) or 0.0),
                    "open_price": float(p.get("price_open", 0.0) or 0.0),
                    "current_price": float(p.get("price_current", 0.0) or 0.0),
                    "profit": float(p.get("profit", 0.0) or 0.0),
                    "margin": float(p.get("margin", 0.0) or 0.0),
                    "stop_loss": float(p.get("sl", 0.0) or 0.0) or None,
                    "take_profit": float(p.get("tp", 0.0) or 0.0) or None,
                    "opened_at": datetime.fromtimestamp(int(p.get("time", 0) or 0), tz=UTC).isoformat()
                    if p.get("time")
                    else datetime.now(UTC).isoformat(),
                }
            )
        return result

    def _time_in_force_code(self, tif: str | None) -> int:
        mt5 = self._mt5
        mapping = {
            "gtc": getattr(mt5, "ORDER_TIME_GTC", 0),
            "day": getattr(mt5, "ORDER_TIME_DAY", 0),
            "ioc": getattr(mt5, "ORDER_TIME_GTC", 0),
            "fok": getattr(mt5, "ORDER_TIME_GTC", 0),
        }
        return int(mapping.get((tif or "gtc").lower(), getattr(mt5, "ORDER_TIME_GTC", 0)))

    async def place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5

        symbol = await self._ensure_symbol(str(payload.get("symbol", "")))
        side = str(payload.get("side", "buy")).lower()
        order_type = str(payload.get("order_type", "market")).lower()
        volume = float(payload.get("volume", 0.0) or 0.0)
        if volume <= 0:
            return {"status": "rejected", "message": "Volume must be > 0"}

        tick = await asyncio.to_thread(mt5.symbol_info_tick, symbol)
        tick_data = self._asdict(tick)
        bid = float(tick_data.get("bid", 0.0) or 0.0)
        ask = float(tick_data.get("ask", 0.0) or 0.0)
        if bid <= 0 or ask <= 0:
            return {"status": "rejected", "message": f"Price unavailable for {symbol}"}

        if order_type == "market":
            action = int(getattr(mt5, "TRADE_ACTION_DEAL", 1))
            type_code = int(getattr(mt5, "ORDER_TYPE_BUY", 0) if side == "buy" else getattr(mt5, "ORDER_TYPE_SELL", 1))
            price = ask if side == "buy" else bid
        elif order_type == "limit":
            action = int(getattr(mt5, "TRADE_ACTION_PENDING", 5))
            type_code = int(
                getattr(mt5, "ORDER_TYPE_BUY_LIMIT", 2)
                if side == "buy"
                else getattr(mt5, "ORDER_TYPE_SELL_LIMIT", 3)
            )
            price = float(payload.get("price", 0.0) or 0.0)
            if price <= 0:
                return {"status": "rejected", "message": "Limit order requires price"}
        elif order_type == "stop":
            action = int(getattr(mt5, "TRADE_ACTION_PENDING", 5))
            type_code = int(
                getattr(mt5, "ORDER_TYPE_BUY_STOP", 4)
                if side == "buy"
                else getattr(mt5, "ORDER_TYPE_SELL_STOP", 5)
            )
            price = float(payload.get("stop_price", payload.get("price", 0.0)) or 0.0)
            if price <= 0:
                return {"status": "rejected", "message": "Stop order requires stop_price/price"}
        else:
            return {"status": "rejected", "message": f"Unsupported order_type: {order_type}"}

        request = {
            "action": action,
            "symbol": symbol,
            "volume": volume,
            "type": type_code,
            "price": price,
            "deviation": 20,
            "type_time": self._time_in_force_code(str(payload.get("time_in_force", "gtc"))),
            "type_filling": int(getattr(mt5, "ORDER_FILLING_IOC", 1)),
            "comment": "prometheus-mt-bridge",
        }
        if payload.get("stop_loss") is not None:
            request["sl"] = float(payload.get("stop_loss"))
        if payload.get("take_profit") is not None:
            request["tp"] = float(payload.get("take_profit"))

        sent = await asyncio.to_thread(mt5.order_send, request)
        data = self._asdict(sent)
        retcode = int(data.get("retcode", -1) or -1)
        done = {
            int(getattr(mt5, "TRADE_RETCODE_DONE", -1)),
            int(getattr(mt5, "TRADE_RETCODE_PLACED", -1)),
            int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", -1)),
        }
        status = "filled" if retcode in done and order_type == "market" else ("pending" if retcode in done else "rejected")
        return {
            "status": status,
            "order_id": str(data.get("order", data.get("deal", ""))),
            "symbol": symbol,
            "side": side,
            "fill_price": price if status == "filled" else None,
            "volume": volume,
            "retcode": retcode,
            "message": str(data.get("comment", data.get("request_id", ""))),
        }

    async def get_open_orders(self) -> list[dict[str, Any]]:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        rows = await asyncio.to_thread(mt5.orders_get)
        if rows is None:
            return []
        result: list[dict[str, Any]] = []
        for row in rows:
            o = self._asdict(row)
            result.append(
                {
                    "order_id": str(o.get("ticket", "")),
                    "ticket": str(o.get("ticket", "")),
                    "symbol": str(o.get("symbol", "")),
                    "side": "buy" if int(o.get("type", 0) or 0) % 2 == 0 else "sell",
                    "order_type": "limit",
                    "status": "pending",
                    "volume": float(o.get("volume_current", o.get("volume_initial", 0.0)) or 0.0),
                    "price": float(o.get("price_open", 0.0) or 0.0),
                    "time": datetime.fromtimestamp(int(o.get("time_setup", 0) or 0), tz=UTC).isoformat()
                    if o.get("time_setup")
                    else datetime.now(UTC).isoformat(),
                }
            )
        return result

    async def get_order(self, order_id: str) -> dict[str, Any] | None:
        for order in await self.get_open_orders():
            if str(order.get("order_id")) == str(order_id):
                return order
        return None

    async def cancel_order(self, order_id: str) -> bool:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        request = {
            "action": int(getattr(mt5, "TRADE_ACTION_REMOVE", 8)),
            "order": int(order_id),
            "comment": "prometheus-mt-bridge-cancel",
        }
        sent = await asyncio.to_thread(mt5.order_send, request)
        data = self._asdict(sent)
        retcode = int(data.get("retcode", -1) or -1)
        return retcode in {
            int(getattr(mt5, "TRADE_RETCODE_DONE", -1)),
            int(getattr(mt5, "TRADE_RETCODE_PLACED", -1)),
        }

    async def close_position(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        symbol = str(payload.get("symbol", "")).upper()
        if not symbol:
            return {"status": "rejected", "message": "Missing symbol"}
        rows = await asyncio.to_thread(mt5.positions_get, symbol=symbol)
        if not rows:
            return {"status": "rejected", "message": f"No open position for {symbol}"}
        pos = self._asdict(rows[0])
        position_ticket = int(pos.get("ticket", 0) or 0)
        position_volume = float(pos.get("volume", 0.0) or 0.0)
        close_volume = float(payload.get("volume", position_volume) or position_volume)
        close_volume = min(close_volume, position_volume)
        pos_type = int(pos.get("type", 0) or 0)

        selected_symbol = await self._ensure_symbol(symbol)
        tick = await asyncio.to_thread(mt5.symbol_info_tick, selected_symbol)
        tick_data = self._asdict(tick)
        bid = float(tick_data.get("bid", 0.0) or 0.0)
        ask = float(tick_data.get("ask", 0.0) or 0.0)
        side_close = int(getattr(mt5, "ORDER_TYPE_SELL", 1)) if pos_type == int(getattr(mt5, "POSITION_TYPE_BUY", 0)) else int(getattr(mt5, "ORDER_TYPE_BUY", 0))
        price = bid if side_close == int(getattr(mt5, "ORDER_TYPE_SELL", 1)) else ask

        request = {
            "action": int(getattr(mt5, "TRADE_ACTION_DEAL", 1)),
            "symbol": selected_symbol,
            "volume": close_volume,
            "type": side_close,
            "position": position_ticket,
            "price": price,
            "deviation": 20,
            "type_time": int(getattr(mt5, "ORDER_TIME_GTC", 0)),
            "type_filling": int(getattr(mt5, "ORDER_FILLING_IOC", 1)),
            "comment": "prometheus-mt-bridge-close",
        }
        sent = await asyncio.to_thread(mt5.order_send, request)
        data = self._asdict(sent)
        retcode = int(data.get("retcode", -1) or -1)
        ok = retcode in {
            int(getattr(mt5, "TRADE_RETCODE_DONE", -1)),
            int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", -1)),
        }
        return {
            "status": "filled" if ok else "rejected",
            "order_id": str(data.get("order", data.get("deal", ""))),
            "symbol": selected_symbol,
            "side": "sell" if side_close == int(getattr(mt5, "ORDER_TYPE_SELL", 1)) else "buy",
            "fill_price": price if ok else None,
            "volume": close_volume,
            "retcode": retcode,
            "message": str(data.get("comment", "")),
        }

    async def modify_position(self, payload: dict[str, Any]) -> bool:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        symbol = str(payload.get("symbol", "")).upper()
        if not symbol:
            return False
        rows = await asyncio.to_thread(mt5.positions_get, symbol=symbol)
        if not rows:
            return False
        pos = self._asdict(rows[0])
        request = {
            "action": int(getattr(mt5, "TRADE_ACTION_SLTP", 6)),
            "position": int(pos.get("ticket", 0) or 0),
            "symbol": symbol,
        }
        if payload.get("stop_loss") is not None:
            request["sl"] = float(payload.get("stop_loss"))
        if payload.get("take_profit") is not None:
            request["tp"] = float(payload.get("take_profit"))
        sent = await asyncio.to_thread(mt5.order_send, request)
        data = self._asdict(sent)
        retcode = int(data.get("retcode", -1) or -1)
        return retcode in {
            int(getattr(mt5, "TRADE_RETCODE_DONE", -1)),
            int(getattr(mt5, "TRADE_RETCODE_PLACED", -1)),
        }

    async def get_price(self, symbol: str) -> dict[str, Any]:
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        selected_symbol = await self._ensure_symbol(symbol)
        tick = await asyncio.to_thread(mt5.symbol_info_tick, selected_symbol)
        data = self._asdict(tick)
        bid = float(data.get("bid", 0.0) or 0.0)
        ask = float(data.get("ask", 0.0) or 0.0)
        if bid <= 0 or ask <= 0:
            raise BridgeProviderError(f"No valid tick for {selected_symbol}")
        return {
            "symbol": selected_symbol,
            "bid": bid,
            "ask": ask,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _map_timeframe(self, tf: str) -> int:
        mt5 = self._mt5
        mapping = {
            "M1": int(getattr(mt5, "TIMEFRAME_M1", 1)),
            "M5": int(getattr(mt5, "TIMEFRAME_M5", 5)),
            "M15": int(getattr(mt5, "TIMEFRAME_M15", 15)),
            "M30": int(getattr(mt5, "TIMEFRAME_M30", 30)),
            "H1": int(getattr(mt5, "TIMEFRAME_H1", 60)),
            "H4": int(getattr(mt5, "TIMEFRAME_H4", 240)),
            "D": int(getattr(mt5, "TIMEFRAME_D1", 1440)),
        }
        return mapping.get((tf or "M5").upper(), int(getattr(mt5, "TIMEFRAME_M5", 5)))

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
        if not self._connected or not self._mt5:
            raise BridgeProviderError("MT5 provider not connected")
        mt5 = self._mt5
        selected_symbol = await self._ensure_symbol(symbol)
        tf = self._map_timeframe(timeframe)
        safe_count = max(1, min(int(count or 100), 2000))
        rates = await asyncio.to_thread(mt5.copy_rates_from_pos, selected_symbol, tf, 0, safe_count)
        if rates is None:
            return []

        result: list[dict[str, Any]] = []
        for rate in rates:
            row = self._asdict(rate)
            ts_value = int(row.get("time", 0) or 0)
            result.append(
                {
                    "symbol": selected_symbol,
                    "timestamp": datetime.fromtimestamp(ts_value, tz=UTC).isoformat() if ts_value else datetime.now(UTC).isoformat(),
                    "open": float(row.get("open", 0.0) or 0.0),
                    "high": float(row.get("high", 0.0) or 0.0),
                    "low": float(row.get("low", 0.0) or 0.0),
                    "close": float(row.get("close", 0.0) or 0.0),
                    "volume": float(row.get("tick_volume", row.get("real_volume", 0.0)) or 0.0),
                    "timeframe": timeframe,
                }
            )
        return result
