"""
Broker Factory

Factory for creating broker instances based on configuration.
Supports multiple brokers: OANDA, MetaTrader (MetaApi or Bridge), IG, Interactive Brokers, Alpaca.

NOTE: This factory reads from os.environ directly (not Pydantic settings)
to support dynamic credential updates without server restart.
"""

import os

from src.engines.trading.alpaca_broker import AlpacaBroker
from src.engines.trading.base_broker import BaseBroker
from src.engines.trading.ig_broker import IGBroker
from src.engines.trading.metatrader_bridge_broker import MetaTraderBridgeBroker
from src.engines.trading.metatrader_broker import MetaTraderBroker
from src.engines.trading.oanda_broker import OANDABroker
from src.engines.trading.platform_rest_broker import (
    CTraderBroker,
    DXTradeBroker,
    MatchTraderBroker,
)


class NoBrokerConfiguredError(Exception):
    """Raised when no broker is configured or credentials are missing."""
    pass


class BrokerFactory:
    """
    Factory for creating broker instances.

    Usage:
        broker = BrokerFactory.create("oanda")
        await broker.connect()

    NOTE: Reads from os.environ directly to support dynamic credential updates.
    """

    _instances: dict = {}

    @classmethod
    def is_configured(cls, broker_type: str | None = None) -> bool:
        """Check if a broker is properly configured with credentials."""
        # Read from os.environ directly to get dynamically updated values
        broker_type = (broker_type or os.environ.get("BROKER_TYPE", "none")).lower()

        if broker_type == "oanda":
            api_key = os.environ.get("OANDA_API_KEY", "")
            account_id = os.environ.get("OANDA_ACCOUNT_ID", "")
            return bool(api_key and account_id)
        elif broker_type in ("metatrader", "metaapi", "mt4", "mt5"):
            mode = (os.environ.get("METATRADER_CONNECTION_MODE", "metaapi") or "metaapi").strip().lower()
            if mode == "bridge":
                account_number = (
                    os.environ.get("MT_BRIDGE_ACCOUNT_NUMBER", "")
                    or os.environ.get("BROKER_ACCOUNT_NUMBER", "")
                )
                password = os.environ.get("MT_BRIDGE_PASSWORD", "") or os.environ.get("BROKER_PASSWORD", "")
                server_name = os.environ.get("MT_BRIDGE_SERVER_NAME", "") or os.environ.get("BROKER_SERVER_NAME", "")
                bridge_base_url = os.environ.get("MT_BRIDGE_BASE_URL", "")
                platform = (
                    os.environ.get("MT_BRIDGE_PLATFORM", "")
                    or os.environ.get("BROKER_PLATFORM", "")
                    or ("mt4" if broker_type == "mt4" else "mt5")
                )
                safe_platform = str(platform or "mt5").strip().lower()
                if safe_platform not in {"mt4", "mt5"}:
                    safe_platform = "mt4" if broker_type == "mt4" else "mt5"
                needs_server = safe_platform == "mt4"
                return bool(account_number and password and bridge_base_url and (server_name or not needs_server))
            token = os.environ.get("METAAPI_ACCESS_TOKEN", "")
            account = os.environ.get("METAAPI_ACCOUNT_ID", "")
            return bool(token and account)
        elif broker_type == "ig":
            api_key = os.environ.get("IG_API_KEY", "")
            username = os.environ.get("IG_USERNAME", "")
            password = os.environ.get("IG_PASSWORD", "")
            return bool(api_key and username and password)
        elif broker_type == "alpaca":
            api_key = os.environ.get("ALPACA_API_KEY", "")
            secret = os.environ.get("ALPACA_SECRET_KEY", "")
            return bool(api_key and secret)
        elif broker_type in {"ctrader", "dxtrade", "matchtrader"}:
            prefix = broker_type.upper()
            account_id = os.environ.get(f"{prefix}_ACCOUNT_ID", "") or os.environ.get("BROKER_ACCOUNT_ID", "")
            password = os.environ.get(f"{prefix}_PASSWORD", "") or os.environ.get("BROKER_PASSWORD", "")
            server_name = os.environ.get(f"{prefix}_SERVER_NAME", "") or os.environ.get("BROKER_SERVER_NAME", "")
            return bool(account_id and password and server_name)
        elif broker_type == "none":
            return False
        else:
            return False

    @classmethod
    def create(
        cls,
        broker_type: str | None = None,
        **kwargs,
    ) -> BaseBroker:
        """
        Create a broker instance.

        Args:
            broker_type: Type of broker (oanda, metatrader, ig, ib, alpaca)
                        If not specified, uses BROKER_TYPE from environment
            **kwargs: Additional arguments passed to broker constructor

        Returns:
            BaseBroker instance

        Raises:
            NoBrokerConfiguredError: If broker credentials are not configured
            ValueError: If broker type is not supported

        NOTE: Reads from os.environ directly to support dynamic credential updates.
        """
        # Read from os.environ directly to get dynamically updated values
        broker_type = (broker_type or os.environ.get("BROKER_TYPE", "none")).lower()

        # Check if broker type is "none" or not configured
        if broker_type == "none":
            raise NoBrokerConfiguredError("No broker configured. Configure broker in Settings.")

        if broker_type == "oanda":
            api_key = kwargs.get("api_key", os.environ.get("OANDA_API_KEY", ""))
            account_id = kwargs.get("account_id", os.environ.get("OANDA_ACCOUNT_ID", ""))
            environment = kwargs.get("environment", os.environ.get("OANDA_ENVIRONMENT", "practice"))

            if not api_key or not account_id:
                raise NoBrokerConfiguredError(
                    "OANDA broker requires API key and account ID. Configure in Settings."
                )

            return OANDABroker(
                api_key=api_key,
                account_id=account_id,
                environment=environment,
            )

        elif broker_type in ("metatrader", "metaapi", "mt4", "mt5"):
            mode = (
                kwargs.get("connection_mode")
                or kwargs.get("mt_connection_mode")
                or os.environ.get("METATRADER_CONNECTION_MODE")
                or "metaapi"
            )
            mode = str(mode).strip().lower()

            if mode == "bridge":
                platform = (
                    kwargs.get("platform")
                    or os.environ.get("MT_BRIDGE_PLATFORM", "")
                    or os.environ.get("BROKER_PLATFORM", "")
                    or ("mt4" if broker_type == "mt4" else "mt5")
                )
                safe_platform = str(platform or "mt5").strip().lower()
                if safe_platform not in {"mt4", "mt5"}:
                    safe_platform = "mt4" if broker_type == "mt4" else "mt5"

                account_number = (
                    kwargs.get("account_number")
                    or kwargs.get("login")
                    or os.environ.get("MT_BRIDGE_ACCOUNT_NUMBER", "")
                    or os.environ.get("BROKER_ACCOUNT_NUMBER", "")
                )
                password = (
                    kwargs.get("password")
                    or kwargs.get("account_password")
                    or os.environ.get("MT_BRIDGE_PASSWORD", "")
                    or os.environ.get("BROKER_PASSWORD", "")
                )
                server_name = (
                    kwargs.get("server_name")
                    or kwargs.get("server")
                    or os.environ.get("MT_BRIDGE_SERVER_NAME", "")
                    or os.environ.get("BROKER_SERVER_NAME", "")
                )
                bridge_base_url = (
                    kwargs.get("bridge_base_url")
                    or kwargs.get("mt_bridge_base_url")
                    or os.environ.get("MT_BRIDGE_BASE_URL", "")
                )
                bridge_api_key = (
                    kwargs.get("bridge_api_key")
                    or kwargs.get("mt_bridge_api_key")
                    or os.environ.get("MT_BRIDGE_API_KEY", "")
                )
                server_candidates = (
                    kwargs.get("server_candidates")
                    or kwargs.get("mt_server_candidates")
                    or kwargs.get("mt5_server_candidates")
                    or os.environ.get("MT_BRIDGE_SERVER_CANDIDATES", "")
                    or os.environ.get("MT_BRIDGE_MT5_SERVER_CANDIDATES", "")
                )

                if not account_number or not password:
                    raise NoBrokerConfiguredError(
                        "MetaTrader bridge mode requires account number/login and password. Configure in Settings."
                    )
                if safe_platform == "mt4" and not server_name:
                    raise NoBrokerConfiguredError(
                        "MetaTrader MT4 bridge mode requires server name. Configure in Settings."
                    )
                if not bridge_base_url:
                    raise NoBrokerConfiguredError(
                        "MetaTrader bridge mode requires bridge base URL. "
                        "Set mt_bridge_base_url in credentials or MT_BRIDGE_BASE_URL in environment."
                    )

                bridge_kwargs = dict(kwargs)
                for key in {
                    "connection_mode",
                    "mt_connection_mode",
                    "account_number",
                    "login",
                    "password",
                    "account_password",
                    "server_name",
                    "server",
                    "bridge_base_url",
                    "mt_bridge_base_url",
                    "bridge_api_key",
                    "mt_bridge_api_key",
                    "server_candidates",
                    "mt_server_candidates",
                    "mt5_server_candidates",
                    "platform",
                }:
                    bridge_kwargs.pop(key, None)

                return MetaTraderBridgeBroker(
                    account_number=str(account_number),
                    password=str(password),
                    server_name=str(server_name) if server_name else None,
                    server_candidates=server_candidates,
                    platform=safe_platform,
                    bridge_base_url=str(bridge_base_url),
                    bridge_api_key=str(bridge_api_key) if bridge_api_key else None,
                    **bridge_kwargs,
                )

            token = kwargs.get("access_token", os.environ.get("METAAPI_ACCESS_TOKEN", ""))
            account = kwargs.get("account_id", os.environ.get("METAAPI_ACCOUNT_ID", ""))

            if not token or not account:
                raise NoBrokerConfiguredError(
                    "MetaTrader broker requires MetaApi token and account ID. Configure in Settings."
                )

            return MetaTraderBroker(
                access_token=token,
                account_id=account,
            )

        elif broker_type == "ig":
            api_key = kwargs.get("api_key", os.environ.get("IG_API_KEY", ""))
            username = kwargs.get("username", os.environ.get("IG_USERNAME", ""))
            password = kwargs.get("password", os.environ.get("IG_PASSWORD", ""))
            account_id = kwargs.get("account_id", os.environ.get("IG_ACCOUNT_ID", ""))
            environment = kwargs.get("environment", os.environ.get("IG_ENVIRONMENT", "demo"))
            if not api_key or not username or not password:
                raise NoBrokerConfiguredError(
                    "IG broker requires api key, username and password. Configure in Settings."
                )
            return IGBroker(
                api_key=api_key,
                username=username,
                password=password,
                account_id=account_id or None,
                environment=environment,
            )

        elif broker_type in ("ib", "interactive_brokers"):
            raise NotImplementedError("Interactive Brokers not yet implemented")

        elif broker_type in ("ctrader", "dxtrade", "matchtrader"):
            prefix = broker_type.upper()
            account_id = (
                kwargs.get("account_id")
                or kwargs.get("account_number")
                or kwargs.get("login")
                or os.environ.get(f"{prefix}_ACCOUNT_ID", "")
                or os.environ.get("BROKER_ACCOUNT_ID", "")
            )
            password = (
                kwargs.get("password")
                or kwargs.get("account_password")
                or os.environ.get(f"{prefix}_PASSWORD", "")
                or os.environ.get("BROKER_PASSWORD", "")
            )
            server_name = (
                kwargs.get("server_name")
                or kwargs.get("server")
                or os.environ.get(f"{prefix}_SERVER_NAME", "")
                or os.environ.get("BROKER_SERVER_NAME", "")
            )
            api_base_url = (
                kwargs.get("api_base_url")
                or kwargs.get("base_url")
                or os.environ.get(f"{prefix}_API_BASE_URL", "")
                or os.environ.get("BROKER_API_BASE_URL", "")
            )

            if not account_id or not password or not server_name:
                raise NoBrokerConfiguredError(
                    f"{broker_type} broker requires account id/login, password and server name. "
                    "Configure in Settings."
                )

            adapter_kwargs = dict(kwargs)
            for key in {
                "account_id",
                "account_number",
                "login",
                "password",
                "account_password",
                "server_name",
                "server",
                "api_base_url",
                "base_url",
            }:
                adapter_kwargs.pop(key, None)

            if broker_type == "ctrader":
                return CTraderBroker(
                    account_id=str(account_id),
                    password=str(password),
                    server_name=str(server_name),
                    api_base_url=str(api_base_url) if api_base_url else None,
                    **adapter_kwargs,
                )
            if broker_type == "dxtrade":
                return DXTradeBroker(
                    account_id=str(account_id),
                    password=str(password),
                    server_name=str(server_name),
                    api_base_url=str(api_base_url) if api_base_url else None,
                    **adapter_kwargs,
                )
            return MatchTraderBroker(
                account_id=str(account_id),
                password=str(password),
                server_name=str(server_name),
                api_base_url=str(api_base_url) if api_base_url else None,
                **adapter_kwargs,
            )

        elif broker_type == "alpaca":
            api_key = kwargs.get("api_key", os.environ.get("ALPACA_API_KEY", ""))
            secret_key = kwargs.get("secret_key", os.environ.get("ALPACA_SECRET_KEY", ""))
            raw_paper = kwargs.get("paper", os.environ.get("ALPACA_PAPER", "true"))
            if isinstance(raw_paper, bool):
                paper = raw_paper
            else:
                paper = str(raw_paper).lower() == "true"
            if not api_key or not secret_key:
                raise NoBrokerConfiguredError(
                    "Alpaca broker requires api key and secret key. Configure in Settings."
                )
            return AlpacaBroker(
                api_key=api_key,
                secret_key=secret_key,
                paper=paper,
            )

        else:
            raise NoBrokerConfiguredError(f"Unknown broker type: {broker_type}. Configure in Settings.")

    @classmethod
    async def get_instance(
        cls,
        broker_type: str | None = None,
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
        # Read from os.environ directly to get dynamically updated values
        broker_type = (broker_type or os.environ.get("BROKER_TYPE", "none")).lower()

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

    @classmethod
    async def reset_instance(cls, broker_type: str | None = None) -> None:
        """
        Reset a broker instance to force reconnection with new credentials.

        Args:
            broker_type: Type of broker to reset. If None, resets all.
        """
        if broker_type:
            broker_type = broker_type.lower()
            if broker_type in cls._instances:
                await cls._instances[broker_type].disconnect()
                del cls._instances[broker_type]
        else:
            await cls.close_all()


# Convenience function
async def get_broker(broker_type: str | None = None) -> BaseBroker:
    """Get the default broker instance."""
    return await BrokerFactory.get_instance(broker_type)
