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
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, AsyncIterator, Dict, List, Optional
import time

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

    # Cache TTLs (in seconds)
    ACCOUNT_INFO_CACHE_TTL = 30  # Cache account info for 30 seconds
    POSITIONS_CACHE_TTL = 15  # Cache positions for 15 seconds
    PRICES_CACHE_TTL = 2  # Cache prices for 2 seconds
    ORDERS_CACHE_TTL = 10  # Cache orders for 10 seconds

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

        # Cache for API responses to avoid rate limiting
        self._cache: Dict[str, Dict[str, Any]] = {}  # key -> {"data": ..., "expires": timestamp}
        self._rate_limit_until: Optional[float] = None  # Timestamp until which we should not make API calls
        self._rate_limit_endpoint: Optional[str] = None  # Which endpoint is rate limited

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

    def _get_cache(self, key: str) -> Optional[Any]:
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

    async def _request(
        self,
        method: str,
        endpoint: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
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

            # Check known aliases (exact match)
            aliases = self.SYMBOL_ALIASES.get(symbol, [])
            for alias in aliases:
                for broker_sym in self._broker_symbols:
                    if broker_sym.upper() == alias.upper():
                        self._symbol_map[symbol] = broker_sym
                        return broker_sym

            # Check aliases with suffix patterns (e.g., "US30" matches "US30.stp", "US30m", etc.)
            for alias in aliases:
                for broker_sym in self._broker_symbols:
                    broker_upper = broker_sym.upper()
                    alias_upper = alias.upper()
                    # Match if broker symbol starts with alias or alias starts with broker symbol
                    if broker_upper.startswith(alias_upper) or alias_upper.startswith(broker_upper):
                        self._symbol_map[symbol] = broker_sym
                        return broker_sym

            # Fuzzy match - broker symbol starts with base symbol
            for broker_sym in self._broker_symbols:
                if broker_sym.upper().startswith(base_symbol.upper()):
                    self._symbol_map[symbol] = broker_sym
                    return broker_sym

            # Reverse fuzzy match - base symbol starts with broker symbol
            for broker_sym in self._broker_symbols:
                if base_symbol.upper().startswith(broker_sym.upper()):
                    self._symbol_map[symbol] = broker_sym
                    return broker_sym

            # Check if any alias is contained in broker symbol (for patterns like "[US30]" or ".US30")
            for alias in aliases:
                for broker_sym in self._broker_symbols:
                    # Strip common prefixes/suffixes and check
                    clean_broker = broker_sym.strip('[]._-').upper()
                    if clean_broker == alias.upper():
                        self._symbol_map[symbol] = broker_sym
                        return broker_sym

            # Log that we couldn't find a match (only once per symbol)
            if symbol not in self._symbol_map:
                print(f"[MetaTrader] WARNING: Could not resolve symbol '{symbol}' to broker format")
                print(f"[MetaTrader] Tried aliases: {aliases[:5]}...")
                # Cache the fallback to avoid repeated logs
                fallback = symbol.replace('_', '')
                self._symbol_map[symbol] = fallback
                return fallback

        # Fallback: return without underscore
        return symbol.replace('_', '')

    async def _build_symbol_map(self) -> None:
        """Build symbol mapping from broker's available symbols."""
        try:
            symbols = await self.get_symbols()
            self._broker_symbols = [s.get('symbol', s) if isinstance(s, dict) else s for s in symbols]

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

            account_info = AccountInfo(
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

            # Cache the result
            self._set_cache(cache_key, account_info, self.ACCOUNT_INFO_CACHE_TTL)
            return account_info

        except RateLimitError:
            # Return stale cache if available
            if cache_key in self._cache:
                print("[MetaTrader] Rate limited, returning stale cached account info")
                return self._cache[cache_key]["data"]
            raise

    async def get_positions(self) -> List[Position]:
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
        """Get current bid/ask price for symbol with caching."""
        if not self._connected:
            await self.connect()

        broker_symbol = self._resolve_symbol(symbol)
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
            price_data = await self._request(
                "GET",
                f"/users/current/accounts/{self.account_id}/symbols/{broker_symbol}/current-price",
            )

            tick = Tick(
                symbol=symbol,  # Return original symbol for consistency
                bid=Decimal(str(price_data.get("bid", 0))),
                ask=Decimal(str(price_data.get("ask", 0))),
                timestamp=datetime.now(),
            )

            # Cache the result
            self._set_cache(cache_key, tick, self.PRICES_CACHE_TTL)
            return tick

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
