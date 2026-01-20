"""
Broker Factory

Factory for creating broker instances based on configuration.
Supports multiple brokers: OANDA, MetaTrader, IG, Interactive Brokers, Alpaca.
"""

from typing import Optional

from src.core.config import settings
from src.engines.trading.base_broker import BaseBroker
from src.engines.trading.oanda_broker import OANDABroker
from src.engines.trading.metatrader_broker import MetaTraderBroker


class NoBrokerConfiguredError(Exception):
    """Raised when no broker is configured or credentials are missing."""
    pass


class BrokerFactory:
    """
    Factory for creating broker instances.

    Usage:
        broker = BrokerFactory.create("oanda")
        await broker.connect()
    """

    _instances: dict = {}

    @classmethod
    def is_configured(cls, broker_type: Optional[str] = None) -> bool:
        """Check if a broker is properly configured with credentials."""
        broker_type = (broker_type or settings.BROKER_TYPE).lower()

        if broker_type == "oanda":
            return bool(settings.OANDA_API_KEY and settings.OANDA_ACCOUNT_ID)
        elif broker_type in ("metatrader", "mt4", "mt5"):
            token = getattr(settings, 'METAAPI_ACCESS_TOKEN', None)
            account = getattr(settings, 'METAAPI_ACCOUNT_ID', None)
            return bool(token and account)
        elif broker_type == "none":
            return False
        else:
            return False

    @classmethod
    def create(
        cls,
        broker_type: Optional[str] = None,
        **kwargs,
    ) -> BaseBroker:
        """
        Create a broker instance.

        Args:
            broker_type: Type of broker (oanda, metatrader, ig, ib, alpaca)
                        If not specified, uses BROKER_TYPE from settings
            **kwargs: Additional arguments passed to broker constructor

        Returns:
            BaseBroker instance

        Raises:
            NoBrokerConfiguredError: If broker credentials are not configured
            ValueError: If broker type is not supported
        """
        broker_type = (broker_type or settings.BROKER_TYPE).lower()

        # Check if broker type is "none" or not configured
        if broker_type == "none":
            raise NoBrokerConfiguredError("No broker configured. Configure broker in Settings.")

        if broker_type == "oanda":
            api_key = kwargs.get("api_key", settings.OANDA_API_KEY)
            account_id = kwargs.get("account_id", settings.OANDA_ACCOUNT_ID)

            if not api_key or not account_id:
                raise NoBrokerConfiguredError(
                    "OANDA broker requires API key and account ID. Configure in Settings."
                )

            return OANDABroker(
                api_key=api_key,
                account_id=account_id,
                environment=kwargs.get("environment", settings.OANDA_ENVIRONMENT),
            )

        elif broker_type in ("metatrader", "mt4", "mt5"):
            token = kwargs.get("access_token", getattr(settings, 'METAAPI_ACCESS_TOKEN', None))
            account = kwargs.get("account_id", getattr(settings, 'METAAPI_ACCOUNT_ID', None))

            if not token or not account:
                raise NoBrokerConfiguredError(
                    "MetaTrader broker requires MetaApi token and account ID. Configure in Settings."
                )

            return MetaTraderBroker(
                access_token=token,
                account_id=account,
            )

        elif broker_type == "ig":
            raise NotImplementedError("IG broker not yet implemented")

        elif broker_type in ("ib", "interactive_brokers"):
            raise NotImplementedError("Interactive Brokers not yet implemented")

        elif broker_type == "alpaca":
            raise NotImplementedError("Alpaca broker not yet implemented")

        else:
            raise NoBrokerConfiguredError(f"Unknown broker type: {broker_type}. Configure in Settings.")

    @classmethod
    async def get_instance(
        cls,
        broker_type: Optional[str] = None,
        **kwargs,
    ) -> BaseBroker:
        """
        Get a connected broker instance (singleton per broker type).

        Args:
            broker_type: Type of broker
            **kwargs: Additional arguments

        Returns:
            Connected BaseBroker instance

        Raises:
            NoBrokerConfiguredError: If broker is not configured
        """
        broker_type = (broker_type or settings.BROKER_TYPE).lower()

        if broker_type not in cls._instances:
            broker = cls.create(broker_type, **kwargs)
            await broker.connect()
            cls._instances[broker_type] = broker

        return cls._instances[broker_type]

    @classmethod
    async def close_all(cls) -> None:
        """Close all broker connections."""
        for broker in cls._instances.values():
            await broker.disconnect()
        cls._instances.clear()


# Convenience function
async def get_broker(broker_type: Optional[str] = None) -> BaseBroker:
    """Get the default broker instance."""
    return await BrokerFactory.get_instance(broker_type)
