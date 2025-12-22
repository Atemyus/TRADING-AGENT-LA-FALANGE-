"""
Broker Factory

Factory for creating broker instances based on configuration.
Supports multiple brokers: OANDA, IG, Interactive Brokers, Alpaca.
"""

from typing import Optional

from src.core.config import settings
from src.engines.trading.base_broker import BaseBroker
from src.engines.trading.oanda_broker import OANDABroker


class BrokerFactory:
    """
    Factory for creating broker instances.

    Usage:
        broker = BrokerFactory.create("oanda")
        await broker.connect()
    """

    _instances: dict = {}

    @classmethod
    def create(
        cls,
        broker_type: Optional[str] = None,
        **kwargs,
    ) -> BaseBroker:
        """
        Create a broker instance.

        Args:
            broker_type: Type of broker (oanda, ig, ib, alpaca)
                        If not specified, uses BROKER_TYPE from settings
            **kwargs: Additional arguments passed to broker constructor

        Returns:
            BaseBroker instance

        Raises:
            ValueError: If broker type is not supported
        """
        broker_type = (broker_type or settings.BROKER_TYPE).lower()

        if broker_type == "oanda":
            return OANDABroker(
                api_key=kwargs.get("api_key", settings.OANDA_API_KEY),
                account_id=kwargs.get("account_id", settings.OANDA_ACCOUNT_ID),
                environment=kwargs.get("environment", settings.OANDA_ENVIRONMENT),
            )

        elif broker_type == "ig":
            # TODO: Implement IG broker
            raise NotImplementedError("IG broker not yet implemented")

        elif broker_type in ("ib", "interactive_brokers"):
            # TODO: Implement Interactive Brokers
            raise NotImplementedError("Interactive Brokers not yet implemented")

        elif broker_type == "alpaca":
            # TODO: Implement Alpaca broker
            raise NotImplementedError("Alpaca broker not yet implemented")

        else:
            raise ValueError(f"Unsupported broker type: {broker_type}")

    @classmethod
    async def get_instance(
        cls,
        broker_type: Optional[str] = None,
        **kwargs,
    ) -> BaseBroker:
        """
        Get a connected broker instance (singleton per broker type).

        This is useful for sharing a single broker connection across
        multiple parts of the application.

        Args:
            broker_type: Type of broker
            **kwargs: Additional arguments

        Returns:
            Connected BaseBroker instance
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
