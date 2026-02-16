"""
Utilities for platform-specific broker credentials.

This module centralizes:
- credentials normalization/masking
- merge logic that preserves masked secrets on update
- runtime credential resolution for supported broker adapters
- optional MetaApi auto-provisioning for MT4/MT5 credentials
- optional self-hosted MT bridge runtime resolution
"""

import os
import secrets
from typing import Any

import httpx
from fastapi import HTTPException

from src.core.config import settings
from src.core.models import BrokerAccount

METAAPI_PROVISIONING_URL = "https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai"
SENSITIVE_KEY_HINTS = ("password", "secret", "token", "api_key", "key", "passphrase")
MASKED_PREFIX = "***"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    return any(hint in lowered for hint in SENSITIVE_KEY_HINTS)


def normalize_credentials(credentials: dict[str, Any] | None) -> dict[str, str]:
    if not credentials:
        return {}

    normalized: dict[str, str] = {}
    for raw_key, raw_value in credentials.items():
        key = _clean(raw_key)
        if not key:
            continue
        value = _clean(raw_value)
        if value:
            normalized[key] = value
    return normalized


def mask_credentials(credentials: dict[str, str] | None) -> dict[str, str]:
    if not credentials:
        return {}

    masked: dict[str, str] = {}
    for key, value in credentials.items():
        if not value:
            continue
        if is_sensitive_key(key):
            masked[key] = f"{MASKED_PREFIX}{value[-4:]}" if len(value) > 4 else MASKED_PREFIX
        else:
            masked[key] = value
    return masked


def merge_credentials_preserving_masked(
    existing: dict[str, str] | None,
    incoming: dict[str, Any] | None,
) -> dict[str, str]:
    current = normalize_credentials(existing)
    updates = normalize_credentials(incoming)
    if not updates:
        return current

    merged = dict(current)
    for key, value in updates.items():
        if value.startswith(MASKED_PREFIX) and key in current and is_sensitive_key(key):
            merged[key] = current[key]
        else:
            merged[key] = value
    return merged


def _first_non_empty(*values: Any) -> str | None:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"true", "1", "yes", "y", "on"}:
        return True
    if lowered in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _to_timeout_seconds(value: Any, default: float = 90.0, minimum: float = 30.0) -> float:
    try:
        parsed = float(_clean(value))
    except Exception:
        return default
    if parsed < minimum:
        return default
    return parsed


def _resolve_mt_connection_mode(creds: dict[str, str], broker: BrokerAccount | None = None) -> str:
    _ = (creds, broker)
    # Bridge mode is intentionally disabled for MT4/MT5 workspaces in this deployment.
    return "metaapi"


def should_use_mt_bridge(broker: BrokerAccount) -> bool:
    _ = broker
    return False


def resolve_oanda_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    creds = normalize_credentials(broker.credentials)
    account_id = _first_non_empty(
        creds.get("oanda_account_id"),
        creds.get("account_id"),
        os.environ.get("OANDA_ACCOUNT_ID"),
        settings.OANDA_ACCOUNT_ID,
    )
    api_key = _first_non_empty(
        creds.get("oanda_api_key"),
        creds.get("api_key"),
        os.environ.get("OANDA_API_KEY"),
        settings.OANDA_API_KEY,
    )
    environment = _first_non_empty(
        creds.get("oanda_environment"),
        creds.get("environment"),
        os.environ.get("OANDA_ENVIRONMENT"),
        settings.OANDA_ENVIRONMENT,
    ) or "practice"

    if not account_id or not api_key:
        raise HTTPException(status_code=400, detail="OANDA credentials not configured for this workspace.")

    return {
        "account_id": account_id,
        "api_key": api_key,
        "environment": environment,
    }


def resolve_ig_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    creds = normalize_credentials(broker.credentials)
    api_key = _first_non_empty(
        creds.get("ig_api_key"),
        creds.get("api_key"),
        os.environ.get("IG_API_KEY"),
        settings.IG_API_KEY,
    )
    username = _first_non_empty(
        creds.get("ig_username"),
        creds.get("username"),
        os.environ.get("IG_USERNAME"),
        settings.IG_USERNAME,
    )
    password = _first_non_empty(
        creds.get("ig_password"),
        creds.get("password"),
        os.environ.get("IG_PASSWORD"),
        settings.IG_PASSWORD,
    )
    account_id = _first_non_empty(
        creds.get("ig_account_id"),
        creds.get("account_id"),
        os.environ.get("IG_ACCOUNT_ID"),
        settings.IG_ACCOUNT_ID,
    )
    environment = _first_non_empty(
        creds.get("ig_environment"),
        creds.get("environment"),
        os.environ.get("IG_ENVIRONMENT"),
        settings.IG_ENVIRONMENT,
    ) or "demo"

    if not api_key or not username or not password:
        raise HTTPException(
            status_code=400,
            detail="IG credentials not configured for this workspace (api key, username, password required).",
        )

    runtime = {
        "api_key": api_key,
        "username": username,
        "password": password,
        "environment": environment,
    }
    if account_id:
        runtime["account_id"] = account_id
    return runtime


def resolve_alpaca_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    creds = normalize_credentials(broker.credentials)
    api_key = _first_non_empty(
        creds.get("alpaca_api_key"),
        creds.get("api_key"),
        os.environ.get("ALPACA_API_KEY"),
        settings.ALPACA_API_KEY,
    )
    secret_key = _first_non_empty(
        creds.get("alpaca_secret_key"),
        creds.get("secret_key"),
        creds.get("password"),
        os.environ.get("ALPACA_SECRET_KEY"),
        settings.ALPACA_SECRET_KEY,
    )
    paper_bool = _to_bool(
        _first_non_empty(
            creds.get("alpaca_paper"),
            creds.get("paper"),
            os.environ.get("ALPACA_PAPER"),
            settings.ALPACA_PAPER,
        ),
        default=True,
    )

    if not api_key or not secret_key:
        raise HTTPException(
            status_code=400,
            detail="Alpaca credentials not configured for this workspace (api key and secret key required).",
        )

    return {
        "api_key": api_key,
        "secret_key": secret_key,
        "paper": "true" if paper_bool else "false",
    }


def _resolve_platform_account_credentials(
    broker: BrokerAccount,
    *,
    platform_label: str,
    default_login_endpoint: str,
    default_health_endpoint: str = "/",
) -> dict[str, str]:
    creds = normalize_credentials(broker.credentials)
    account_id = _first_non_empty(
        creds.get("account_id"),
        creds.get("account_number"),
        creds.get("login"),
        creds.get("username"),
    )
    password = _first_non_empty(
        creds.get("account_password"),
        creds.get("password"),
        creds.get("passphrase"),
    )
    server_name = _first_non_empty(
        creds.get("server_name"),
        creds.get("server"),
        creds.get("broker_server"),
        creds.get("host"),
    )
    api_base_url = _first_non_empty(
        creds.get("api_base_url"),
        creds.get("base_url"),
        creds.get("url"),
    )
    login_endpoint = _first_non_empty(
        creds.get("login_endpoint"),
        creds.get("auth_endpoint"),
    ) or default_login_endpoint
    health_endpoint = _first_non_empty(
        creds.get("health_endpoint"),
        creds.get("ping_endpoint"),
    ) or default_health_endpoint

    if not account_id or not password or not server_name:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{platform_label} credentials not configured for this workspace. "
                "Required: account id/login, password, server name."
            ),
        )

    return {
        "account_id": account_id,
        "password": password,
        "server_name": server_name,
        "api_base_url": api_base_url or "",
        "login_endpoint": login_endpoint,
        "health_endpoint": health_endpoint,
    }


def resolve_ctrader_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    return _resolve_platform_account_credentials(
        broker,
        platform_label="cTrader",
        default_login_endpoint="/connect/token",
        default_health_endpoint="/",
    )


def resolve_dxtrade_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    return _resolve_platform_account_credentials(
        broker,
        platform_label="DXtrade",
        default_login_endpoint="/api/auth/login",
        default_health_endpoint="/api/health",
    )


def resolve_matchtrader_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    return _resolve_platform_account_credentials(
        broker,
        platform_label="Match-Trader",
        default_login_endpoint="/api/login",
        default_health_endpoint="/api/health",
    )


async def _find_existing_metaapi_account(
    *,
    token: str,
    account_number: str,
    server_name: str,
    platform: str,
) -> str | None:
    headers = {"auth-token": token}
    async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
        response = await client.get(f"{METAAPI_PROVISIONING_URL}/users/current/accounts", headers=headers)
        if response.status_code != 200:
            return None
        payload = response.json()
        candidates = payload if isinstance(payload, list) else payload.get("items", [])
        target_server = server_name.lower()
        for account in candidates:
            login = _clean(account.get("login"))
            server = _clean(account.get("server")).lower()
            acct_platform = _clean(account.get("platform")).lower()
            if login == account_number and server == target_server and acct_platform == platform:
                account_id = _clean(account.get("id"))
                if account_id:
                    return account_id
    return None


async def _provision_metaapi_account(
    *,
    token: str,
    workspace_name: str,
    platform: str,
    account_number: str,
    account_password: str,
    server_name: str,
) -> str:
    existing_id = await _find_existing_metaapi_account(
        token=token,
        account_number=account_number,
        server_name=server_name,
        platform=platform,
    )
    if existing_id:
        return existing_id

    headers = {
        "auth-token": token,
        "transaction-id": secrets.token_hex(16),
    }
    payload = {
        "name": workspace_name[:120],
        "type": "cloud-g1",
        "platform": platform,
        "login": account_number,
        "password": account_password,
        "server": server_name,
        "magic": 1000,
        "manualTrades": True,
    }

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
        response = await client.post(
            f"{METAAPI_PROVISIONING_URL}/users/current/accounts",
            headers=headers,
            json=payload,
        )

        if response.status_code not in {200, 201, 202}:
            detail = response.text.strip() or f"status {response.status_code}"
            raise HTTPException(
                status_code=400,
                detail=f"Automatic MT account provisioning failed: {detail}",
            )

        data = response.json() if response.content else {}
        account_id = _clean(data.get("id"))
        if not account_id:
            raise HTTPException(
                status_code=400,
                detail="Automatic MT account provisioning did not return an account id.",
            )

        # Best effort deployment: account may still come online asynchronously.
        try:
            await client.post(
                f"{METAAPI_PROVISIONING_URL}/users/current/accounts/{account_id}/deploy",
                headers={"auth-token": token, "transaction-id": secrets.token_hex(16)},
            )
        except Exception:
            pass

        return account_id


async def resolve_metaapi_runtime_credentials(
    broker: BrokerAccount,
) -> dict[str, str]:
    creds = normalize_credentials(broker.credentials)
    broker_type = (broker.broker_type or "").strip().lower()
    default_platform = "mt4" if broker_type == "mt4" else "mt5"

    token = _first_non_empty(
        broker.metaapi_token,
        creds.get("metaapi_token"),
        os.environ.get("METAAPI_ACCESS_TOKEN"),
        settings.METAAPI_ACCESS_TOKEN,
    )
    account_id = _first_non_empty(
        broker.metaapi_account_id,
        creds.get("metaapi_account_id"),
    )
    platform = (_first_non_empty(broker.platform_id, creds.get("platform")) or default_platform).lower()
    if platform not in {"mt4", "mt5"}:
        platform = default_platform

    if account_id and token:
        return {
            "access_token": token,
            "account_id": account_id,
            "platform": platform,
            "connection_mode": "metaapi",
        }

    account_number = _first_non_empty(
        creds.get("account_number"),
        creds.get("login"),
        creds.get("account_id"),
    )
    account_password = _first_non_empty(
        creds.get("account_password"),
        creds.get("password"),
        creds.get("investor_password"),
        creds.get("master_password"),
    )
    server_name = _first_non_empty(
        creds.get("server_name"),
        creds.get("server"),
        creds.get("broker_server"),
    )

    if not token:
        raise HTTPException(
            status_code=400,
            detail=(
                "MetaApi gateway token not configured on server. "
                "Set METAAPI_ACCESS_TOKEN in backend environment."
            ),
        )

    if not account_id:
        if not account_number or not account_password or not server_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing MT credentials. Required: account number, password, server name "
                    "(or an existing MetaApi account id)."
                ),
            )
        account_id = await _provision_metaapi_account(
            token=token,
            workspace_name=broker.name,
            platform=platform,
            account_number=account_number,
            account_password=account_password,
            server_name=server_name,
        )
        broker.metaapi_account_id = account_id

    return {
        "access_token": token,
        "account_id": account_id,
        "platform": platform,
        "connection_mode": "metaapi",
    }


def resolve_mt_bridge_runtime_credentials(broker: BrokerAccount) -> dict[str, str]:
    creds = normalize_credentials(broker.credentials)
    mode = _resolve_mt_connection_mode(creds, broker=broker)
    broker_type = (broker.broker_type or "").strip().lower()
    default_platform = "mt4" if broker_type == "mt4" else "mt5"

    account_number = _first_non_empty(
        creds.get("account_number"),
        creds.get("login"),
        creds.get("account_id"),
    )
    account_password = _first_non_empty(
        creds.get("account_password"),
        creds.get("password"),
        creds.get("master_password"),
    )
    server_name = _first_non_empty(
        creds.get("server_name"),
        creds.get("server"),
        creds.get("broker_server"),
    )
    server_candidates = _first_non_empty(
        creds.get("server_candidates"),
        creds.get("mt_server_candidates"),
        creds.get("mt5_server_candidates"),
    )
    platform = (_first_non_empty(broker.platform_id, creds.get("platform")) or default_platform).lower()
    if platform not in {"mt4", "mt5"}:
        platform = default_platform

    bridge_base_url = _first_non_empty(
        creds.get("mt_bridge_base_url"),
        creds.get("bridge_base_url"),
        creds.get("mt_bridge_url"),
        os.environ.get("MT_BRIDGE_BASE_URL"),
        settings.MT_BRIDGE_BASE_URL,
    )
    bridge_api_key = _first_non_empty(
        creds.get("mt_bridge_api_key"),
        creds.get("bridge_api_key"),
        os.environ.get("MT_BRIDGE_API_KEY"),
        settings.MT_BRIDGE_API_KEY,
    )
    timeout_seconds_raw = _first_non_empty(
        creds.get("mt_bridge_timeout_seconds"),
        creds.get("bridge_timeout_seconds"),
        os.environ.get("MT_BRIDGE_TIMEOUT_SECONDS"),
        settings.MT_BRIDGE_TIMEOUT_SECONDS,
    ) or "90"
    timeout_seconds = _to_timeout_seconds(timeout_seconds_raw, default=90.0, minimum=30.0)

    if mode != "bridge":
        raise HTTPException(
            status_code=400,
            detail=(
                "MT bridge resolution requested but workspace is not configured for bridge mode. "
                "Set mt_connection_mode=bridge."
            ),
        )

    if not account_number or not account_password:
        raise HTTPException(
            status_code=400,
            detail=(
                "Missing MT bridge credentials. Required: account number and password."
            ),
        )
    if platform == "mt4" and not server_name:
        raise HTTPException(
            status_code=400,
            detail="Missing MT4 bridge credentials. Required: server name.",
        )
    if not bridge_base_url:
        raise HTTPException(
            status_code=400,
            detail=(
                "MT bridge base URL not configured. Set mt_bridge_base_url in workspace credentials "
                "or MT_BRIDGE_BASE_URL in backend environment."
            ),
        )

    runtime: dict[str, str] = {
        "connection_mode": "bridge",
        "account_number": account_number,
        "password": account_password,
        "platform": platform,
        "bridge_base_url": bridge_base_url,
        "timeout_seconds": str(int(timeout_seconds) if timeout_seconds.is_integer() else timeout_seconds),
    }
    if server_name:
        runtime["server_name"] = server_name
    if server_candidates:
        runtime["server_candidates"] = server_candidates
    if bridge_api_key:
        runtime["bridge_api_key"] = bridge_api_key

    optional_passthrough_keys = {
        "terminal_path": ["terminal_path", "mt_terminal_path"],
        "data_path": ["data_path", "mt_data_path"],
        "workspace_id": ["workspace_id", "mt_workspace_id"],
        "connect_endpoint": ["connect_endpoint", "mt_bridge_connect_endpoint"],
        "disconnect_endpoint": ["disconnect_endpoint", "mt_bridge_disconnect_endpoint"],
        "account_endpoint": ["account_endpoint", "mt_bridge_account_endpoint"],
        "positions_endpoint": ["positions_endpoint", "mt_bridge_positions_endpoint"],
        "price_endpoint": ["price_endpoint", "mt_bridge_price_endpoint"],
        "prices_endpoint": ["prices_endpoint", "mt_bridge_prices_endpoint"],
        "candles_endpoint": ["candles_endpoint", "mt_bridge_candles_endpoint"],
        "place_order_endpoint": ["place_order_endpoint", "mt_bridge_place_order_endpoint"],
        "open_orders_endpoint": ["open_orders_endpoint", "mt_bridge_open_orders_endpoint"],
        "order_endpoint": ["order_endpoint", "mt_bridge_order_endpoint"],
        "cancel_order_endpoint": ["cancel_order_endpoint", "mt_bridge_cancel_order_endpoint"],
        "close_position_endpoint": ["close_position_endpoint", "mt_bridge_close_position_endpoint"],
        "modify_position_endpoint": ["modify_position_endpoint", "mt_bridge_modify_position_endpoint"],
    }
    for runtime_key, aliases in optional_passthrough_keys.items():
        value = _first_non_empty(*(creds.get(alias) for alias in aliases))
        if value:
            runtime[runtime_key] = value

    return runtime


async def resolve_broker_runtime_kwargs(broker: BrokerAccount) -> dict[str, str]:
    broker_type = (broker.broker_type or "metaapi").lower()
    if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
        if should_use_mt_bridge(broker):
            return resolve_mt_bridge_runtime_credentials(broker)
        return await resolve_metaapi_runtime_credentials(broker)
    if broker_type == "oanda":
        return resolve_oanda_runtime_credentials(broker)
    if broker_type == "ig":
        return resolve_ig_runtime_credentials(broker)
    if broker_type == "alpaca":
        return resolve_alpaca_runtime_credentials(broker)
    if broker_type == "ctrader":
        return resolve_ctrader_runtime_credentials(broker)
    if broker_type == "dxtrade":
        return resolve_dxtrade_runtime_credentials(broker)
    if broker_type == "matchtrader":
        return resolve_matchtrader_runtime_credentials(broker)
    return normalize_credentials(broker.credentials)
