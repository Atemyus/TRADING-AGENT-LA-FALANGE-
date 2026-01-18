"""
Settings API routes for configuring broker, AI providers, and other settings.
Settings are stored in a JSON file for persistence.
"""

import json
import os
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# Settings file path
SETTINGS_FILE = Path("/tmp/trading_settings.json")


# ============ Models ============

class BrokerSettings(BaseModel):
    broker_type: str = "metatrader"  # oanda, metatrader, ig, alpaca
    # OANDA
    oanda_api_key: Optional[str] = None
    oanda_account_id: Optional[str] = None
    oanda_environment: str = "practice"
    # MetaTrader (via MetaApi)
    metaapi_token: Optional[str] = None
    metaapi_account_id: Optional[str] = None
    metaapi_platform: str = "mt5"
    # IG Markets
    ig_api_key: Optional[str] = None
    ig_username: Optional[str] = None
    ig_password: Optional[str] = None
    ig_account_id: Optional[str] = None
    ig_environment: str = "demo"
    # Alpaca
    alpaca_api_key: Optional[str] = None
    alpaca_secret_key: Optional[str] = None
    alpaca_paper: bool = True


class AIProviderSettings(BaseModel):
    aiml_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None


class RiskSettings(BaseModel):
    max_positions: int = 5
    max_daily_trades: int = 50
    max_daily_loss_percent: float = 5.0
    risk_per_trade: float = 1.0
    default_leverage: int = 10
    trading_enabled: bool = False


class NotificationSettings(BaseModel):
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_enabled: bool = False
    discord_webhook: Optional[str] = None


class AllSettings(BaseModel):
    broker: BrokerSettings = BrokerSettings()
    ai: AIProviderSettings = AIProviderSettings()
    risk: RiskSettings = RiskSettings()
    notifications: NotificationSettings = NotificationSettings()


# ============ Helper Functions ============

def load_settings() -> AllSettings:
    """Load settings from file."""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                return AllSettings(**data)
        except Exception:
            pass
    return AllSettings()


def save_settings(settings: AllSettings) -> None:
    """Save settings to file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings.model_dump(), f, indent=2)


def apply_settings_to_env(settings: AllSettings) -> None:
    """Apply settings to environment variables for the current session."""
    broker = settings.broker
    ai = settings.ai
    risk = settings.risk
    notif = settings.notifications

    # Broker settings
    os.environ["BROKER_TYPE"] = broker.broker_type

    if broker.broker_type == "oanda":
        if broker.oanda_api_key:
            os.environ["OANDA_API_KEY"] = broker.oanda_api_key
        if broker.oanda_account_id:
            os.environ["OANDA_ACCOUNT_ID"] = broker.oanda_account_id
        os.environ["OANDA_ENVIRONMENT"] = broker.oanda_environment

    elif broker.broker_type == "metatrader":
        if broker.metaapi_token:
            os.environ["METAAPI_ACCESS_TOKEN"] = broker.metaapi_token
        if broker.metaapi_account_id:
            os.environ["METAAPI_ACCOUNT_ID"] = broker.metaapi_account_id

    elif broker.broker_type == "ig":
        if broker.ig_api_key:
            os.environ["IG_API_KEY"] = broker.ig_api_key
        if broker.ig_username:
            os.environ["IG_USERNAME"] = broker.ig_username
        if broker.ig_password:
            os.environ["IG_PASSWORD"] = broker.ig_password
        if broker.ig_account_id:
            os.environ["IG_ACCOUNT_ID"] = broker.ig_account_id
        os.environ["IG_ENVIRONMENT"] = broker.ig_environment

    elif broker.broker_type == "alpaca":
        if broker.alpaca_api_key:
            os.environ["ALPACA_API_KEY"] = broker.alpaca_api_key
        if broker.alpaca_secret_key:
            os.environ["ALPACA_SECRET_KEY"] = broker.alpaca_secret_key
        os.environ["ALPACA_PAPER"] = str(broker.alpaca_paper).lower()

    # AI settings
    if ai.aiml_api_key:
        os.environ["AIML_API_KEY"] = ai.aiml_api_key
    if ai.openai_api_key:
        os.environ["OPENAI_API_KEY"] = ai.openai_api_key
    if ai.anthropic_api_key:
        os.environ["ANTHROPIC_API_KEY"] = ai.anthropic_api_key
    if ai.google_api_key:
        os.environ["GOOGLE_API_KEY"] = ai.google_api_key
    if ai.groq_api_key:
        os.environ["GROQ_API_KEY"] = ai.groq_api_key
    if ai.mistral_api_key:
        os.environ["MISTRAL_API_KEY"] = ai.mistral_api_key

    # Risk settings
    os.environ["MAX_POSITIONS"] = str(risk.max_positions)
    os.environ["MAX_DAILY_TRADES"] = str(risk.max_daily_trades)
    os.environ["MAX_DAILY_LOSS_PERCENT"] = str(risk.max_daily_loss_percent)
    os.environ["DEFAULT_RISK_PER_TRADE"] = str(risk.risk_per_trade)
    os.environ["TRADING_ENABLED"] = str(risk.trading_enabled).lower()

    # Notification settings
    if notif.telegram_bot_token:
        os.environ["TELEGRAM_BOT_TOKEN"] = notif.telegram_bot_token
    if notif.telegram_chat_id:
        os.environ["TELEGRAM_CHAT_ID"] = notif.telegram_chat_id
    if notif.discord_webhook:
        os.environ["DISCORD_WEBHOOK_URL"] = notif.discord_webhook


# ============ API Routes ============

@router.get("", response_model=AllSettings)
async def get_settings():
    """Get all current settings."""
    settings = load_settings()
    # Mask sensitive data
    response = settings.model_dump()

    # Mask API keys (show only last 4 chars)
    def mask_key(key: Optional[str]) -> Optional[str]:
        if key and len(key) > 4:
            return "***" + key[-4:]
        return key

    if response["broker"]["oanda_api_key"]:
        response["broker"]["oanda_api_key"] = mask_key(response["broker"]["oanda_api_key"])
    if response["broker"]["metaapi_token"]:
        response["broker"]["metaapi_token"] = mask_key(response["broker"]["metaapi_token"])
    if response["broker"]["ig_api_key"]:
        response["broker"]["ig_api_key"] = mask_key(response["broker"]["ig_api_key"])
    if response["broker"]["ig_password"]:
        response["broker"]["ig_password"] = "***"
    if response["broker"]["alpaca_api_key"]:
        response["broker"]["alpaca_api_key"] = mask_key(response["broker"]["alpaca_api_key"])
    if response["broker"]["alpaca_secret_key"]:
        response["broker"]["alpaca_secret_key"] = mask_key(response["broker"]["alpaca_secret_key"])
    if response["ai"]["aiml_api_key"]:
        response["ai"]["aiml_api_key"] = mask_key(response["ai"]["aiml_api_key"])
    if response["ai"]["openai_api_key"]:
        response["ai"]["openai_api_key"] = mask_key(response["ai"]["openai_api_key"])

    return response


@router.put("", response_model=dict)
async def update_all_settings(settings: AllSettings):
    """Update all settings at once."""
    # Load existing settings to preserve masked fields
    existing = load_settings()

    # Don't overwrite with masked values
    def preserve_if_masked(new_val: Optional[str], old_val: Optional[str]) -> Optional[str]:
        if new_val and new_val.startswith("***"):
            return old_val
        return new_val

    # Preserve masked broker credentials
    settings.broker.oanda_api_key = preserve_if_masked(
        settings.broker.oanda_api_key, existing.broker.oanda_api_key
    )
    settings.broker.metaapi_token = preserve_if_masked(
        settings.broker.metaapi_token, existing.broker.metaapi_token
    )
    settings.broker.ig_api_key = preserve_if_masked(
        settings.broker.ig_api_key, existing.broker.ig_api_key
    )
    settings.broker.ig_password = preserve_if_masked(
        settings.broker.ig_password, existing.broker.ig_password
    )
    settings.broker.alpaca_api_key = preserve_if_masked(
        settings.broker.alpaca_api_key, existing.broker.alpaca_api_key
    )
    settings.broker.alpaca_secret_key = preserve_if_masked(
        settings.broker.alpaca_secret_key, existing.broker.alpaca_secret_key
    )

    # Preserve masked AI keys
    settings.ai.aiml_api_key = preserve_if_masked(
        settings.ai.aiml_api_key, existing.ai.aiml_api_key
    )
    settings.ai.openai_api_key = preserve_if_masked(
        settings.ai.openai_api_key, existing.ai.openai_api_key
    )
    settings.ai.anthropic_api_key = preserve_if_masked(
        settings.ai.anthropic_api_key, existing.ai.anthropic_api_key
    )

    # Save and apply
    save_settings(settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "Settings saved successfully"}


@router.put("/broker", response_model=dict)
async def update_broker_settings(broker: BrokerSettings):
    """Update broker settings."""
    settings = load_settings()
    existing_broker = settings.broker

    # Preserve masked values
    def preserve_if_masked(new_val: Optional[str], old_val: Optional[str]) -> Optional[str]:
        if new_val and new_val.startswith("***"):
            return old_val
        return new_val

    broker.oanda_api_key = preserve_if_masked(broker.oanda_api_key, existing_broker.oanda_api_key)
    broker.metaapi_token = preserve_if_masked(broker.metaapi_token, existing_broker.metaapi_token)
    broker.ig_api_key = preserve_if_masked(broker.ig_api_key, existing_broker.ig_api_key)
    broker.ig_password = preserve_if_masked(broker.ig_password, existing_broker.ig_password)
    broker.alpaca_api_key = preserve_if_masked(broker.alpaca_api_key, existing_broker.alpaca_api_key)
    broker.alpaca_secret_key = preserve_if_masked(broker.alpaca_secret_key, existing_broker.alpaca_secret_key)

    settings.broker = broker
    save_settings(settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "Broker settings saved"}


@router.put("/ai", response_model=dict)
async def update_ai_settings(ai: AIProviderSettings):
    """Update AI provider settings."""
    settings = load_settings()
    existing_ai = settings.ai

    def preserve_if_masked(new_val: Optional[str], old_val: Optional[str]) -> Optional[str]:
        if new_val and new_val.startswith("***"):
            return old_val
        return new_val

    ai.aiml_api_key = preserve_if_masked(ai.aiml_api_key, existing_ai.aiml_api_key)
    ai.openai_api_key = preserve_if_masked(ai.openai_api_key, existing_ai.openai_api_key)
    ai.anthropic_api_key = preserve_if_masked(ai.anthropic_api_key, existing_ai.anthropic_api_key)
    ai.google_api_key = preserve_if_masked(ai.google_api_key, existing_ai.google_api_key)
    ai.groq_api_key = preserve_if_masked(ai.groq_api_key, existing_ai.groq_api_key)
    ai.mistral_api_key = preserve_if_masked(ai.mistral_api_key, existing_ai.mistral_api_key)

    settings.ai = ai
    save_settings(settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "AI settings saved"}


@router.put("/risk", response_model=dict)
async def update_risk_settings(risk: RiskSettings):
    """Update risk management settings."""
    settings = load_settings()
    settings.risk = risk
    save_settings(settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "Risk settings saved"}


@router.put("/notifications", response_model=dict)
async def update_notification_settings(notifications: NotificationSettings):
    """Update notification settings."""
    settings = load_settings()
    settings.notifications = notifications
    save_settings(settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "Notification settings saved"}


@router.post("/test-broker", response_model=dict)
async def test_broker_connection():
    """Test the broker connection with current settings."""
    settings = load_settings()
    broker = settings.broker

    try:
        if broker.broker_type == "metatrader":
            if not broker.metaapi_token or not broker.metaapi_account_id:
                raise HTTPException(status_code=400, detail="MetaApi credentials not configured")

            # Test MetaApi connection
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/{broker.metaapi_account_id}",
                    headers={"auth-token": broker.metaapi_token},
                    timeout=10.0
                )
                if response.status_code == 200:
                    account_info = response.json()
                    return {
                        "status": "success",
                        "message": "Connected to MetaTrader successfully",
                        "account_name": account_info.get("name", "Unknown"),
                        "platform": account_info.get("platform", broker.metaapi_platform),
                    }
                else:
                    raise HTTPException(status_code=400, detail="Invalid MetaApi credentials")

        elif broker.broker_type == "oanda":
            if not broker.oanda_api_key or not broker.oanda_account_id:
                raise HTTPException(status_code=400, detail="OANDA credentials not configured")

            # Test OANDA connection
            import httpx
            base_url = "https://api-fxpractice.oanda.com" if broker.oanda_environment == "practice" else "https://api-fxtrade.oanda.com"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{base_url}/v3/accounts/{broker.oanda_account_id}/summary",
                    headers={"Authorization": f"Bearer {broker.oanda_api_key}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return {"status": "success", "message": "Connected to OANDA successfully"}
                else:
                    raise HTTPException(status_code=400, detail="Invalid OANDA credentials")

        else:
            return {"status": "success", "message": f"Broker {broker.broker_type} configured (connection test not implemented)"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
