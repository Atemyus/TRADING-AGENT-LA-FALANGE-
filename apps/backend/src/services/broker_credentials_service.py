"""
Utilities for platform-specific broker credentials.

This module centralizes:
- credentials normalization/masking
- merge logic that preserves masked secrets on update
- runtime credential resolution for supported broker adapters
- optional MetaApi auto-provisioning for MT4/MT5 credentials
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

    token = _first_non_empty(
        broker.metaapi_token,
        creds.get("metaapi_token"),
        os.environ.get("METAAPI_ACCESS_TOKEN"),
        settings.METAAPI_ACCESS_TOKEN,
    )
    account_id = _first_non_empty(
        broker.metaapi_account_id,
        creds.get("metaapi_account_id"),
        os.environ.get("METAAPI_ACCOUNT_ID"),
        settings.METAAPI_ACCOUNT_ID,
    )
    platform = (_first_non_empty(broker.platform_id, creds.get("platform")) or "mt5").lower()
    if platform not in {"mt4", "mt5"}:
        platform = "mt5"

    if account_id and token:
        return {"access_token": token, "account_id": account_id, "platform": platform}

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

    return {"access_token": token, "account_id": account_id, "platform": platform}


async def resolve_broker_runtime_kwargs(broker: BrokerAccount) -> dict[str, str]:
    broker_type = (broker.broker_type or "metaapi").lower()
    if broker_type in {"metaapi", "metatrader", "mt4", "mt5"}:
        return await resolve_metaapi_runtime_credentials(broker)
    if broker_type == "oanda":
        return resolve_oanda_runtime_credentials(broker)
    return normalize_credentials(broker.credentials)
