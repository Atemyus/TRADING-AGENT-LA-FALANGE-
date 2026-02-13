"""Trading engine module."""

from .base_broker import (
    AccountInfo,
    BaseBroker,
    Candle,
    Instrument,
    OrderRequest,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    PositionSide,
    Tick,
    TimeInForce,
)
from .broker_factory import BrokerFactory, get_broker
from .ig_broker import IGBroker
from .alpaca_broker import AlpacaBroker
from .metatrader_bridge_broker import MetaTraderBridgeBroker
from .oanda_broker import OANDABroker
from .platform_rest_broker import CTraderBroker, DXTradeBroker, MatchTraderBroker
from .risk_manager import RiskManager, risk_manager

__all__ = [
    # Base broker
    "BaseBroker",
    "AccountInfo",
    "Position",
    "OrderRequest",
    "OrderResult",
    "OrderSide",
    "OrderType",
    "OrderStatus",
    "PositionSide",
    "TimeInForce",
    "Tick",
    "Candle",
    "Instrument",
    # Risk manager
    "RiskManager",
    "risk_manager",
    # Broker implementations
    "OANDABroker",
    "IGBroker",
    "AlpacaBroker",
    "MetaTraderBridgeBroker",
    "CTraderBroker",
    "DXTradeBroker",
    "MatchTraderBroker",
    "BrokerFactory",
    "get_broker",
]
