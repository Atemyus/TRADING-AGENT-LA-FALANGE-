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
import re
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote

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


class RateLimitError(Exception):
    """Raised when API rate limit is exceeded."""
    pass


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
        # Different brokers use various naming conventions for indices
        'US30': ['US30', 'US30m', 'US30.', 'US30.stp', 'US30-', 'US30_', 'US30Cash',
                 '.US30Cash', '.US30', 'US30.cash',  # Common broker patterns
                 'DJ30', 'DJI30', 'DOW30', 'DJIA', 'WS30', 'WS30m', '[US30]',
                 'USA30', 'USA30m', 'DowJones', 'DowJones30', 'USDJIND'],
        'US500': ['US500', 'US500m', 'US500.', 'US500.stp', 'US500-', 'US500_', 'US500Cash',
                  '.US500Cash', '.US500', 'US500.cash',  # Common broker patterns
                  'SPX500', 'SPX500m', 'SP500', 'SPX', 'SPXm', '.SPX500', '[US500]',
                  'USA500', 'USA500m', 'SPA500', 'S&P500', 'SP500m'],
        'NAS100': ['NAS100', 'NAS100m', 'NAS100.', 'NAS100.stp', 'NAS100-', 'NAS100_', 'NAS100Cash',
                   '.NAS100Cash', '.NAS100', 'NAS100.cash',  # Common broker patterns
                   'USTEC', 'USTECm', 'USTEC.', '.USTECCash', '.USTECHCash', 'USTECH', 'USTECHCash',
                   'NDX100', 'NASDAQ', 'NASDAQ100', 'NDX', 'NDXm', '[NAS100]', 'USTECH100', 'NSDQ100'],
        'US2000': ['US2000', 'US2000m', 'US2000.', 'US2000.stp', 'US2000-', 'US2000_', 'US2000Cash',
                   '.US2000Cash', '.US2000', 'US2000.cash',  # Common broker patterns
                   'RUSSELL', 'RUSSELL2000', 'RUT', 'RUTm', 'RTY', 'RTYm', 'RUS2000',
                   '[US2000]', 'USA2000'],

        # ============ EUROPEAN INDICES ============
        'DE40': ['DE40', 'DE40m', 'DE40.', 'DE40.stp', 'DE40-', 'DE40_', 'DE40Cash',
                 '.DE40Cash', '.DE40', 'DE40.cash',  # Common broker patterns
                 'GER40', 'GER40m', 'GER30', 'GER30m', 'DAX40', 'DAX', 'DAXm', 'DAX30',
                 '[DE40]', 'GERMANY40', 'GERMANY30', 'DEU40', 'DEU30'],
        'UK100': ['UK100', 'UK100m', 'UK100.', 'UK100.stp', 'UK100-', 'UK100_', 'UK100Cash',
                  '.UK100Cash', '.UK100', 'UK100.cash',  # Common broker patterns
                  'FTSE100', 'FTSE', 'FTSEm', 'FTSE.', '[UK100]',
                  'GBR100', 'GB100', 'UKFTSE'],
        'FR40': ['FR40', 'FR40m', 'FR40.', 'FR40.stp', 'FR40-', 'FR40_', 'FR40Cash',
                 '.FR40Cash', '.FR40', 'FR40.cash',  # Common broker patterns
                 'FRA40', 'FRA40m', 'CAC40', 'CAC', 'CACm', 'CAC.', '[FR40]',
                 'FRANCE40'],
        'EU50': ['EU50', 'EU50m', 'EU50.', 'EU50.stp', 'EU50-', 'EU50_', 'EU50Cash',
                 '.EU50Cash', '.EU50', 'EU50.cash',  # Common broker patterns
                 'EUSTX50', 'EUSTX50m', 'STOXX50', 'STOXX50m', 'SX5E', 'SX5Em',
                 '[EU50]', 'EURO50', 'EUR50', 'EUROSTOXX50'],
        'ES35': ['ES35', 'ES35m', 'ES35.', 'ES35.stp', 'ES35-', 'ES35_', 'ES35Cash',
                 '.ES35Cash', '.ES35', 'ES35.cash',  # Common broker patterns
                 'ESP35', 'ESP35m', 'IBEX35', 'IBEX', 'IBEXm', '[ES35]',
                 'SPAIN35', 'SPA35'],
        'IT40': ['IT40', 'IT40m', 'IT40.', 'IT40.stp', 'IT40-', 'IT40_', 'IT40Cash',
                 '.IT40Cash', '.IT40', 'IT40.cash',  # Common broker patterns
                 'ITA40', 'ITA40m', 'FTMIB', 'FTMIBm', 'MIB', 'MIBm', 'MIB40',
                 '[IT40]', 'ITALY40'],

        # ============ ASIAN INDICES ============
        'JP225': ['JP225', 'JP225m', 'JP225.', 'JP225.stp', 'JP225-', 'JP225_', 'JP225Cash',
                  '.JP225Cash', '.JP225', 'JP225.cash',  # Common broker patterns
                  'JPN225', 'JPN225m', 'NIKKEI', 'NIKKEI225', 'NIKKEIm', 'NI225', 'NI225m',
                  '[JP225]', 'JAPAN225', 'JAP225'],
        'HK50': ['HK50', 'HK50m', 'HK50.', 'HK50.stp', 'HK50-', 'HK50_', 'HK50Cash',
                 '.HK50Cash', '.HK50', 'HK50.cash',  # Common broker patterns
                 'HSI', 'HSIm', 'HSI50', 'HANGSENG', 'HK33', 'HK33m', '[HK50]',
                 'HONGKONG50', 'HKIND'],
        'AU200': ['AU200', 'AU200m', 'AU200.', 'AU200.stp', 'AU200-', 'AU200_', 'AU200Cash',
                  '.AU200Cash', '.AU200', 'AU200.cash',  # Common broker patterns
                  'AUS200', 'AUS200m', 'ASX200', 'ASX', 'ASXm', '[AU200]',
                  'AUSTRALIA200', 'AUIND'],
        'CN50': ['CN50', 'CN50m', 'CN50.', 'CN50.stp', 'CN50-', 'CN50_', 'CN50Cash',
                 '.CN50Cash', '.CN50', 'CN50.cash',  # Common broker patterns
                 'CHINA50', 'CHINA50m', 'CHINAA50', 'A50', 'A50m', 'CNA50', '[CN50]',
                 'CHINA', 'CHN50', 'FTXIN50'],

        # ============ OTHER INDICES ============
        'VIX': ['VIX', 'VIXm', 'VIX.', 'VOLATILITY', 'UVXY', '.VIX', '[VIX]', 'CBOE_VIX'],

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

    # Affixes frequently used by MT brokers around instrument names.
    LOOKUP_AFFIX_SUFFIXES = (
        "MICRO", "MINI", "NANO",
        "CASH", "SPOT",
        "PRO", "RAW", "ECN", "STP",
        "MT4", "MT5",
        "M", "I", "R", "S", "Z", "P", "Q",
    )
    LOOKUP_AFFIX_PREFIXES = (
        "MICRO", "MINI", "NANO",
        "PRO", "RAW", "ECN", "STP",
        "MT4", "MT5",
        "M", "I", "R", "S", "Z", "P", "Q",
    )
    CONTRACT_TAIL_PATTERNS = (
        r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)(20)?\d{2}$",
        r"Q[1-4](20)?\d{2}$",
        r"[FGHJKMNQUVXZ]\d{1,2}$",
    )

    # Cache TTLs (in seconds)
    ACCOUNT_INFO_CACHE_TTL = 30  # Cache account info for 30 seconds
    POSITIONS_CACHE_TTL = 15  # Cache positions for 15 seconds
    PRICES_CACHE_TTL = 8  # Cache prices for 8 seconds (prevents rate limiting)
    ORDERS_CACHE_TTL = 10  # Cache orders for 10 seconds

    def __init__(
        self,
        access_token: str | None = None,
        account_id: str | None = None,
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
        self._client: httpx.AsyncClient | None = None
        self._account_info: dict[str, Any] | None = None
        self._connected = False
        self._symbol_map: dict[str, str] = {}  # Maps our symbols to broker symbols
        self._broker_symbols: list[str] = []  # List of available broker symbols
        self._broker_symbol_meta: dict[str, dict[str, Any]] = {}  # Raw symbol metadata from MetaApi
        self._broker_token_map: dict[str, str] = {}  # token -> unique broker symbol
        self._broker_token_collisions: set[str] = set()
        self._alias_lookup_map: dict[str, str] = self._build_alias_lookup_map()
        self._client_api_url: str | None = None  # Set during connect based on region

        # Cache for API responses to avoid rate limiting
        self._cache: dict[str, dict[str, Any]] = {}  # key -> {"data": ..., "expires": timestamp}
        self._rate_limit_until: float | None = None  # Timestamp until which we should not make API calls
        self._rate_limit_endpoint: str | None = None  # Which endpoint is rate limited

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

    def _get_cache(self, key: str) -> Any | None:
        """Get cached data if not expired."""
        if key in self._cache:
            cached = self._cache[key]
            if time.time() < cached["expires"]:
                return cached["data"]
            else:
                # Expired, remove from cache
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any, ttl: int) -> None:
        """Set cache with TTL in seconds."""
        self._cache[key] = {
            "data": data,
            "expires": time.time() + ttl,
        }

    def _is_rate_limited(self, endpoint: str = None) -> bool:
        """Check if we're currently rate limited."""
        if self._rate_limit_until is None:
            return False
        if time.time() >= self._rate_limit_until:
            # Rate limit has expired
            self._rate_limit_until = None
            self._rate_limit_endpoint = None
            return False
        return True

    def _set_rate_limit(self, retry_time: str, endpoint: str) -> None:
        """Set rate limit from API response."""
        try:
            # Parse ISO format: "2026-01-26T21:08:21.567Z"
            retry_dt = datetime.fromisoformat(retry_time.replace("Z", "+00:00"))
            self._rate_limit_until = retry_dt.timestamp()
            self._rate_limit_endpoint = endpoint
            print(f"[MetaTrader] Rate limited until {retry_time} for endpoint: {endpoint}")
        except Exception as e:
            # If parsing fails, set a 5 minute backoff
            self._rate_limit_until = time.time() + 300
            self._rate_limit_endpoint = endpoint
            print(f"[MetaTrader] Rate limited (parse error: {e}), backing off for 5 minutes")

    def _is_metaapi_routing_or_connection_error(self, error_text: str) -> bool:
        """Detect MetaApi errors which are usually resolved by region/account-state refresh."""
        lowered = (error_text or "").lower()
        markers = (
            "does not match the account region",
            "not connected to broker yet",
            "api-access/api-urls",
            '"error":"timeouterror"',
        )
        return any(marker in lowered for marker in markers)

    async def _refresh_metaapi_routing(
        self,
        *,
        wait_for_connected: bool = True,
        max_wait_checks: int = 6,
        wait_seconds: int = 5,
    ) -> bool:
        """
        Refresh account region routing and optionally wait for terminal connection.
        Returns True when account is connected, otherwise False.
        """
        account = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}",
            base_url=self.PROVISIONING_URL,
            retry_on_metaapi_region_error=False,
        )

        region = account.get("region", "vint-hill")
        self._client_api_url = f"https://mt-client-api-v1.{region}.agiliumtrade.ai"
        state = account.get("state", "UNKNOWN")
        conn_status = account.get("connectionStatus", "UNKNOWN")

        if state != "DEPLOYED":
            print(f"[MetaTrader] Account state={state}, deploying before retry...")
            await self._request(
                "POST",
                f"/users/current/accounts/{self.account_id}/deploy",
                base_url=self.PROVISIONING_URL,
                retry_on_metaapi_region_error=False,
            )
            await asyncio.sleep(wait_seconds)
            account = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}",
                base_url=self.PROVISIONING_URL,
                retry_on_metaapi_region_error=False,
            )
            conn_status = account.get("connectionStatus", "UNKNOWN")

        if not wait_for_connected:
            return conn_status == "CONNECTED"

        if conn_status == "CONNECTED":
            return True

        for i in range(max_wait_checks):
            await asyncio.sleep(wait_seconds)
            account = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}",
                base_url=self.PROVISIONING_URL,
                retry_on_metaapi_region_error=False,
            )
            conn_status = account.get("connectionStatus", "UNKNOWN")
            if conn_status == "CONNECTED":
                return True
            print(
                f"[MetaTrader] Waiting terminal connection {i + 1}/{max_wait_checks}: "
                f"{conn_status}"
            )

        return False

    async def _request(
        self,
        method: str,
        endpoint: str,
        base_url: str | None = None,
        retry_on_metaapi_region_error: bool = True,
        **kwargs
    ) -> dict[str, Any]:
        """Make API request with rate limit handling."""
        await self._ensure_client()

        # Use provided base_url, or the client API URL (set during connect), or fallback
        effective_base_url = base_url or self._client_api_url or "https://mt-client-api-v1.vint-hill.agiliumtrade.ai"
        url = f"{effective_base_url}{endpoint}"
        response = await self._client.request(method, url, **kwargs)

        if response.status_code == 429:
            # Rate limit hit - parse the error to get retry time
            try:
                error_data = response.json()
                retry_time = error_data.get("metadata", {}).get("recommendedRetryTime")
                if retry_time:
                    self._set_rate_limit(retry_time, endpoint)
            except Exception:
                # Set a default 5 minute backoff
                self._rate_limit_until = time.time() + 300
                self._rate_limit_endpoint = endpoint

            raise RateLimitError(f"MetaApi rate limit exceeded for {endpoint}")

        if response.status_code >= 400:
            error_text = response.text
            should_retry_routing = (
                retry_on_metaapi_region_error
                and response.status_code in {500, 502, 503, 504}
                and effective_base_url != self.PROVISIONING_URL
                and self._is_metaapi_routing_or_connection_error(error_text)
            )
            if should_retry_routing:
                print(
                    f"[MetaTrader] MetaApi {response.status_code} indicates routing/connection issue. "
                    "Refreshing account routing and retrying once..."
                )
                try:
                    connected = await self._refresh_metaapi_routing(
                        wait_for_connected=True,
                        max_wait_checks=6,
                        wait_seconds=5,
                    )
                    if not connected:
                        raise Exception(
                            "MetaApi account is not connected to broker yet (connectionStatus!=CONNECTED). "
                            "Open MetaApi dashboard, verify MT login/server/password, deploy account, and retry."
                        )
                    return await self._request(
                        method,
                        endpoint,
                        base_url=base_url,
                        retry_on_metaapi_region_error=False,
                        **kwargs,
                    )
                except Exception as refresh_error:
                    print(f"[MetaTrader] Routing refresh failed: {refresh_error}")

            # For trade endpoints, try to return JSON body so caller can parse error details
            if "/trade" in endpoint:
                try:
                    error_json = response.json()
                    print(f"[MetaApi] Trade error ({response.status_code}): {error_json}")
                    # Return the JSON so place_order can parse stringCode/numericCode
                    return error_json
                except Exception:
                    pass
            raise Exception(f"MetaApi error ({response.status_code}): {error_text}")

        if response.status_code == 204:
            return {}

        return response.json()

    def _build_alias_lookup_map(self) -> dict[str, str]:
        """
        Build token->canonical lookup map from SYMBOL_ALIASES.

        Allows users to type common variants (e.g. DAX, XAUUSD, GER40Cash#)
        while keeping internal canonical keys (e.g. DE40, XAU_USD).
        """
        mapping: dict[str, str] = {}
        for canonical, aliases in self.SYMBOL_ALIASES.items():
            raw_variants = [canonical, canonical.replace("_", ""), *aliases]
            for variant in raw_variants:
                token = self._normalize_symbol_token(variant)
                if token and token not in mapping:
                    mapping[token] = canonical
        return mapping

    def _symbol_lookup_key(self, symbol: str) -> str:
        raw = (symbol or "").replace("/", "_").strip().upper()
        if not raw:
            return raw

        token = self._normalize_symbol_token(raw)
        if not token:
            return raw

        for candidate in self._expand_symbol_token_candidates(token):
            canonical = self._alias_lookup_map.get(candidate)
            if canonical:
                return canonical

        for candidate in self._expand_symbol_token_candidates(token):
            broker_symbol = self._broker_token_map.get(candidate)
            if broker_symbol:
                return broker_symbol

        return raw

    def _normalize_symbol_token(self, symbol: str) -> str:
        return "".join(ch for ch in (symbol or "").upper() if ch.isalnum())

    def _encode_symbol_path(self, symbol: str) -> str:
        """Encode broker-native symbol for safe usage inside URL path segments."""
        return quote(str(symbol or ""), safe="")

    def _strip_contract_tail_token(self, token: str) -> str:
        current = token
        for pattern in self.CONTRACT_TAIL_PATTERNS:
            updated = re.sub(pattern, "", current)
            if updated != current and updated:
                return updated
        return current

    def _expand_symbol_token_candidates(self, token: str) -> list[str]:
        if not token:
            return []

        ordered: list[str] = []
        seen: set[str] = set()
        pending: list[str] = [token]

        while pending and len(ordered) < 48:
            current = pending.pop(0)
            if not current or current in seen:
                continue
            seen.add(current)
            ordered.append(current)

            stripped_contract = self._strip_contract_tail_token(current)
            if stripped_contract and stripped_contract != current:
                pending.append(stripped_contract)

            for suffix in self.LOOKUP_AFFIX_SUFFIXES:
                if current.endswith(suffix) and len(current) > (len(suffix) + 2):
                    pending.append(current[: -len(suffix)])

            for prefix in self.LOOKUP_AFFIX_PREFIXES:
                if current.startswith(prefix) and len(current) > (len(prefix) + 2):
                    pending.append(current[len(prefix):])

            if len(current) > 6 and current[-1:].isdigit():
                pending.append(current[:-1])
            if len(current) > 7 and current[-2:].isdigit():
                pending.append(current[:-2])
            if len(current) > 6 and current[:1].isdigit():
                pending.append(current[1:])
            if len(current) > 7 and current[:2].isdigit():
                pending.append(current[2:])

        return ordered

    def _candidate_bases(self, symbol: str) -> list[str]:
        lookup = self._symbol_lookup_key(symbol)
        raw_candidates = [lookup.replace("_", ""), *self.SYMBOL_ALIASES.get(lookup, [])]
        normalized: list[str] = []
        seen: set[str] = set()
        for candidate in raw_candidates:
            token = self._normalize_symbol_token(candidate)
            if not token:
                continue
            for variant in self._expand_symbol_token_candidates(token):
                if variant and variant not in seen:
                    seen.add(variant)
                    normalized.append(variant)
        return normalized

    def _lookup_probe_tokens(self, lookup: str) -> list[str]:
        """
        Build search probes for fuzzy broker-symbol matching when direct alias
        mapping is not enough.
        """
        stopwords = {
            "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
            "SGD", "HKD", "NOK", "SEK", "DKK", "PLN", "TRY", "MXN",
            "ZAR", "CNH", "HUF", "CZK", "RON",
            "CASH", "SPOT", "PRO", "RAW", "ECN", "STP", "MICRO", "MINI",
            "MT4", "MT5",
        }
        probes: set[str] = set()
        for base in self._candidate_bases(lookup)[:14]:
            for part in re.findall(r"[A-Z0-9]{3,}", base.upper()):
                if part in stopwords:
                    continue
                probes.add(part)

        # Metals often use broker-specific names with only GOLD/SILVER in description.
        if "XAU" in probes or lookup == "XAU_USD":
            probes.update({"XAU", "GOLD"})
        if "XAG" in probes or lookup == "XAG_USD":
            probes.update({"XAG", "SILVER"})

        ordered = sorted(probes, key=lambda token: (-len(token), token))
        return ordered[:20]

    def _match_broker_symbols_by_lookup(self, lookup: str, limit: int = 20) -> list[str]:
        if not self._broker_symbols:
            return []

        probes = self._lookup_probe_tokens(lookup)
        if not probes:
            return []

        scored: list[tuple[int, str]] = []
        for broker_symbol in self._broker_symbols:
            token = self._normalize_symbol_token(broker_symbol)
            meta = self._broker_symbol_meta.get(broker_symbol, {})
            description = self._normalize_symbol_token(str(meta.get("description", "")))
            if not token and not description:
                continue

            best_score = 0
            for probe in probes:
                if probe in token or probe in description:
                    best_score = max(best_score, len(probe))

            if best_score > 0:
                scored.append((best_score, broker_symbol))

        scored.sort(key=lambda item: (-item[0], len(item[1]), item[1]))
        ordered: list[str] = []
        seen: set[str] = set()
        for _, broker_symbol in scored:
            if broker_symbol in seen:
                continue
            seen.add(broker_symbol)
            ordered.append(broker_symbol)
            if len(ordered) >= limit:
                break
        return ordered

    def _is_forex_lookup(self, lookup: str) -> bool:
        parts = (lookup or "").split("_")
        return len(parts) == 2 and all(len(part) == 3 and part.isalpha() for part in parts)

    def _split_forex_lookup(self, lookup: str) -> tuple[str, str] | None:
        parts = (lookup or "").split("_")
        if len(parts) != 2:
            return None
        base, quote = parts[0], parts[1]
        if len(base) == 3 and len(quote) == 3 and base.isalpha() and quote.isalpha():
            return (base, quote)
        return None

    def _is_forex_candidate_compatible(self, lookup: str, broker_symbol: str) -> bool:
        """
        Ensure forex routing does not accidentally select a different cross.
        Example: USD_CAD must not resolve to USDCADTRY.
        """
        pair = self._split_forex_lookup(lookup)
        if not pair:
            return True

        pair_token = f"{pair[0]}{pair[1]}"
        token = self._normalize_symbol_token(broker_symbol)
        if not token or pair_token not in token:
            return False

        idx = token.find(pair_token)
        prefix = token[:idx]
        suffix = token[idx + len(pair_token):]
        extras = [prefix, suffix]

        known_affixes = {
            "M", "I", "R", "S", "Z",
            "PRO", "RAW", "ECN", "CASH", "SPOT", "MICRO", "MINI", "STD",
            "MT4", "MT5",
        }
        currency_codes = {
            "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD",
            "SGD", "HKD", "NOK", "SEK", "DKK", "PLN", "TRY", "MXN",
            "ZAR", "HUF", "CZK", "RON", "ILS", "CNH",
        }

        for extra in extras:
            if not extra:
                continue
            if extra in known_affixes:
                continue
            if extra.isdigit():
                continue
            if len(extra) <= 2:
                continue
            # Explicitly reject tails/prefixes that look like another currency.
            if extra in currency_codes:
                return False
            if len(extra) >= 3:
                if any(extra.startswith(code) or extra.endswith(code) for code in currency_codes):
                    return False
            # Unknown long alphabetic tails are likely different instruments.
            if extra.isalpha() and len(extra) > 4:
                return False
        return True

    def _is_plausible_price_for_lookup(
        self,
        lookup: str,
        bid: float,
        ask: float,
    ) -> bool:
        """
        Sanity check used during symbol candidate routing.
        Reject obviously wrong scales for forex pairs to avoid mismatched symbols.
        """
        if bid <= 0 or ask <= 0 or ask < bid:
            return False

        pair = self._split_forex_lookup(lookup)
        if not pair:
            return True

        mid = (bid + ask) / 2.0
        spread = ask - bid
        if mid <= 0:
            return False

        # Defensive spread sanity for forex (5% is already very permissive).
        if (spread / mid) > 0.05:
            return False

        quote = pair[1]
        bounds_by_quote: dict[str, tuple[float, float]] = {
            "JPY": (10.0, 500.0),
            "HUF": (10.0, 5000.0),
            "CLP": (10.0, 20000.0),
            "IDR": (100.0, 200000.0),
            "KRW": (100.0, 10000.0),
            "TRY": (0.05, 500.0),
            "MXN": (0.05, 500.0),
            "ZAR": (0.05, 500.0),
            "NOK": (0.05, 500.0),
            "SEK": (0.05, 500.0),
            "DKK": (0.05, 500.0),
            "PLN": (0.05, 500.0),
            "CZK": (0.05, 500.0),
            "HKD": (0.05, 100.0),
            "SGD": (0.05, 50.0),
        }
        low, high = bounds_by_quote.get(quote, (0.02, 10.0))
        return low <= mid <= high

    def _extract_spec_currency(
        self,
        spec: dict[str, Any] | None,
        keys: tuple[str, ...],
    ) -> str:
        if not isinstance(spec, dict):
            return ""
        for key in keys:
            raw = spec.get(key)
            if raw is None:
                continue
            token = self._normalize_symbol_token(str(raw))
            if len(token) == 3 and token.isalpha():
                return token
            if len(token) > 3 and token[:3].isalpha():
                return token[:3]
        return ""

    def _is_forex_spec_compatible(self, lookup: str, spec: dict[str, Any] | None) -> bool:
        """
        Validate forex pair routing against broker-provided symbol specification.
        If spec has no currency fields, keep candidate as potentially valid.
        """
        pair = self._split_forex_lookup(lookup)
        if not pair:
            return True

        expected_base, expected_quote = pair
        base = self._extract_spec_currency(
            spec,
            ("currencyBase", "baseCurrency", "currencyBaseCode", "base"),
        )
        quote = self._extract_spec_currency(
            spec,
            (
                "currencyProfit",
                "currencyQuote",
                "quoteCurrency",
                "profitCurrency",
                "counterCurrency",
                "currencyCounter",
            ),
        )

        if base and base != expected_base:
            return False
        if quote and quote != expected_quote:
            return False
        return True

    def _is_futures_intent_lookup(self, lookup: str) -> bool:
        """
        Return True when our internal symbol explicitly targets futures contracts.
        Examples: ES1, NQ1, YM1, CL1, 6E1.
        """
        token = self._normalize_symbol_token(lookup)
        if not token or not token.endswith("1"):
            return False
        if token in {"US30", "US500", "US2000", "NAS100"}:
            return False
        if len(token) <= 5:
            return True
        known_prefixes = {"ES", "NQ", "YM", "RTY", "GC", "SI", "CL", "NG", "6E", "6B", "6J", "ZB", "ZN"}
        return any(token.startswith(prefix) for prefix in known_prefixes)

    def _looks_like_dated_contract(self, broker_symbol: str) -> bool:
        upper = (broker_symbol or "").upper()
        if not upper:
            return False

        month_pattern = r"(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
        if re.search(rf"(?:^|[^A-Z]){month_pattern}(?:20)?\d{{2}}(?:[^A-Z]|$)", upper):
            return True
        if re.search(r"(?:^|[^A-Z])Q[1-4](?:20)?\d{2}(?:[^A-Z]|$)", upper):
            return True

        token = self._normalize_symbol_token(upper)
        if re.search(r"[FGHJKMNQUVXZ]\d{1,2}$", token):
            return True
        return False

    def _variant_score_adjustment(self, lookup: str, broker_symbol: str) -> int:
        """
        Prefer spot/cash symbols and penalize expiring futures-style contracts.
        This keeps routing stable across brokers using suffix/prefix naming.
        """
        upper = (broker_symbol or "").upper()
        token = self._normalize_symbol_token(upper)
        if not token:
            return 0

        adjustment = 0
        if any(marker in upper for marker in ("CASH", "SPOT", ".CASH", "_CASH", "#")):
            adjustment += 80
        if any(marker in upper for marker in ("FUT", "FUTURE", "CONTRACT", "ROLL")):
            adjustment -= 120
        if self._looks_like_dated_contract(upper):
            adjustment -= 220

        # For forex pairs, dated contracts are almost always a wrong variant.
        if self._is_forex_lookup(lookup) and self._looks_like_dated_contract(upper):
            adjustment -= 140

        return adjustment

    def _score_symbol_match(self, broker_symbol: str, bases: list[str], lookup: str) -> int:
        broker_token = self._normalize_symbol_token(broker_symbol)
        if not broker_token:
            return 0

        if self._is_forex_lookup(lookup) and not self._is_forex_candidate_compatible(lookup, broker_symbol):
            return 0

        best = 0
        matched = False
        for idx, base in enumerate(bases):
            if not base:
                continue
            score = 0
            if broker_token == base:
                score = 1000
            elif broker_token.startswith(base) or broker_token.endswith(base):
                score = 920
            elif base in broker_token:
                score = 860
            elif broker_token in base:
                score = 760
            else:
                continue

            matched = True
            score -= abs(len(broker_token) - len(base))
            score += max(0, 120 - (idx * 6))  # Respect alias priority (canonical first)
            if score > best:
                best = score

        if not matched:
            return 0

        best += self._variant_score_adjustment(lookup, broker_symbol)
        return max(1, best)

    def _get_symbol_candidates(self, symbol: str) -> list[str]:
        lookup = self._symbol_lookup_key(symbol)
        if not self._broker_symbols:
            raw_candidates = [lookup.replace("_", ""), *self.SYMBOL_ALIASES.get(lookup, [])]
            ordered_fallback: list[str] = []
            seen_tokens: set[str] = set()
            for candidate in raw_candidates:
                normalized = self._normalize_symbol_token(candidate)
                if not normalized or normalized in seen_tokens:
                    continue
                seen_tokens.add(normalized)
                ordered_fallback.append(candidate)
            return ordered_fallback or [lookup.replace("_", "")]

        bases = self._candidate_bases(lookup)
        scored: list[tuple[int, str]] = []
        score_by_symbol: dict[str, int] = {}
        for broker_symbol in self._broker_symbols:
            score = self._score_symbol_match(broker_symbol, bases, lookup)
            if score > 0:
                scored.append((score, broker_symbol))
                score_by_symbol[broker_symbol] = score

        if not scored:
            # Some broker setups expose fewer symbols in /symbols than those tradable
            # via current-price/trade endpoints. Try canonical + aliases as fallback.
            sticky = self._symbol_map.get(lookup)
            fuzzy_matches = self._match_broker_symbols_by_lookup(lookup, limit=20)
            raw_candidates = [
                sticky,
                *fuzzy_matches,
                lookup.replace("_", ""),
                *self.SYMBOL_ALIASES.get(lookup, []),
            ]
            ordered_fallback: list[str] = []
            seen_tokens: set[str] = set()
            for candidate in raw_candidates:
                if not candidate:
                    continue
                normalized = self._normalize_symbol_token(candidate)
                if not normalized or normalized in seen_tokens:
                    continue
                seen_tokens.add(normalized)
                ordered_fallback.append(candidate)
            return ordered_fallback

        scored.sort(key=lambda item: (-item[0], len(item[1])))
        ordered: list[str] = []
        seen: set[str] = set()
        for _, broker_symbol in scored:
            if broker_symbol not in seen:
                seen.add(broker_symbol)
                ordered.append(broker_symbol)

        # If this lookup is not futures-oriented, avoid expiring contracts when
        # non-dated variants are available (e.g. prefer GER40Cash# over GER40-MAR26).
        if not self._is_futures_intent_lookup(lookup):
            non_dated = [s for s in ordered if not self._looks_like_dated_contract(s)]
            dated = [s for s in ordered if self._looks_like_dated_contract(s)]
            if non_dated:
                ordered = [*non_dated, *dated]

        mapped = self._symbol_map.get(lookup)
        if mapped and mapped in seen:
            top_score = scored[0][0]
            mapped_score = score_by_symbol.get(mapped, 0)
            # Keep sticky mapping only if comparable with current best candidate.
            if mapped_score >= (top_score - 40):
                ordered = [mapped, *[item for item in ordered if item != mapped]]
            else:
                print(
                    f"[MetaTrader] Ignoring stale mapped symbol {mapped} for {lookup} "
                    f"(mappedScore={mapped_score}, bestScore={top_score})"
                )

        return ordered

    def _is_trade_mode_compatible(self, trade_mode: Any, side: OrderSide | None = None) -> bool:
        """Return True if symbol tradeMode allows opening a position for the requested side."""
        if trade_mode is None:
            return True

        if isinstance(trade_mode, (int, float)):
            mode = int(trade_mode)
            if mode == 0:  # SYMBOL_TRADE_MODE_DISABLED
                return False
            if mode == 1:  # SYMBOL_TRADE_MODE_LONGONLY
                return side != OrderSide.SELL
            if mode == 2:  # SYMBOL_TRADE_MODE_SHORTONLY
                return side != OrderSide.BUY
            if mode == 3:  # SYMBOL_TRADE_MODE_CLOSEONLY
                return False
            if mode == 4:  # SYMBOL_TRADE_MODE_FULL
                return True
            return True

        mode = str(trade_mode).strip().upper()
        if not mode:
            return True
        if "DISABLED" in mode or "CLOSEONLY" in mode or "CLOSE_ONLY" in mode:
            return False
        if "LONGONLY" in mode or "LONG_ONLY" in mode:
            return side != OrderSide.SELL
        if "SHORTONLY" in mode or "SHORT_ONLY" in mode:
            return side != OrderSide.BUY
        return True

    def _is_symbol_lookup_error(self, error_text: str) -> bool:
        lowered = (error_text or "").lower()
        markers = (
            "invalid symbol",
            "symbol not found",
            "unknown symbol",
            "symbol does not exist",
            "no prices for symbol",
            "failed to resolve symbol",
            "not subscribed",
            "could not find path",
            "notfounderror",
            "/symbols/",
            ". not found",
        )
        return any(marker in lowered for marker in markers)

    def _is_invalid_stops_rejection(self, string_code: str | None, message: str | None) -> bool:
        code = (string_code or "").upper()
        text = (message or "").upper()
        if code == "TRADE_RETCODE_INVALID_STOPS":
            return True
        markers = (
            "INVALID_STOPS",
            "INVALID STOPS",
            "SL/TP NON VALIDI",
            "STOP LEVEL",
            "STOPS LEVEL",
            "FREEZE LEVEL",
            "TOO CLOSE",
            "MINIMUM DISTANCE",
        )
        return any(marker in text for marker in markers)

    async def _modify_position_by_id(
        self,
        position_id: str,
        stop_loss: float | None = None,
        take_profit: float | None = None,
    ) -> bool:
        payload = {
            "actionType": "POSITION_MODIFY",
            "positionId": str(position_id),
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
        except Exception as exc:
            print(f"[MetaTrader] Failed to apply SL/TP via positionId={position_id}: {exc}")
            return False

    async def _get_symbol_specification_for_broker_symbol(self, broker_symbol: str) -> dict[str, Any]:
        """Get symbol specification using broker-native symbol name."""
        if not self._connected:
            await self.connect()

        cache_key = f"symbol_spec_broker_{broker_symbol}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        spec = await self._request(
            "GET",
            f"/users/current/accounts/{self.account_id}/symbols/{self._encode_symbol_path(broker_symbol)}/specification",
        )
        self._set_cache(cache_key, spec, 300)  # Cache for 5 minutes
        return spec

    async def _resolve_symbol_for_order(
        self,
        symbol: str,
        side: OrderSide,
    ) -> tuple[str, dict[str, Any], str | None]:
        """
        Resolve symbol and prefer a tradable variant if broker uses prefixes/suffixes.
        Returns: (broker_symbol, spec, optional_error_message)
        """
        lookup = self._symbol_lookup_key(symbol)
        if not self._broker_symbols:
            await self._ensure_symbol_inventory(force_reload=True)
        candidates = self._get_symbol_candidates(lookup)
        if not candidates:
            fallback = lookup.replace("_", "")
            self._symbol_map[lookup] = fallback
            try:
                spec = await self._get_symbol_specification_for_broker_symbol(fallback)
            except Exception:
                spec = {}
            return fallback, spec, None

        disabled_details: list[str] = []
        unknown_mode_candidates: list[tuple[str, dict[str, Any]]] = []
        unresolved_spec_candidates: list[str] = []

        for broker_symbol in candidates[:30]:
            if self._is_forex_lookup(lookup) and not self._is_forex_candidate_compatible(lookup, broker_symbol):
                disabled_details.append(f"{broker_symbol}(FOREX_MISMATCH)")
                continue

            try:
                spec = await self._get_symbol_specification_for_broker_symbol(broker_symbol)
            except Exception as exc:
                print(f"[MetaTrader] Symbol spec lookup failed for {broker_symbol}: {exc}")
                unresolved_spec_candidates.append(broker_symbol)
                continue

            if self._is_forex_lookup(lookup) and not self._is_forex_spec_compatible(lookup, spec):
                disabled_details.append(f"{broker_symbol}(FOREX_SPEC_MISMATCH)")
                continue

            trade_mode = spec.get("tradeMode")
            if trade_mode in {None, ""}:
                trade_mode = self._broker_symbol_meta.get(broker_symbol, {}).get("tradeMode")

            if trade_mode in {None, ""}:
                unknown_mode_candidates.append((broker_symbol, spec))
                continue

            if self._is_trade_mode_compatible(trade_mode, side):
                self._symbol_map[lookup] = broker_symbol
                return broker_symbol, spec, None

            disabled_details.append(f"{broker_symbol}({trade_mode})")

        if unknown_mode_candidates:
            broker_symbol, spec = unknown_mode_candidates[0]
            self._symbol_map[lookup] = broker_symbol
            return broker_symbol, spec, None

        if unresolved_spec_candidates:
            broker_symbol = unresolved_spec_candidates[0]
            self._symbol_map[lookup] = broker_symbol
            print(
                f"[MetaTrader] Falling back to unresolved-spec candidate for {lookup}: "
                f"{broker_symbol}"
            )
            return broker_symbol, {}, None

        fallback_symbol = candidates[0]
        self._symbol_map[lookup] = fallback_symbol
        detail = (
            f"Nessuna variante tradabile trovata per {lookup}. "
            f"Varianti controllate: {', '.join(disabled_details[:8])}"
        )
        if len(disabled_details) > 8:
            detail += f" (+{len(disabled_details) - 8} altre)"
        return fallback_symbol, {}, detail

    async def can_trade_symbol(
        self,
        symbol: str,
        side: OrderSide,
    ) -> tuple[bool, str, str | None]:
        """
        Check whether a symbol can be traded for the requested side.
        Returns (is_tradable, reason_if_not, resolved_broker_symbol).
        """
        broker_symbol, spec, resolution_error = await self._resolve_symbol_for_order(symbol, side)
        if resolution_error:
            return (False, resolution_error, None)

        trade_mode = spec.get("tradeMode") if spec else self._broker_symbol_meta.get(broker_symbol, {}).get("tradeMode")
        if not self._is_trade_mode_compatible(trade_mode, side):
            return (
                False,
                (
                    f"Trading non consentito su {broker_symbol} per side={side.value} "
                    f"(tradeMode={trade_mode})."
                ),
                broker_symbol,
            )

        return (True, "", broker_symbol)

    def _resolve_symbol(self, symbol: str) -> str:
        """
        Resolve our internal symbol to broker symbol, supporting arbitrary prefixes/suffixes.
        """
        lookup = self._symbol_lookup_key(symbol)
        mapped = self._symbol_map.get(lookup)
        if mapped:
            return mapped

        candidates = self._get_symbol_candidates(lookup)
        if candidates:
            resolved = candidates[0]
            self._symbol_map[lookup] = resolved
            return resolved

        fallback = lookup.replace("_", "")
        if lookup not in self._symbol_map:
            aliases = self.SYMBOL_ALIASES.get(lookup, [])
            print(f"[MetaTrader] WARNING: Could not resolve symbol '{lookup}' to broker format")
            print(f"[MetaTrader] Tried aliases: {aliases[:5]}...")
        self._symbol_map[lookup] = fallback
        return fallback

    async def _build_symbol_map(self) -> None:
        """Build symbol mapping from broker's available symbols."""
        try:
            symbols = await self.get_symbols()
            self._broker_symbols = []
            self._broker_symbol_meta = {}
            for item in symbols:
                if isinstance(item, dict):
                    broker_symbol = str(item.get("symbol", "")).strip()
                    if not broker_symbol:
                        continue
                    self._broker_symbols.append(broker_symbol)
                    self._broker_symbol_meta[broker_symbol] = item
                else:
                    broker_symbol = str(item).strip()
                    if not broker_symbol:
                        continue
                    self._broker_symbols.append(broker_symbol)

            # Deduplicate while preserving order
            self._broker_symbols = list(dict.fromkeys(self._broker_symbols))
            self._broker_token_map = {}
            self._broker_token_collisions = set()
            for broker_symbol in self._broker_symbols:
                token = self._normalize_symbol_token(broker_symbol)
                if not token:
                    continue
                existing = self._broker_token_map.get(token)
                if existing and existing != broker_symbol:
                    self._broker_token_collisions.add(token)
                else:
                    self._broker_token_map[token] = broker_symbol
            for token in self._broker_token_collisions:
                self._broker_token_map.pop(token, None)

            print(f"[MetaTrader] Broker has {len(self._broker_symbols)} symbols available")

            # Log indices found on broker (helpful for debugging)
            index_keywords = ['30', '40', '50', '100', '200', '225', '500', 'DAX', 'FTSE', 'CAC',
                              'IBEX', 'NIKKEI', 'STOXX', 'DOW', 'SPX', 'NAS', 'HSI', 'ASX']
            found_indices = [s for s in self._broker_symbols
                             if any(kw in s.upper() for kw in index_keywords)]
            if found_indices:
                print(f"[MetaTrader] Indices found on broker: {found_indices[:15]}")
                if len(found_indices) > 15:
                    print(f"[MetaTrader] ... and {len(found_indices) - 15} more indices")
            else:
                print("[MetaTrader] WARNING: No indices found on broker!")

            # Pre-map common symbols
            mapped_count = 0
            for our_symbol in self.SYMBOL_ALIASES.keys():
                resolved = self._resolve_symbol(our_symbol)
                if resolved != our_symbol.replace('_', ''):
                    mapped_count += 1

            print(f"[MetaTrader] Successfully mapped {mapped_count}/{len(self.SYMBOL_ALIASES)} symbols to broker format")

        except Exception as e:
            print(f"Warning: Could not build symbol map: {e}")

    async def _ensure_symbol_inventory(self, *, force_reload: bool = False) -> None:
        """
        Ensure broker symbols metadata is available.
        Useful when initial symbol-map build failed during connect.
        """
        if not self._connected:
            await self.connect()
            return
        if self._broker_symbols and not force_reload:
            return

        before = len(self._broker_symbols)
        await self._build_symbol_map()
        after = len(self._broker_symbols)
        if after == 0:
            print("[MetaTrader] WARNING: Broker symbol inventory still empty after refresh")
        elif force_reload and after != before:
            print(f"[MetaTrader] Symbol inventory refreshed: {before} -> {after}")

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

            # Check connection status
            conn_status = account.get("connectionStatus", "UNKNOWN")
            print(f"[MetaTrader] Account state: {account.get('state')} | connectionStatus: {conn_status}")

            if conn_status != "CONNECTED":
                # Wait for terminal to connect to broker
                print(f"[MetaTrader] Terminal status is {conn_status}, waiting for connection...")
                for wait_attempt in range(6):
                    await asyncio.sleep(5)
                    account = await self._request(
                        "GET",
                        f"/users/current/accounts/{self.account_id}",
                        base_url=self.PROVISIONING_URL,
                    )
                    conn_status = account.get("connectionStatus", "UNKNOWN")
                    print(f"[MetaTrader] Connection status check {wait_attempt + 1}/6: {conn_status}")
                    if conn_status == "CONNECTED":
                        break
                if conn_status != "CONNECTED":
                    print(
                        f"[MetaTrader] Account still '{conn_status}' after initial wait. "
                        "Refreshing routing and waiting longer..."
                    )
                    connected = await self._refresh_metaapi_routing(
                        wait_for_connected=True,
                        max_wait_checks=12,  # extra 60s for slow broker terminal handshakes
                        wait_seconds=5,
                    )
                    if not connected:
                        raise Exception(
                            "MetaApi account is deployed but terminal is not connected to broker yet "
                            "(connectionStatus!=CONNECTED). Verify MT login/password/server in MetaApi, "
                            "wait for CONNECTED state, then retry start."
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

    async def _ensure_connected_to_broker(self) -> bool:
        """Check if the MT terminal is connected to the broker before trading."""
        try:
            account = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}",
                base_url=self.PROVISIONING_URL,
            )
            conn_status = account.get("connectionStatus", "UNKNOWN")
            state = account.get("state", "UNKNOWN")

            # Log full diagnostic info for debugging
            print("[MetaTrader] === ACCOUNT DIAGNOSTICS ===")
            print(f"[MetaTrader] state={state} | connectionStatus={conn_status}")
            print(f"[MetaTrader] platform={account.get('platform')} | type={account.get('type')}")
            print(f"[MetaTrader] server={account.get('server')} | login={account.get('login')}")
            print(f"[MetaTrader] region={account.get('region')} | reliability={account.get('reliability')}")
            print(f"[MetaTrader] manualTrades={account.get('manualTrades')} | magic={account.get('magic')}")
            print(f"[MetaTrader] accessRights={account.get('accessRights')} | tradeMode={account.get('tradeMode')}")
            print("[MetaTrader] === END DIAGNOSTICS ===")

            if state != "DEPLOYED":
                print(f"[MetaTrader] Account not deployed (state={state}), deploying...")
                await self._request(
                    "POST",
                    f"/users/current/accounts/{self.account_id}/deploy",
                    base_url=self.PROVISIONING_URL,
                )
                await asyncio.sleep(5)

            if conn_status != "CONNECTED":
                print(f"[MetaTrader] Terminal not connected ({conn_status}), waiting...")
                for i in range(12):  # Wait up to 60 seconds
                    await asyncio.sleep(5)
                    account = await self._request(
                        "GET",
                        f"/users/current/accounts/{self.account_id}",
                        base_url=self.PROVISIONING_URL,
                    )
                    conn_status = account.get("connectionStatus", "UNKNOWN")
                    print(f"[MetaTrader] Connection wait {i+1}/12: {conn_status}")
                    if conn_status == "CONNECTED":
                        return True

                print(f"[MetaTrader] WARNING: Terminal still {conn_status} after waiting")
                return False

            return True
        except Exception as e:
            print(f"[MetaTrader] Error checking connection status: {e}")
            return False

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
    def supported_markets(self) -> list[str]:
        """List of supported market types."""
        return ["forex", "indices", "commodities", "metals", "futures"]

    async def get_account_info(self) -> AccountInfo:
        """Get account information with caching."""
        if not self._connected:
            await self.connect()

        cache_key = "account_info"

        # Check cache first
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Check if we're rate limited
        if self._is_rate_limited():
            # Return last known data if available, or raise error
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached account info")
                return self._cache[cache_key]["data"]
            raise RateLimitError("Rate limited and no cached data available")

        try:
            info = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/account-information",
            )

            # Calculate realized P&L today from deal history
            realized_today = Decimal("0")
            try:
                deals = await self.get_deals_history()
                for deal in deals:
                    profit = deal.get("profit", 0)
                    if profit and deal.get("type") in ("DEAL_TYPE_SELL", "DEAL_TYPE_BUY", "sell", "buy"):
                        realized_today += Decimal(str(profit))
                    # Also add swap and commission
                    realized_today += Decimal(str(deal.get("swap", 0)))
                    realized_today += Decimal(str(deal.get("commission", 0)))
            except Exception as e:
                print(f"[MetaTrader] Error calculating daily P&L: {e}")

            account_info = AccountInfo(
                account_id=self.account_id,
                balance=Decimal(str(info.get("balance", 0))),
                equity=Decimal(str(info.get("equity", 0))),
                margin_used=Decimal(str(info.get("margin", 0))),
                margin_available=Decimal(str(info.get("freeMargin", 0))),
                unrealized_pnl=Decimal(str(info.get("equity", 0) - info.get("balance", 0))),
                realized_pnl_today=realized_today,
                currency=info.get("currency", "USD"),
                leverage=info.get("leverage", 1),
            )

            # Cache the result
            self._set_cache(cache_key, account_info, self.ACCOUNT_INFO_CACHE_TTL)
            return account_info

        except RateLimitError:
            # Return stale cache if available
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached account info")
                return self._cache[cache_key]["data"]
            raise

    async def get_positions(self) -> list[Position]:
        """Get all open positions with caching."""
        if not self._connected:
            await self.connect()

        cache_key = "positions"

        # Check cache first
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Check if we're rate limited
        if self._is_rate_limited():
            # Return last known data if available
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached positions")
                return self._cache[cache_key]["data"]
            # Return empty list if no cache (better than failing)
            print("[MetaTrader] Rate limited and no cached positions, returning empty list")
            return []

        try:
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

            # Cache the result
            self._set_cache(cache_key, positions, self.POSITIONS_CACHE_TTL)
            return positions

        except RateLimitError:
            # Return stale cache if available
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached positions")
                return self._cache[cache_key]["data"]
            print("[MetaTrader] Rate limited and no cached positions, returning empty list")
            return []

    async def get_position(self, symbol: str) -> Position | None:
        """Get position for a specific symbol."""
        broker_symbol = self._resolve_symbol(symbol)
        positions = await self.get_positions()
        for pos in positions:
            # Compare with both original and broker symbol format
            if pos.symbol == broker_symbol or pos.symbol.upper() == broker_symbol.upper():
                return pos
        return None

    async def get_symbol_specification(self, symbol: str) -> dict[str, Any]:
        """Get symbol specification (fillingModes, volume limits, etc.)."""
        if not self._connected:
            await self.connect()

        lookup = self._symbol_lookup_key(symbol)
        cache_key = f"symbol_spec_{lookup}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        candidates = self._get_symbol_candidates(lookup) or [self._resolve_symbol(lookup)]
        for broker_symbol in candidates[:10]:
            try:
                spec = await self._get_symbol_specification_for_broker_symbol(broker_symbol)
                self._symbol_map[lookup] = broker_symbol
                self._set_cache(cache_key, spec, 300)  # Cache for 5 minutes
                return spec
            except Exception as e:
                print(f"[MetaTrader] Could not fetch symbol specification for {lookup} via {broker_symbol}: {e}")

        return {}

    def _normalize_volume(self, volume: float, spec: dict[str, Any]) -> float:
        """Normalize volume to broker's min/max/step constraints."""
        min_vol = spec.get("minVolume", 0.01)
        max_vol = spec.get("maxVolume", 100.0)
        vol_step = spec.get("volumeStep", 0.01)

        # Round to nearest volume step
        if vol_step > 0:
            volume = round(round(volume / vol_step) * vol_step, 8)

        # Clamp to min/max
        volume = max(min_vol, min(max_vol, volume))

        # Final round to avoid floating point issues
        # Determine decimal places from vol_step
        step_str = f"{vol_step:.8f}".rstrip('0')
        decimals = len(step_str.split('.')[-1]) if '.' in step_str else 0
        volume = round(volume, decimals)

        return volume

    async def place_order(self, order: OrderRequest) -> OrderResult:
        """Place a trading order."""
        if not self._connected:
            await self.connect()

        # Verify terminal is connected to broker before placing trade
        is_broker_connected = await self._ensure_connected_to_broker()
        if not is_broker_connected:
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message="Terminale MT non connesso al broker. Verificare le credenziali e lo stato dell'account MetaApi.",
            )

        # Fetch symbol specification and choose a tradable symbol variant (prefix/suffix aware)
        broker_symbol, spec, symbol_resolution_error = await self._resolve_symbol_for_order(
            order.symbol,
            order.side,
        )
        if symbol_resolution_error:
            print(f"[MetaTrader] {symbol_resolution_error}")
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=symbol_resolution_error,
            )

        if spec:
            print(f"[MetaTrader] Symbol spec for {broker_symbol}: "
                  f"fillingModes={spec.get('fillingModes')}, "
                  f"minVol={spec.get('minVolume')}, maxVol={spec.get('maxVolume')}, "
                  f"volStep={spec.get('volumeStep')}, "
                  f"executionMode={spec.get('executionMode')}, "
                  f"tradeMode={spec.get('tradeMode')}")

        # Check if trading is enabled for requested side on this symbol
        trade_mode = spec.get("tradeMode") if spec else self._broker_symbol_meta.get(broker_symbol, {}).get("tradeMode")
        if not self._is_trade_mode_compatible(trade_mode, order.side):
            error_msg = (
                f"Trading non consentito su {broker_symbol} per side={order.side.value} "
                f"(tradeMode={trade_mode})."
            )
            print(f"[MetaTrader] {error_msg}")
            return OrderResult(
                order_id="",
                symbol=order.symbol,
                side=order.side,
                order_type=order.order_type,
                status=OrderStatus.REJECTED,
                size=order.size,
                filled_size=Decimal("0"),
                error_message=error_msg,
            )

        # Normalize volume to broker constraints
        raw_volume = float(order.size)
        volume = self._normalize_volume(raw_volume, spec) if spec else raw_volume
        if volume != raw_volume:
            print(f"[MetaTrader] Volume adjusted: {raw_volume} → {volume} "
                  f"(min={spec.get('minVolume')}, max={spec.get('maxVolume')}, step={spec.get('volumeStep')})")

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

        # Build order payload
        payload = {
            "actionType": action_type,
            "symbol": broker_symbol,
            "volume": volume,
        }

        # Map symbol filling modes to order filling modes
        # Symbol spec returns: SYMBOL_FILLING_FOK, SYMBOL_FILLING_IOC
        # Trade request needs: ORDER_FILLING_FOK, ORDER_FILLING_IOC
        FILLING_MODE_MAP = {
            "SYMBOL_FILLING_FOK": "ORDER_FILLING_FOK",
            "SYMBOL_FILLING_IOC": "ORDER_FILLING_IOC",
            "SYMBOL_FILLING_RETURN": "ORDER_FILLING_RETURN",
        }

        # Add fillingModes from symbol specification (critical for forex)
        symbol_filling_modes = spec.get("fillingModes") if spec else None
        if symbol_filling_modes:
            # Convert SYMBOL_FILLING_* to ORDER_FILLING_*
            order_filling_modes = [
                FILLING_MODE_MAP.get(mode, mode) for mode in symbol_filling_modes
            ]
            payload["fillingModes"] = order_filling_modes
            print(f"[MetaTrader] Using symbol's fillingModes: {symbol_filling_modes} → {order_filling_modes}")

        # Add SL/TP
        if order.stop_loss:
            payload["stopLoss"] = float(order.stop_loss)
        if order.take_profit:
            payload["takeProfit"] = float(order.take_profit)

        # Add price for limit/stop orders
        if order.order_type in [OrderType.LIMIT, OrderType.STOP] and order.price:
            payload["openPrice"] = float(order.price)

        # Map known MT5 error stringCodes to human-readable messages
        MT5_ERROR_MESSAGES = {
            "TRADE_RETCODE_INVALID": "Richiesta non valida",
            "TRADE_RETCODE_INVALID_STOPS": "SL/TP non validi (troppo vicini al prezzo o livello non permesso dal broker)",
            "TRADE_RETCODE_INVALID_VOLUME": "Volume non valido (controlla lotto min/max/step del simbolo)",
            "TRADE_RETCODE_INVALID_PRICE": "Prezzo non valido",
            "TRADE_RETCODE_INVALID_FILL": "Tipo di riempimento non supportato",
            "TRADE_RETCODE_NO_MONEY": "Margine insufficiente per aprire la posizione",
            "TRADE_RETCODE_MARKET_CLOSED": "Mercato chiuso",
            "TRADE_RETCODE_TRADE_DISABLED": "Trading disabilitato sul simbolo",
            "TRADE_RETCODE_TOO_MANY_REQUESTS": "Troppe richieste",
            "TRADE_RETCODE_LIMIT_ORDERS": "Troppi ordini limite pendenti",
            "TRADE_RETCODE_LIMIT_VOLUME": "Volume cumulativo troppo alto",
            "TRADE_RETCODE_ORDER_LOCKED": "Ordine bloccato in elaborazione",
            "TRADE_RETCODE_FROZEN": "Ordine/posizione congelata",
            "TRADE_RETCODE_REJECT": "Richiesta rifiutata dal broker",
            "TRADE_RETCODE_CONNECTION": "Nessuna connessione al server di trading",
            "TRADE_RETCODE_TIMEOUT": "Timeout della richiesta",
            "TRADE_RETCODE_CANCEL": "Ordine cancellato",
            "TRADE_RETCODE_POSITION_CLOSED": "Posizione già chiusa",
            "TRADE_RETCODE_UNKNOWN": "Terminale MT disconnesso dal broker (numericCode=-1). Controllare connessione MetaApi.",
        }

        SUCCESS_CODES = {
            "TRADE_RETCODE_DONE",
            "TRADE_RETCODE_PLACED",
            "TRADE_RETCODE_DONE_PARTIAL",
            "ERR_NO_ERROR",
            "",
        }
        SUCCESS_NUMERIC = {10008, 10009, 10010}

        # Retry strategies: each attempt tries a different payload variation
        # Attempt 1: with symbol's fillingModes (from spec)
        # Attempt 2: without fillingModes (let MetaApi decide)
        # Attempt 3: with explicit FOK only
        RETRY_FILLING_OVERRIDES = [
            None,                           # Keep current fillingModes from spec
            "REMOVE",                       # Remove fillingModes entirely
            ["ORDER_FILLING_FOK"],          # Force FOK
            ["ORDER_FILLING_IOC"],          # Force IOC
        ]
        MAX_RETRIES = len(RETRY_FILLING_OVERRIDES)
        RETRYABLE_CODES = {"TRADE_RETCODE_UNKNOWN", "TRADE_RETCODE_INVALID_FILL", "TRADE_RETCODE_CONNECTION", "TRADE_RETCODE_TIMEOUT"}
        last_reject_reason = ""

        def _parse_trade_response(result_payload: dict[str, Any]) -> tuple[str, bool, str, Any, str, bool, bool]:
            order_id = str(result_payload.get("orderId", result_payload.get("positionId", "")))
            is_filled = bool(result_payload.get("positionId"))
            string_code = result_payload.get("stringCode", "")
            numeric_code = result_payload.get("numericCode")
            error_msg = result_payload.get("errorMessage", result_payload.get("message", ""))

            is_success_code = string_code in SUCCESS_CODES or (numeric_code in SUCCESS_NUMERIC if numeric_code else False)
            has_order = bool(order_id)

            # For MARKET orders: require positionId or explicit success code.
            if order.order_type == OrderType.MARKET and not is_filled and not is_success_code and has_order:
                print(
                    f"[MetaTrader] Market order has orderId={order_id} but no positionId "
                    f"and stringCode='{string_code}' - treating as rejection"
                )
                has_order = False

            accepted = is_filled or is_success_code or has_order
            return (
                order_id,
                is_filled,
                string_code,
                numeric_code,
                str(error_msg or ""),
                accepted,
                has_order,
            )

        for attempt in range(MAX_RETRIES):
            # Apply filling mode override for retries
            override = RETRY_FILLING_OVERRIDES[attempt]
            if override == "REMOVE":
                payload.pop("fillingModes", None)
            elif override is not None:
                payload["fillingModes"] = override

            try:
                filling_info = payload.get('fillingModes', 'default')
                print(f"[MetaTrader] Placing order (attempt {attempt + 1}/{MAX_RETRIES}, filling={filling_info}): {payload}")
                result = await self._request(
                    "POST",
                    f"/users/current/accounts/{self.account_id}/trade",
                    json=payload,
                )
                print(f"[MetaTrader] Order response: {result}")

                (
                    order_id,
                    is_filled,
                    string_code,
                    numeric_code,
                    error_msg,
                    accepted,
                    has_order,
                ) = _parse_trade_response(result)

                # Success path
                if accepted:
                    if has_order and not is_filled and string_code not in SUCCESS_CODES:
                        print(f"[MetaTrader] WARNING: Unknown stringCode '{string_code}' (numericCode={numeric_code}) but order exists - treating as success")

                    order_status = OrderStatus.FILLED if is_filled else (OrderStatus.PENDING if has_order else OrderStatus.REJECTED)
                    print(f"[MetaTrader] Order {order_status.value} | stringCode: {string_code} | orderId: {order_id}")

                    return OrderResult(
                        order_id=order_id,
                        symbol=order.symbol,
                        side=order.side,
                        order_type=order.order_type,
                        status=order_status,
                        size=order.size,
                        filled_size=Decimal(str(volume)),
                        price=order.price,
                        average_fill_price=Decimal(str(result.get("openPrice", 0))) if result.get("openPrice") else None,
                        commission=Decimal(str(result.get("commission", 0))),
                    )

                # Rejection - build error message
                known_error = MT5_ERROR_MESSAGES.get(string_code)
                if known_error:
                    reject_reason = f"{known_error} [{string_code}]"
                elif error_msg:
                    reject_reason = f"{error_msg} [{string_code or f'code={numeric_code}'}]"
                elif string_code:
                    reject_reason = f"Broker: {string_code} (numericCode={numeric_code})"
                else:
                    reject_reason = f"Risposta senza codice - full response: {result}"

                last_reject_reason = reject_reason

                invalid_stops_reject = self._is_invalid_stops_rejection(string_code, reject_reason)
                has_protection_in_payload = ("stopLoss" in payload) or ("takeProfit" in payload)
                if (
                    invalid_stops_reject
                    and order.order_type == OrderType.MARKET
                    and has_protection_in_payload
                ):
                    fallback_payload = dict(payload)
                    fallback_payload.pop("stopLoss", None)
                    fallback_payload.pop("takeProfit", None)

                    print(
                        f"[MetaTrader] INVALID_STOPS on {broker_symbol}. "
                        "Retrying market order without SL/TP and applying protection after fill..."
                    )
                    try:
                        fallback_result = await self._request(
                            "POST",
                            f"/users/current/accounts/{self.account_id}/trade",
                            json=fallback_payload,
                        )
                        print(f"[MetaTrader] Fallback order response (no SL/TP): {fallback_result}")

                        (
                            fb_order_id,
                            fb_is_filled,
                            fb_string_code,
                            fb_numeric_code,
                            fb_error_msg,
                            fb_accepted,
                            fb_has_order,
                        ) = _parse_trade_response(fallback_result)

                        if fb_accepted:
                            order_status = OrderStatus.FILLED if fb_is_filled else (OrderStatus.PENDING if fb_has_order else OrderStatus.REJECTED)
                            protection_warning = None
                            requested_sl = float(order.stop_loss) if order.stop_loss is not None else None
                            requested_tp = float(order.take_profit) if order.take_profit is not None else None

                            if fb_is_filled and (requested_sl is not None or requested_tp is not None):
                                position_id = str(fallback_result.get("positionId", "") or "")
                                if position_id:
                                    protected = await self._modify_position_by_id(
                                        position_id=position_id,
                                        stop_loss=requested_sl,
                                        take_profit=requested_tp,
                                    )
                                    if not protected:
                                        protection_warning = (
                                            "PROTECTION_NOT_SET: posizione aperta senza SL/TP; "
                                            "impostazione post-fill fallita"
                                        )
                                else:
                                    protection_warning = (
                                        "PROTECTION_NOT_SET: posizione aperta ma positionId assente, "
                                        "impossibile applicare SL/TP post-fill"
                                    )

                            print(
                                f"[MetaTrader] Fallback order {order_status.value} | "
                                f"stringCode: {fb_string_code} | orderId: {fb_order_id}"
                            )
                            return OrderResult(
                                order_id=fb_order_id,
                                symbol=order.symbol,
                                side=order.side,
                                order_type=order.order_type,
                                status=order_status,
                                size=order.size,
                                filled_size=Decimal(str(volume)),
                                price=order.price,
                                average_fill_price=Decimal(str(fallback_result.get("openPrice", 0))) if fallback_result.get("openPrice") else None,
                                commission=Decimal(str(fallback_result.get("commission", 0))),
                                error_message=protection_warning,
                            )

                        fb_known_error = MT5_ERROR_MESSAGES.get(fb_string_code)
                        if fb_known_error:
                            fb_reject_reason = f"{fb_known_error} [{fb_string_code}]"
                        elif fb_error_msg:
                            fb_reject_reason = f"{fb_error_msg} [{fb_string_code or f'code={fb_numeric_code}'}]"
                        elif fb_string_code:
                            fb_reject_reason = f"Broker: {fb_string_code} (numericCode={fb_numeric_code})"
                        else:
                            fb_reject_reason = f"Fallback senza SL/TP rifiutato - full response: {fallback_result}"

                        last_reject_reason = (
                            f"{reject_reason} | fallback senza SL/TP: {fb_reject_reason}"
                        )
                        if fb_string_code in RETRYABLE_CODES and attempt < MAX_RETRIES - 1:
                            wait_secs = 2
                            print(
                                f"[MetaTrader] Retryable fallback error ({fb_string_code}), "
                                f"trying different filling in {wait_secs}s..."
                            )
                            await asyncio.sleep(wait_secs)
                            continue
                    except Exception as fallback_exc:
                        print(f"[MetaTrader] Fallback order without SL/TP failed: {fallback_exc}")

                # If retryable and not last attempt, wait and retry with different filling
                if string_code in RETRYABLE_CODES and attempt < MAX_RETRIES - 1:
                    wait_secs = 2
                    print(f"[MetaTrader] Retryable error ({string_code}), trying different filling in {wait_secs}s...")
                    await asyncio.sleep(wait_secs)
                    continue

                # Non-retryable or last attempt
                print(f"[MetaTrader] Order REJECTED - {reject_reason}")
                return OrderResult(
                    order_id=order_id if order_id else "",
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.REJECTED,
                    size=order.size,
                    filled_size=Decimal("0"),
                    error_message=str(reject_reason),
                )

            except Exception as e:
                import traceback
                print(f"[MetaTrader] Order EXCEPTION (attempt {attempt + 1}): {str(e)}")
                print(f"[MetaTrader] Traceback: {traceback.format_exc()}")

                if attempt < MAX_RETRIES - 1:
                    wait_secs = (attempt + 1) * 3
                    print(f"[MetaTrader] Retrying in {wait_secs}s...")
                    await asyncio.sleep(wait_secs)
                    continue

                return OrderResult(
                    order_id="",
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    status=OrderStatus.REJECTED,
                    size=order.size,
                    filled_size=Decimal("0"),
                    error_message=f"Errore connessione broker: {str(e)}",
                )

        # Should not reach here, but just in case
        print(f"[MetaTrader] All retries exhausted. Last: {last_reject_reason}")
        return OrderResult(
            order_id="",
            symbol=order.symbol,
            side=order.side,
            order_type=order.order_type,
            status=OrderStatus.REJECTED,
            size=order.size,
            filled_size=Decimal("0"),
            error_message=f"Tutti i tentativi esauriti. Ultimo errore: {last_reject_reason}",
        )

    async def close_position(
        self,
        symbol: str,
        size: Decimal | None = None
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
        stop_loss: Decimal | None = None,
        take_profit: Decimal | None = None,
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

    async def get_open_orders(self, symbol: str | None = None) -> list[OrderResult]:
        """Get all open/pending orders with caching."""
        if not self._connected:
            await self.connect()

        cache_key = "orders"

        # Check cache first (only for unfiltered requests)
        if symbol is None:
            cached = self._get_cache(cache_key)
            if cached is not None:
                return cached

        # Check if we're rate limited
        if self._is_rate_limited():
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached orders")
                all_orders = self._cache[cache_key]["data"]
                if symbol:
                    broker_symbol = self._resolve_symbol(symbol)
                    return [o for o in all_orders if o.symbol.upper() == broker_symbol.upper()]
                return all_orders
            return []

        try:
            orders_data = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/orders",
            )

            orders = []
            for order in orders_data:
                order_symbol = order.get("symbol", "")

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

            # Cache the full result
            self._set_cache(cache_key, orders, self.ORDERS_CACHE_TTL)

            # Filter by symbol if specified
            if symbol:
                broker_symbol = self._resolve_symbol(symbol)
                return [o for o in orders if o.symbol.upper() == broker_symbol.upper()]

            return orders

        except RateLimitError:
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached orders")
                all_orders = self._cache[cache_key]["data"]
                if symbol:
                    broker_symbol = self._resolve_symbol(symbol)
                    return [o for o in all_orders if o.symbol.upper() == broker_symbol.upper()]
                return all_orders
            return []

    async def get_order(self, order_id: str) -> OrderResult | None:
        """Get order by ID."""
        if not self._connected:
            await self.connect()

        # Get all pending orders and search for the one with matching ID
        orders = await self.get_open_orders()
        for order in orders:
            if order.order_id == order_id:
                return order
        return None

    DEALS_CACHE_TTL = 60  # Cache deals for 60 seconds

    async def get_deals_history(self, start_time: str | None = None) -> list[dict]:
        """
        Get closed deal history from MetaApi.

        Args:
            start_time: ISO 8601 start time. Defaults to start of today (UTC).

        Returns:
            List of deal dictionaries with profit, symbol, type, etc.
        """
        if not self._connected:
            await self.connect()

        cache_key = f"deals_{start_time or 'today'}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        if self._is_rate_limited():
            if cache_key in self._cache:
                return self._cache[cache_key]["data"]
            return []

        try:
            if not start_time:
                from datetime import datetime as dt
                today = dt.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                start_time = today.isoformat()

            result = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/history-deals/time/{start_time}/0",
            )

            deals = result if isinstance(result, list) else result.get("deals", result.get("items", []))
            self._set_cache(cache_key, deals, self.DEALS_CACHE_TTL)
            return deals

        except Exception as e:
            print(f"[MetaTrader] Error fetching deal history: {e}")
            if cache_key in self._cache:
                return self._cache[cache_key]["data"]
            return []

    def get_supported_symbols(self) -> list[str]:
        """Get list of internal symbols that have been successfully mapped to broker symbols."""
        supported = []
        for our_symbol, broker_sym in self._symbol_map.items():
            # Check if this was a real mapping (not just fallback)
            if broker_sym in self._broker_symbols:
                supported.append(our_symbol)
        return supported

    async def get_prices(self, symbols: list[str]) -> dict[str, Tick]:
        """Get current prices for multiple symbols with rate-limit-safe batching."""
        if not self._connected:
            await self.connect()

        prices = {}
        errors = []

        # Process in batches of 5 with small delay to avoid rate limiting
        batch_size = 5
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i + batch_size]
            for symbol in batch:
                try:
                    tick = await self.get_current_price(symbol)
                    prices[symbol] = tick
                except Exception as e:
                    errors.append(f"{symbol}: {str(e)[:50]}")

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.3)

        # Log errors for first few symbols only (to avoid spam)
        if errors and len(prices) == 0:
            print(f"[MetaTrader] get_prices failed for ALL {len(errors)} symbols!")
            print(f"[MetaTrader] First 3 errors: {errors[:3]}")
        elif errors:
            print(f"[MetaTrader] get_prices: {len(prices)} OK, {len(errors)} failed")

        return prices

    async def get_instruments(self) -> list[Instrument]:
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
        """Get current bid/ask price for symbol with caching."""
        if not self._connected:
            await self.connect()

        if not self._broker_symbols:
            await self._ensure_symbol_inventory(force_reload=True)

        lookup = self._symbol_lookup_key(symbol)
        broker_symbol = self._resolve_symbol(lookup)
        cache_key = f"price_{symbol}"

        # Check cache first
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        # Check if we're rate limited
        if self._is_rate_limited():
            if cache_key in self._cache:
                print(f"[MetaTrader] Rate limited, returning stale cached price for {symbol}")
                return self._cache[cache_key]["data"]
            raise RateLimitError(f"Rate limited and no cached price for {symbol}")

        try:
            candidates = self._get_symbol_candidates(lookup) or [broker_symbol]
            if broker_symbol in candidates:
                candidates = [broker_symbol, *[c for c in candidates if c != broker_symbol]]
            else:
                candidates = [broker_symbol, *candidates]

            last_error: Exception | None = None
            skipped_or_rejected: list[str] = []
            attempted_candidates: list[str] = []
            request_attempts = 0
            for candidate in candidates[:12]:
                attempted_candidates.append(candidate)
                if self._is_forex_lookup(lookup) and not self._is_forex_candidate_compatible(lookup, candidate):
                    skipped_or_rejected.append(f"{candidate}(FOREX_MISMATCH)")
                    continue

                if self._is_forex_lookup(lookup):
                    meta = self._broker_symbol_meta.get(candidate, {})
                    if meta and not self._is_forex_spec_compatible(lookup, meta):
                        skipped_or_rejected.append(f"{candidate}(FOREX_SPEC_MISMATCH)")
                        continue

                    # If symbol list metadata does not expose currency fields, verify once via specification cache.
                    has_currency_hint = bool(
                        self._extract_spec_currency(meta, ("currencyBase", "baseCurrency", "currencyBaseCode"))
                        or self._extract_spec_currency(meta, ("currencyProfit", "quoteCurrency", "currencyQuote"))
                    )
                    if not has_currency_hint:
                        try:
                            spec = await self._get_symbol_specification_for_broker_symbol(candidate)
                            if not self._is_forex_spec_compatible(lookup, spec):
                                skipped_or_rejected.append(f"{candidate}(FOREX_SPEC_MISMATCH)")
                                continue
                        except Exception:
                            # Missing specification is handled by price retrieval path.
                            pass

                try:
                    request_attempts += 1
                    price_data = await self._request(
                        "GET",
                        f"/users/current/accounts/{self.account_id}/symbols/{self._encode_symbol_path(candidate)}/current-price",
                    )

                    try:
                        bid = float(price_data.get("bid", 0) or 0)
                        ask = float(price_data.get("ask", 0) or 0)
                    except Exception:
                        bid = 0.0
                        ask = 0.0

                    if not self._is_plausible_price_for_lookup(lookup, bid, ask):
                        skipped_or_rejected.append(
                            f"{candidate}(IMPLAUSIBLE_PRICE bid={bid:.6g} ask={ask:.6g})"
                        )
                        continue

                    if candidate != broker_symbol:
                        print(f"[MetaTrader] Price fallback resolved {lookup} -> {candidate}")
                        self._symbol_map[lookup] = candidate

                    tick = Tick(
                        symbol=symbol,  # Return original symbol for consistency
                        bid=Decimal(str(price_data.get("bid", 0))),
                        ask=Decimal(str(price_data.get("ask", 0))),
                        timestamp=datetime.now(),
                    )

                    # Cache the result
                    self._set_cache(cache_key, tick, self.PRICES_CACHE_TTL)
                    return tick
                except Exception as exc:
                    last_error = exc
                    if request_attempts == 1 and not self._is_symbol_lookup_error(str(exc)):
                        # If first candidate failed for non-symbol reasons, don't spam alternate tries.
                        break

            if skipped_or_rejected and last_error is None:
                detail = ", ".join(skipped_or_rejected[:8])
                if len(skipped_or_rejected) > 8:
                    detail += f" (+{len(skipped_or_rejected) - 8} altre)"
                raise Exception(
                    f"Nessuna variante prezzo valida per {lookup}. "
                    f"Varianti scartate: {detail}"
                )

            if last_error:
                detail = f"{type(last_error).__name__}: {last_error}"
                tried = ", ".join(attempted_candidates[:12]) or "<none>"
                related = self._match_broker_symbols_by_lookup(lookup, limit=8)
                related_text = ", ".join(related) if related else "<none>"
                raise Exception(
                    f"{detail} | candidates tried: {tried} | broker related symbols: {related_text}"
                )
            raise Exception("No symbol candidates available for pricing")

        except RateLimitError:
            if cache_key in self._cache:
                print(f"[MetaTrader] Rate limited, returning stale cached price for {symbol}")
                return self._cache[cache_key]["data"]
            raise
        except Exception as e:
            # For other errors, still try to return cached data
            if cache_key in self._cache:
                print(f"[MetaTrader] Error getting price for {symbol}, returning cached: {e}")
                return self._cache[cache_key]["data"]
            raise Exception(f"Failed to get price for {symbol}: {e}")

    async def stream_prices(
        self,
        symbols: list[str],
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
            async def safe_get_price(symbol: str) -> Tick | None:
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

    async def get_symbols(self) -> list[dict[str, Any]]:
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
    ) -> list[dict[str, Any]]:
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
            f"/users/current/accounts/{self.account_id}/historical-market-data/symbols/{self._encode_symbol_path(broker_symbol)}/timeframes/{mt_timeframe}/candles",
            params={"limit": count},
        )

        return candles
