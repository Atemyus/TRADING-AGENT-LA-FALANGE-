"""
MetaTrader Broker Implementation

Connects to MetaTrader 4/5 via MetaApi.cloud REST API.
Supports any MT4/MT5 broker (IC Markets, Pepperstone, XM, etc.)

Setup:
1. Create account at https://metaapi.cloud
2. Add your MT4/MT5 account to MetaApi
3. Get your access token and account ID
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from src.core.config import settings
from src.engines.trading.base_broker import (
    AccountInfo,
    BaseBroker,
    Instrument,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Tick,
)


class MetaTraderBroker(BaseBroker):
    """
    MetaTrader 4/5 broker via MetaApi.cloud

    MetaApi provides a REST API to interact with MT4/MT5 accounts
    without needing to run Expert Advisors or connect via DLL.

    Supported brokers: Any MT4/MT5 broker
    - IC Markets
    - Pepperstone
    - XM
    - FXCM
    - Admiral Markets
    - And many more...
    """

    # Provisioning API is global, Client API depends on account region
    PROVISIONING_URL = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"

    # Common symbol variations across brokers
    SYMBOL_ALIASES = {
        # ============ FOREX MAJORS ============
        'EUR_USD': ['EURUSD', 'EURUSDm', 'EURUSD.', 'EURUSD-ECN', 'EURUSDpro', 'EURUSD.ecn'],
        'GBP_USD': ['GBPUSD', 'GBPUSDm', 'GBPUSD.', 'GBPUSD-ECN', 'GBPUSDpro'],
        'USD_JPY': ['USDJPY', 'USDJPYm', 'USDJPY.', 'USDJPY-ECN', 'USDJPYpro'],
        'USD_CHF': ['USDCHF', 'USDCHFm', 'USDCHF.', 'USDCHF-ECN', 'USDCHFpro'],
        'AUD_USD': ['AUDUSD', 'AUDUSDm', 'AUDUSD.', 'AUDUSD-ECN', 'AUDUSDpro'],
        'USD_CAD': ['USDCAD', 'USDCADm', 'USDCAD.', 'USDCAD-ECN', 'USDCADpro'],
        'NZD_USD': ['NZDUSD', 'NZDUSDm', 'NZDUSD.', 'NZDUSD-ECN', 'NZDUSDpro'],

        # ============ FOREX CROSS PAIRS ============
        'EUR_GBP': ['EURGBP', 'EURGBPm', 'EURGBP.', 'EURGBP-ECN'],
        'EUR_JPY': ['EURJPY', 'EURJPYm', 'EURJPY.', 'EURJPY-ECN'],
        'GBP_JPY': ['GBPJPY', 'GBPJPYm', 'GBPJPY.', 'GBPJPY-ECN'],
        'EUR_CHF': ['EURCHF', 'EURCHFm', 'EURCHF.', 'EURCHF-ECN'],
        'EUR_AUD': ['EURAUD', 'EURAUDm', 'EURAUD.', 'EURAUD-ECN'],
        'EUR_CAD': ['EURCAD', 'EURCADm', 'EURCAD.', 'EURCAD-ECN'],
        'GBP_CHF': ['GBPCHF', 'GBPCHFm', 'GBPCHF.', 'GBPCHF-ECN'],
        'GBP_AUD': ['GBPAUD', 'GBPAUDm', 'GBPAUD.', 'GBPAUD-ECN'],
        'AUD_JPY': ['AUDJPY', 'AUDJPYm', 'AUDJPY.', 'AUDJPY-ECN'],
        'AUD_CAD': ['AUDCAD', 'AUDCADm', 'AUDCAD.', 'AUDCAD-ECN'],
        'AUD_NZD': ['AUDNZD', 'AUDNZDm', 'AUDNZD.', 'AUDNZD-ECN'],
        'CAD_JPY': ['CADJPY', 'CADJPYm', 'CADJPY.', 'CADJPY-ECN'],
        'NZD_JPY': ['NZDJPY', 'NZDJPYm', 'NZDJPY.', 'NZDJPY-ECN'],
        'CHF_JPY': ['CHFJPY', 'CHFJPYm', 'CHFJPY.', 'CHFJPY-ECN'],

        # ============ FOREX EXOTIC PAIRS ============
        'EUR_TRY': ['EURTRY', 'EURTRYm', 'EURTRY.', 'EURTRY-ECN'],
        'USD_TRY': ['USDTRY', 'USDTRYm', 'USDTRY.', 'USDTRY-ECN'],
        'USD_MXN': ['USDMXN', 'USDMXNm', 'USDMXN.', 'USDMXN-ECN'],
        'USD_ZAR': ['USDZAR', 'USDZARm', 'USDZAR.', 'USDZAR-ECN'],
        'USD_SGD': ['USDSGD', 'USDSGDm', 'USDSGD.', 'USDSGD-ECN'],
        'USD_HKD': ['USDHKD', 'USDHKDm', 'USDHKD.', 'USDHKD-ECN'],
        'USD_NOK': ['USDNOK', 'USDNOKm', 'USDNOK.', 'USDNOK-ECN'],
        'USD_SEK': ['USDSEK', 'USDSEKm', 'USDSEK.', 'USDSEK-ECN'],
        'USD_DKK': ['USDDKK', 'USDDKKm', 'USDDKK.', 'USDDKK-ECN'],
        'USD_PLN': ['USDPLN', 'USDPLNm', 'USDPLN.', 'USDPLN-ECN'],

        # ============ METALS ============
        'XAU_USD': ['XAUUSD', 'XAUUSDm', 'GOLD', 'GOLDm', 'GOLD.', 'XAUUSD.', 'XAUUSD-ECN'],
        'XAG_USD': ['XAGUSD', 'XAGUSDm', 'SILVER', 'SILVERm', 'SILVER.', 'XAGUSD.'],
        'XPT_USD': ['XPTUSD', 'XPTUSDm', 'PLATINUM', 'XPTUSD.', 'PLATINUMm'],
        'XPD_USD': ['XPDUSD', 'XPDUSDm', 'PALLADIUM', 'XPDUSD.', 'PALLADIUMm'],
        'XCU_USD': ['XCUUSD', 'COPPER', 'COPPERm', 'COPPER.', 'HG', 'HGm'],

        # ============ ENERGY / OIL ============
        'WTI_USD': ['USOUSD', 'USOUSDm', 'WTIUSD', 'WTI', 'USOIL', 'USOILm', 'XTIUSD', 'CL', 'CLm'],
        'BRENT_USD': ['UKOUSD', 'UKOUSDm', 'BRENT', 'BRENTm', 'UKOIL', 'UKOILm', 'XBRUSD'],
        'NATGAS_USD': ['NATGAS', 'NATGASm', 'NATGAS.', 'NGAS', 'NGASm', 'NG', 'NGm', 'XNGUSD'],

        # ============ AGRICULTURAL COMMODITIES ============
        'WHEAT_USD': ['WHEAT', 'WHEATm', 'WHEAT.', 'ZW', 'ZWm'],
        'CORN_USD': ['CORN', 'CORNm', 'CORN.', 'ZC', 'ZCm'],
        'SOYBEAN_USD': ['SOYBEAN', 'SOYBEANm', 'SOYBEAN.', 'SOYA', 'SOYAm', 'ZS', 'ZSm'],
        'COFFEE_USD': ['COFFEE', 'COFFEEm', 'COFFEE.', 'KC', 'KCm'],
        'SUGAR_USD': ['SUGAR', 'SUGARm', 'SUGAR.', 'SB', 'SBm'],
        'COCOA_USD': ['COCOA', 'COCOAm', 'COCOA.', 'CC', 'CCm'],
        'COTTON_USD': ['COTTON', 'COTTONm', 'COTTON.', 'CT', 'CTm'],

        # ============ US INDICES ============
        'US30': ['US30', 'US30m', 'US30.', 'DJ30', 'DJI30', 'DOW30', 'DJIA'],
        'US500': ['US500', 'US500m', 'US500.', 'SPX500', 'SP500', 'SPX', 'SPXm'],
        'NAS100': ['NAS100', 'NAS100m', 'NAS100.', 'USTEC', 'NDX100', 'NASDAQ', 'NDX', 'NDXm'],
        'US2000': ['US2000', 'US2000m', 'US2000.', 'RUSSELL', 'RUT', 'RUTm', 'RTY'],

        # ============ EUROPEAN INDICES ============
        'DE40': ['DE40', 'DE40m', 'DE40.', 'GER40', 'GER30', 'DAX40', 'DAX', 'DAXm'],
        'UK100': ['UK100', 'UK100m', 'UK100.', 'FTSE100', 'FTSE', 'FTSEm'],
        'FR40': ['FR40', 'FR40m', 'FR40.', 'FRA40', 'CAC40', 'CAC', 'CACm'],
        'EU50': ['EU50', 'EU50m', 'EU50.', 'EUSTX50', 'STOXX50', 'SX5E'],
        'ES35': ['ES35', 'ES35m', 'ES35.', 'ESP35', 'IBEX35', 'IBEX', 'IBEXm'],
        'IT40': ['IT40', 'IT40m', 'IT40.', 'ITA40', 'FTMIB', 'MIB', 'MIBm'],

        # ============ ASIAN INDICES ============
        'JP225': ['JP225', 'JP225m', 'JP225.', 'JPN225', 'NIKKEI', 'NI225', 'NIKKEIm'],
        'HK50': ['HK50', 'HK50m', 'HK50.', 'HSI', 'HSIm', 'HANGSENG'],
        'AU200': ['AU200', 'AU200m', 'AU200.', 'AUS200', 'ASX200', 'ASX', 'ASXm'],
        'CN50': ['CN50', 'CN50m', 'CN50.', 'CHINA50', 'CHINAA50', 'A50', 'A50m'],

        # ============ OTHER INDICES ============
        'VIX': ['VIX', 'VIXm', 'VIX.', 'VOLATILITY', 'UVXY'],

        # ============ INDEX FUTURES ============
        'ES1': ['ES', 'ESm', 'ES1', 'ES1!', 'SP500FUT'],
        'NQ1': ['NQ', 'NQm', 'NQ1', 'NQ1!', 'NASDAQFUT'],
        'YM1': ['YM', 'YMm', 'YM1', 'YM1!', 'DOWFUT'],
        'RTY1': ['RTY', 'RTYm', 'RTY1', 'RTY1!', 'RUSSELLFUT'],

        # ============ METAL FUTURES ============
        'GC1': ['GC', 'GCm', 'GC1', 'GC1!', 'GOLDFUT'],
        'SI1': ['SI', 'SIm', 'SI1', 'SI1!', 'SILVERFUT'],

        # ============ ENERGY FUTURES ============
        'CL1': ['CL', 'CLm', 'CL1', 'CL1!', 'CRUDEOIL', 'OILFUT'],
        'NG1': ['NG', 'NGm', 'NG1', 'NG1!', 'NATGASFUT'],

        # ============ CURRENCY FUTURES ============
        '6E1': ['6E', '6Em', '6E1', '6E1!', 'EUROFUT'],
        '6B1': ['6B', '6Bm', '6B1', '6B1!', 'GBPFUT'],
        '6J1': ['6J', '6Jm', '6J1', '6J1!', 'JPYFUT'],

        # ============ BOND FUTURES ============
        'ZB1': ['ZB', 'ZBm', 'ZB1', 'ZB1!', 'TBOND'],
        'ZN1': ['ZN', 'ZNm', 'ZN1', 'ZN1!', 'TNOTE'],
    }

    def __init__(
        self,
        access_token: Optional[str] = None,
        account_id: Optional[str] = None,
    ):
        """
        Initialize MetaTrader broker.

        Args:
            access_token: MetaApi access token
            account_id: MetaApi account ID (not MT4/MT5 login)
        """
        super().__init__()
        self.access_token = access_token or getattr(settings, 'METAAPI_ACCESS_TOKEN', None)
        self.account_id = account_id or getattr(settings, 'METAAPI_ACCOUNT_ID', None)
        self._client: Optional[httpx.AsyncClient] = None
        self._account_info: Optional[Dict[str, Any]] = None
        self._connected = False
        self._symbol_map: Dict[str, str] = {}  # Maps our symbols to broker symbols
        self._broker_symbols: List[str] = []  # List of available broker symbols
        self._client_api_url: Optional[str] = None  # Set during connect based on region

    async def _ensure_client(self) -> None:
        """Ensure HTTP client is initialized."""
        if self._client is None:
            # Disable SSL verification for cloud environments (Railway, etc.)
            # MetaApi is a trusted external service
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "auth-token": self.access_token,
                    "Content-Type": "application/json",
                },
                verify=False,
            )

    async def _request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make API request."""
        await self._ensure_client()

        # Use provided base_url, or the client API URL (set during connect), or fallback
        effective_base_url = base_url or self._client_api_url or "https://mt-client-api-v1.vint-hill.agiliumtrade.ai"
        url = f"{effective_base_url}{endpoint}"
        response = await self._client.request(method, url, **kwargs)

        if response.status_code >= 400:
            error_text = response.text
            raise Exception(f"MetaApi error ({response.status_code}): {error_text}")

        if response.status_code == 204:
            return {}

        return response.json()

    def _resolve_symbol(self, symbol: str) -> str:
        """
        Resolve our internal symbol to broker's symbol format.

        Examples:
            EUR_USD -> EURUSD (or EURUSDm, EURUSD., etc. depending on broker)
            XAU_USD -> GOLD (or XAUUSD, GOLDm, etc.)
        """
        # If already mapped, return the mapped symbol
        if symbol in self._symbol_map:
            return self._symbol_map[symbol]

        # Try to find a match in available broker symbols
        if self._broker_symbols:
            # Normalize our symbol (remove underscore)
            base_symbol = symbol.replace('_', '')

            # First, check exact match (case insensitive)
            for broker_sym in self._broker_symbols:
                if broker_sym.upper() == base_symbol.upper():
                    self._symbol_map[symbol] = broker_sym
                    return broker_sym

            # Check known aliases
            aliases = self.SYMBOL_ALIASES.get(symbol, [])
            for alias in aliases:
                for broker_sym in self._broker_symbols:
                    if broker_sym.upper() == alias.upper():
                        self._symbol_map[symbol] = broker_sym
                        return broker_sym

            # Fuzzy match - symbol starts with base symbol
            for broker_sym in self._broker_symbols:
                if broker_sym.upper().startswith(base_symbol.upper()):
                    self._symbol_map[symbol] = broker_sym
                    return broker_sym

        # Fallback: return without underscore
        return symbol.replace('_', '')

    async def _build_symbol_map(self) -> None:
        """Build symbol mapping from broker's available symbols."""
        try:
            symbols = await self.get_symbols()
            self._broker_symbols = [s.get('symbol', s) if isinstance(s, dict) else s for s in symbols]

            # Pre-map common symbols
            for our_symbol in self.SYMBOL_ALIASES.keys():
                self._resolve_symbol(our_symbol)

        except Exception as e:
            print(f"Warning: Could not build symbol map: {e}")

    async def connect(self) -> None:
        """Connect to MetaTrader account via MetaApi."""
        if not self.access_token:
            raise ValueError("MetaApi access token not configured")
        if not self.account_id:
            raise ValueError("MetaApi account ID not configured")

        await self._ensure_client()

        # Get account info to verify connection
        try:
            # First, get account details including region
            account = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}",
                base_url=self.PROVISIONING_URL,
            )

            # Get the region from account info to construct correct client API URL
            region = account.get("region", "vint-hill")
            self._client_api_url = f"https://mt-client-api-v1.{region}.agiliumtrade.ai"

            if account.get("state") != "DEPLOYED":
                # Deploy the account if not deployed
                await self._request(
                    "POST",
                    f"/users/current/accounts/{self.account_id}/deploy",
                    base_url=self.PROVISIONING_URL,
                )
                # Wait for deployment
                await asyncio.sleep(5)

                # Re-fetch account info after deployment
                account = await self._request(
                    "GET",
                    f"/users/current/accounts/{self.account_id}",
                    base_url=self.PROVISIONING_URL,
                )

            # Get account information from client API
            self._account_info = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/account-information",
                base_url=self._client_api_url,
            )

            self._connected = True

            # Build symbol mapping after connection
            await self._build_symbol_map()

        except Exception as e:
            raise Exception(f"Failed to connect to MetaTrader: {e}")

    async def disconnect(self) -> None:
        """Disconnect from MetaApi."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected."""
        return self._connected

    @property
    def name(self) -> str:
        """Broker name identifier."""
        return "metatrader"

    @property
    def supported_markets(self) -> List[str]:
        """List of supported market types."""
        return ["forex", "indices", "commodities", "metals", "futures"]

    async def get_account_info(self) -> AccountInfo:
        """Get account information."""
        if not self._connected:
            await self.connect()

        info = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/account-information",
        )

        return AccountInfo(
            account_id=self.account_id,
            balance=Decimal(str(info.get("balance", 0))),
            equity=Decimal(str(info.get("equity", 0))),
            margin_used=Decimal(str(info.get("margin", 0))),
            margin_available=Decimal(str(info.get("freeMargin", 0))),
            unrealized_pnl=Decimal(str(info.get("equity", 0) - info.get("balance", 0))),
            realized_pnl_today=Decimal("0"),  # MetaApi doesn't provide daily P&L directly
            currency=info.get("currency", "USD"),
            leverage=info.get("leverage", 1),
        )

    async def get_positions(self) -> List[Position]:
        """Get all open positions."""
        if not self._connected:
            await self.connect()

        positions_data = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/positions",
        )

        positions = []
        for pos in positions_data:
            positions.append(Position(
                position_id=str(pos.get("id")),
                symbol=pos.get("symbol", ""),
                side=PositionSide.LONG if pos.get("type") == "POSITION_TYPE_BUY" else PositionSide.SHORT,
                size=Decimal(str(abs(pos.get("volume", 0)))),
                entry_price=Decimal(str(pos.get("openPrice", 0))),
                current_price=Decimal(str(pos.get("currentPrice", 0))),
                unrealized_pnl=Decimal(str(pos.get("profit", 0))),
                margin_used=Decimal(str(pos.get("margin", 0))),
                stop_loss=Decimal(str(pos.get("stopLoss", 0))) if pos.get("stopLoss") else None,
                take_profit=Decimal(str(pos.get("takeProfit", 0))) if pos.get("takeProfit") else None,
                opened_at=datetime.fromisoformat(pos.get("time", datetime.now().isoformat()).replace("Z", "+00:00")),
            ))

        return positions

    async def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol."""
        broker_symbol = self._resolve_symbol(symbol)
        positions = await self.get_positions()
        for pos in positions:
            # Compare with both original and broker symbol format
            if pos.symbol == broker_symbol or pos.symbol.upper() == broker_symbol.upper():
                return pos
        return None

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a trading order."""
        if not self._connected:
            await self.connect()

        # Map order type
        action_type = "ORDER_TYPE_BUY" if order.side == OrderSide.BUY else "ORDER_TYPE_SELL"

        if order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                action_type = "ORDER_TYPE_BUY_LIMIT"
            else:
                action_type = "ORDER_TYPE_SELL_LIMIT"
        elif order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY:
                action_type = "ORDER_TYPE_BUY_STOP"
            else:
                action_type = "ORDER_TYPE_SELL_STOP"

        # Build order payload - resolve symbol to broker format
        broker_symbol = self._resolve_symbol(order.symbol)
        payload = {
            "symbol": broker_symbol,
            "actionType": action_type,
            "volume": float(order.size),
        }

        # Add price for limit/stop orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP] and order.price:
            payload["openPrice"] = float(order.price)

        # Add SL/TP
        if order.stop_loss:
            payload["stopLoss"] = float(order.stop_loss)
        if order.take_profit:
            payload["takeProfit"] = float(order.take_profit)

        try:
            result = await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json=payload,
            )

            return OrderResult(
                order_id=str(result.get("orderId", result.get("positionId", ""))),
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.FILLED if result.get("positionId") else OrderStatus.PENDING,
                size=order.size,
                filled_size=order.size if result.get("positionId") else Decimal("0"),
                price=order.price,
                average_fill_price=Decimal(str(result.get("openPrice", 0))) if result.get("openPrice") else None,
                commission=Decimal(str(result.get("commission", 0))),
            )

        except Exception as e:
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=str(e),
            )

    async def close_position(
        self,
        symbol: str,
        size: Optional[Decimal] = None
    ) -> OrderResult:
        """Close a position."""
        if not self._connected:
            await self.connect()

        # Get the position first
        position = await self.get_position(symbol)
        if not position:
            return OrderResult(
                order_id="",
                symbol=symbol,
                side=OrderSide.SELL,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=Decimal("0"),
                filled_size=Decimal("0"),
                error_message="Position not found",
            )

        close_size = size or position.size

        # Close by placing opposite order
        payload = {
            "actionType": "POSITION_CLOSE_ID",
            "positionId": position.position_id,
        }

        if size and size < position.size:
            # Partial close
            payload["volume"] = float(size)

        try:
            result = await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json=payload,
            )

            return OrderResult(
                order_id=str(result.get("orderId", "")),
                symbol=symbol,
                side=OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.FILLED,
                size=close_size,
                filled_size=close_size,
                average_fill_price=Decimal(str(result.get("closePrice", 0))) if result.get("closePrice") else None,
            )

        except Exception as e:
            return OrderResult(
                order_id="",
                symbol=symbol,
                side=OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY,
                order_type=OrderType.MARKET,
                status=OrderStatus.REJECTED,
                size=close_size,
                filled_size=Decimal("0"),
                error_message=str(e),
            )

    async def modify_position(
        self,
        symbol: str,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
    ) -> bool:
        """Modify position SL/TP."""
        if not self._connected:
            await self.connect()

        position = await self.get_position(symbol)
        if not position:
            return False

        payload = {
            "actionType": "POSITION_MODIFY",
            "positionId": position.position_id,
        }

        if stop_loss is not None:
            payload["stopLoss"] = float(stop_loss)
        if take_profit is not None:
            payload["takeProfit"] = float(take_profit)

        try:
            await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json=payload,
            )
            return True
        except Exception:
            return False

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        if not self._connected:
            await self.connect()

        try:
            await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/trade",
                json={
                    "actionType": "ORDER_CANCEL",
                    "orderId": order_id,
                },
            )
            return True
        except Exception:
            return False

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[OrderResult]:
        """Get all open/pending orders."""
        if not self._connected:
            await self.connect()

        orders_data = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/orders",
        )

        orders = []
        for order in orders_data:
            order_symbol = order.get("symbol", "")

            # Filter by symbol if specified
            if symbol:
                broker_symbol = self._resolve_symbol(symbol)
                if order_symbol.upper() != broker_symbol.upper():
                    continue

            side = OrderSide.BUY if "BUY" in order.get("type", "") else OrderSide.SELL

            order_type = OrderType.MARKET
            if "LIMIT" in order.get("type", ""):
                order_type = OrderType.LIMIT
            elif "STOP" in order.get("type", ""):
                order_type = OrderType.STOP

            orders.append(OrderResult(
                order_id=str(order.get("id")),
                client_order_id=order.get("clientId"),
                symbol=order_symbol,
                side=side,
                order_type=order_type,
                status=OrderStatus.PENDING,
                size=Decimal(str(order.get("volume", 0))),
                filled_size=Decimal("0"),
                price=Decimal(str(order.get("openPrice", 0))) if order.get("openPrice") else None,
            ))

        return orders

    async def get_order(self, order_id: str) -> Optional[OrderResult]:
        """Get order by ID."""
        if not self._connected:
            await self.connect()

        # Get all pending orders and search for the one with matching ID
        orders = await self.get_open_orders()
        for order in orders:
            if order.order_id == order_id:
                return order
        return None

    async def get_prices(self, symbols: List[str]) -> Dict[str, Tick]:
        """Get current prices for multiple symbols."""
        if not self._connected:
            await self.connect()

        prices = {}
        errors = []
        for symbol in symbols:
            try:
                tick = await self.get_current_price(symbol)
                prices[symbol] = tick
            except Exception as e:
                errors.append(f"{symbol}: {str(e)[:50]}")

        # Log errors for first few symbols only (to avoid spam)
        if errors and len(prices) == 0:
            print(f"[MetaTrader] get_prices failed for ALL {len(errors)} symbols!")
            print(f"[MetaTrader] First 3 errors: {errors[:3]}")
        elif errors:
            print(f"[MetaTrader] get_prices: {len(prices)} OK, {len(errors)} failed")

        return prices

    async def get_instruments(self) -> List[Instrument]:
        """Get list of available trading instruments."""
        if not self._connected:
            await self.connect()

        symbols_data = await self.get_symbols()
        instruments = []

        for sym_data in symbols_data:
            if isinstance(sym_data, dict):
                symbol = sym_data.get("symbol", "")
                description = sym_data.get("description", symbol)
                digits = sym_data.get("digits", 5)

                # Determine instrument type from symbol
                instrument_type = "forex"
                if any(x in symbol.upper() for x in ["XAU", "XAG", "GOLD", "SILVER"]):
                    instrument_type = "metals"
                elif any(x in symbol.upper() for x in ["OIL", "WTI", "BRENT", "GAS"]):
                    instrument_type = "commodities"
                elif any(x in symbol.upper() for x in ["US30", "US500", "NAS", "DAX", "FTSE", "JP225"]):
                    instrument_type = "indices"

                instruments.append(Instrument(
                    symbol=symbol,
                    name=description,
                    instrument_type=instrument_type,
                    pip_location=-digits,
                    min_size=Decimal(str(sym_data.get("volumeMin", 0.01))),
                    max_size=Decimal(str(sym_data.get("volumeMax", 100))) if sym_data.get("volumeMax") else None,
                    size_increment=Decimal(str(sym_data.get("volumeStep", 0.01))),
                ))
            else:
                # Simple string symbol
                instruments.append(Instrument(
                    symbol=str(sym_data),
                    name=str(sym_data),
                    instrument_type="forex",
                ))

        return instruments

    async def get_current_price(self, symbol: str) -> Tick:
        """Get current bid/ask price for symbol."""
        if not self._connected:
            await self.connect()

        broker_symbol = self._resolve_symbol(symbol)

        try:
            price_data = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/symbols/{broker_symbol}/current-price",
            )

            return Tick(
                symbol=symbol,  # Return original symbol for consistency
                bid=Decimal(str(price_data.get("bid", 0))),
                ask=Decimal(str(price_data.get("ask", 0))),
                timestamp=datetime.now(),
            )
        except Exception as e:
            raise Exception(f"Failed to get price for {symbol}: {e}")

    async def stream_prices(
        self,
        symbols: List[str],
    ) -> AsyncIterator[Tick]:
        """
        Stream live prices.

        Note: MetaApi uses WebSocket for real-time prices.
        This implementation polls in parallel for better performance.
        """
        if not self._connected:
            await self.connect()

        while True:
            # Fetch all prices in PARALLEL instead of sequentially
            async def safe_get_price(symbol: str) -> Optional[Tick]:
                try:
                    return await self.get_current_price(symbol)
                except Exception:
                    return None

            # Create tasks for all symbols
            tasks = [safe_get_price(symbol) for symbol in symbols]

            # Execute all in parallel
            results = await asyncio.gather(*tasks)

            # Yield all valid ticks
            for tick in results:
                if tick is not None:
                    yield tick

            await asyncio.sleep(0.5)  # Poll every 500ms for smoother updates

    async def get_symbols(self) -> List[Dict[str, Any]]:
        """Get available trading symbols."""
        if not self._connected:
            await self.connect()

        symbols = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/symbols",
        )

        return symbols

    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1h",
        count: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get historical candles.

        Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1mn
        """
        if not self._connected:
            await self.connect()

        # Map timeframe to MetaApi format
        tf_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
        }
        mt_timeframe = tf_map.get(timeframe, "1h")

        broker_symbol = self._resolve_symbol(symbol)

        candles = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/historical-market-data/symbols/{broker_symbol}/timeframes/{mt_timeframe}/candles",
            params={"limit": count},
        )

        return candles
