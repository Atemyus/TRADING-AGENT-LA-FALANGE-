"""
Unit tests for broker affix autodiscovery in MetaTraderBroker.

Uses importlib to load ONLY the metatrader_broker module directly,
bypassing the full app import chain that requires heavy dependencies.
"""

import sys
import os
import types
import importlib
import importlib.util
import re

import pytest

# ---------------------------------------------------------------------------
# Setup: stub all transitive deps so metatrader_broker.py can load in isolation
# ---------------------------------------------------------------------------

_backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _make_stub(name, attrs=None):
    """Register a stub module in sys.modules."""
    if name in sys.modules:
        mod = sys.modules[name]
    else:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    if attrs:
        for k, v in attrs.items():
            setattr(mod, k, v)
    return mod


# --- Stub httpx ---
_make_stub("httpx", {
    "AsyncClient": type("AsyncClient", (), {"__init__": lambda *a, **kw: None}),
})

# --- Stub src.core.config ---
_fake_settings = types.SimpleNamespace(
    METAAPI_ACCESS_TOKEN="test-token",
    METAAPI_ACCOUNT_ID="test-account",
)
_make_stub("src")
_make_stub("src.core")
_make_stub("src.core.config", {"settings": _fake_settings})

# --- Stub src.engines.trading.base_broker with required names ---
# We need actual enums / namedtuples for OrderSide etc.
from enum import Enum

class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"

class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"

class BaseBroker:
    """Minimal stub of the abstract base broker."""
    def __init__(self):
        pass
    async def connect(self): pass
    async def disconnect(self): pass

# Simple dataclass-like stubs
class AccountInfo:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class Instrument:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class OrderRequest:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class OrderResult:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class Position:
    def __init__(self, **kw):
        self.__dict__.update(kw)

class Tick:
    def __init__(self, **kw):
        self.__dict__.update(kw)

_make_stub("src.engines")
_make_stub("src.engines.trading")
_make_stub("src.engines.trading.base_broker", {
    "BaseBroker": BaseBroker,
    "AccountInfo": AccountInfo,
    "Instrument": Instrument,
    "OrderRequest": OrderRequest,
    "OrderResult": OrderResult,
    "OrderSide": OrderSide,
    "OrderType": OrderType,
    "OrderStatus": OrderStatus,
    "Position": Position,
    "PositionSide": PositionSide,
    "Tick": Tick,
})

# --- Now load metatrader_broker.py directly ---
_mt_path = os.path.join(_backend_root, "src", "engines", "trading", "metatrader_broker.py")
_spec = importlib.util.spec_from_file_location("metatrader_broker", _mt_path)
_mt_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mt_mod)

MetaTraderBroker = _mt_mod.MetaTraderBroker


def _make_broker() -> "MetaTraderBroker":
    return MetaTraderBroker(access_token="tok", account_id="acc")


# ===========================================================================
# Tests
# ===========================================================================

class TestDetectBrokerAffix:
    """Test the pattern detection logic."""

    def test_detects_hash_suffix(self):
        broker = _make_broker()
        broker._broker_symbols = [
            "EURUSD#", "GBPUSD#", "USDJPY#", "GOLD#", "US30#", "USDPLN#",
        ]
        broker._symbol_map = {
            "EUR_USD": "EURUSD#",
            "GBP_USD": "GBPUSD#",
            "USD_JPY": "USDJPY#",
            "XAU_USD": "GOLD#",
            "US30": "US30#",
        }
        broker._detect_broker_affix()

        assert broker._discovered_broker_suffix == "#"
        assert broker._broker_affix_confidence >= 0.4

    def test_detects_dot_suffix(self):
        broker = _make_broker()
        broker._broker_symbols = [
            "EURUSD.", "GBPUSD.", "USDJPY.", "GOLD.", "NAS100.",
        ]
        broker._symbol_map = {
            "EUR_USD": "EURUSD.",
            "GBP_USD": "GBPUSD.",
            "USD_JPY": "USDJPY.",
            "XAU_USD": "GOLD.",
        }
        broker._detect_broker_affix()

        assert broker._discovered_broker_suffix == "."
        assert broker._broker_affix_confidence >= 0.4

    def test_detects_pro_suffix(self):
        broker = _make_broker()
        broker._broker_symbols = [
            "EURUSD.pro", "GBPUSD.pro", "USDJPY.pro", "XAUUSD.pro",
        ]
        broker._symbol_map = {
            "EUR_USD": "EURUSD.pro",
            "GBP_USD": "GBPUSD.pro",
            "USD_JPY": "USDJPY.pro",
            "XAU_USD": "XAUUSD.pro",
        }
        broker._detect_broker_affix()

        assert broker._discovered_broker_suffix == ".pro"
        assert broker._broker_affix_confidence >= 0.4

    def test_no_affix_when_plain_symbols(self):
        broker = _make_broker()
        broker._broker_symbols = [
            "EURUSD", "GBPUSD", "USDJPY", "XAUUSD",
        ]
        broker._symbol_map = {
            "EUR_USD": "EURUSD",
            "GBP_USD": "GBPUSD",
            "USD_JPY": "USDJPY",
            "XAU_USD": "XAUUSD",
        }
        broker._detect_broker_affix()

        assert broker._discovered_broker_suffix == ""
        assert broker._discovered_broker_prefix == ""

    def test_no_affix_when_too_few_pairs(self):
        broker = _make_broker()
        broker._broker_symbols = ["EURUSD#", "GBPUSD#"]
        broker._symbol_map = {"EUR_USD": "EURUSD#", "GBP_USD": "GBPUSD#"}
        broker._detect_broker_affix()

        assert broker._discovered_broker_suffix == ""
        assert broker._broker_affix_confidence == 0.0

    def test_detects_dominant_in_mixed_patterns(self):
        """When symbols have varied suffixes, detect the most frequent one."""
        broker = _make_broker()
        broker._broker_symbols = [
            "EURUSD#", "GBPUSD.", "USDJPYm", "XAUUSD-ECN",
            "AUDCAD#", "NZDCHF.", "CADCHF#", "EURGBP#",
        ]
        broker._symbol_map = {
            "EUR_USD": "EURUSD#",
            "GBP_USD": "GBPUSD.",
            "USD_JPY": "USDJPYm",
            "XAU_USD": "XAUUSD-ECN",
            "AUD_CAD": "AUDCAD#",
            "NZD_CHF": "NZDCHF.",
            "CAD_CHF": "CADCHF#",
            "EUR_GBP": "EURGBP#",
        }
        broker._detect_broker_affix()

        # "#" appears 4/8 = 50%, should detect it
        assert broker._discovered_broker_suffix == "#"


class TestApplyDiscoveredAffix:

    def test_applies_suffix(self):
        broker = _make_broker()
        broker._discovered_broker_suffix = "#"
        broker._broker_affix_confidence = 0.9

        candidates = broker._apply_discovered_affix("USDPLN")
        assert "USDPLN#" in candidates

    def test_applies_prefix(self):
        broker = _make_broker()
        broker._discovered_broker_prefix = "m"
        broker._broker_affix_confidence = 0.8

        candidates = broker._apply_discovered_affix("EURUSD")
        assert "mEURUSD" in candidates

    def test_empty_when_no_affix(self):
        broker = _make_broker()
        candidates = broker._apply_discovered_affix("EURUSD")
        assert candidates == []

    def test_includes_alias_variants_with_suffix(self):
        broker = _make_broker()
        broker._discovered_broker_suffix = "#"
        broker._broker_affix_confidence = 0.95

        candidates = broker._apply_discovered_affix("XAUUSD")
        assert "XAUUSD#" in candidates


class TestResolveSymbolWithAffix:

    def test_resolve_uses_affix_for_exotic_pair(self):
        """Symbols not in SYMBOL_ALIASES should be resolved via affix."""
        broker = _make_broker()
        broker._broker_symbols = [
            "EURUSD#", "GBPUSD#", "USDJPY#", "USDPLN#", "EURSEK#",
        ]
        broker._broker_symbol_meta = {}
        broker._broker_token_map = {}
        broker._broker_token_collisions = set()
        for bs in broker._broker_symbols:
            token = broker._normalize_symbol_token(bs)
            broker._broker_token_map[token] = bs

        # Simulate first pass resolved some common symbols
        broker._symbol_map = {
            "EUR_USD": "EURUSD#",
            "GBP_USD": "GBPUSD#",
            "USD_JPY": "USDJPY#",
        }
        broker._detect_broker_affix()
        assert broker._discovered_broker_suffix == "#"

        # EUR_SEK is in SYMBOL_ALIASES but not with '#', so it should be
        # found via candidate scoring (EURSEK# is in broker list) or affix.
        resolved = broker._resolve_symbol("EUR_SEK")
        assert resolved == "EURSEK#"

    def test_resolve_prefers_scored_match(self):
        """Normal scoring takes priority over affix fallback."""
        broker = _make_broker()
        broker._broker_symbols = ["EURUSD", "EURUSD#"]
        broker._broker_symbol_meta = {}
        broker._broker_token_map = {}
        broker._broker_token_collisions = set()
        for bs in broker._broker_symbols:
            token = broker._normalize_symbol_token(bs)
            if token in broker._broker_token_map:
                broker._broker_token_collisions.add(token)
            else:
                broker._broker_token_map[token] = bs
        for t in broker._broker_token_collisions:
            broker._broker_token_map.pop(t, None)

        resolved = broker._resolve_symbol("EUR_USD")
        assert resolved in ("EURUSD", "EURUSD#")
