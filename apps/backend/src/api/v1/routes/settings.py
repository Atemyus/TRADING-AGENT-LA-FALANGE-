"""
Settings API routes for configuring broker, AI providers, and other settings.
Settings are stored in PostgreSQL database for persistence across deployments.
"""

import json
import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import clear_settings_cache
from src.core.database import get_db
from src.core.models import AppSettings
from src.engines.trading.broker_factory import BrokerFactory
from src.services.ai_service import reset_ai_service
from src.services.price_streaming_service import reset_price_streaming_service
from src.services.trading_service import reset_trading_service

router = APIRouter()


# ============ Models ============

class BrokerSettings(BaseModel):
    broker_type: str = "metatrader"  # oanda, metatrader, ig, alpaca
    # OANDA
    oanda_api_key: str | None = None
    oanda_account_id: str | None = None
    oanda_environment: str = "practice"
    # MetaTrader (via MetaApi)
    metaapi_token: str | None = None
    metaapi_account_id: str | None = None
    metaapi_platform: str = "mt5"
    # IG Markets
    ig_api_key: str | None = None
    ig_username: str | None = None
    ig_password: str | None = None
    ig_account_id: str | None = None
    ig_environment: str = "demo"
    # Alpaca
    alpaca_api_key: str | None = None
    alpaca_secret_key: str | None = None
    alpaca_paper: bool = True


class AIProviderSettings(BaseModel):
    aiml_api_key: str | None = None
    nvidia_api_key: str | None = None
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    groq_api_key: str | None = None
    mistral_api_key: str | None = None


class RiskSettings(BaseModel):
    max_positions: int = 5
    max_daily_trades: int = 50
    max_daily_loss_percent: float = 5.0
    risk_per_trade: float = 1.0
    default_leverage: int = 10
    trading_enabled: bool = False


class NotificationSettings(BaseModel):
    telegram_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    discord_enabled: bool = False
    discord_webhook: str | None = None


class AllSettings(BaseModel):
    broker: BrokerSettings = BrokerSettings()
    ai: AIProviderSettings = AIProviderSettings()
    risk: RiskSettings = RiskSettings()
    notifications: NotificationSettings = NotificationSettings()


# ============ Database Helper Functions ============

async def get_setting(db: AsyncSession, key: str) -> str | None:
    """Get a setting value from database."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(db: AsyncSession, key: str, value: str | None) -> None:
    """Set a setting value in database."""
    result = await db.execute(
        select(AppSettings).where(AppSettings.key == key)
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = value
    else:
        setting = AppSettings(key=key, value=value)
        db.add(setting)

    await db.flush()


async def load_settings_from_db(db: AsyncSession) -> AllSettings:
    """Load all settings from database."""
    settings_json = await get_setting(db, "app_settings")

    if settings_json:
        try:
            data = json.loads(settings_json)
            return AllSettings(**data)
        except Exception:
            pass

    return AllSettings()


async def save_settings_to_db(db: AsyncSession, settings: AllSettings) -> None:
    """Save all settings to database."""
    settings_json = json.dumps(settings.model_dump())
    await set_setting(db, "app_settings", settings_json)


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
    if ai.nvidia_api_key:
        os.environ["NVIDIA_API_KEY"] = ai.nvidia_api_key
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


def mask_key(key: str | None) -> str | None:
    """Mask sensitive data - show only last 4 chars."""
    if key and len(key) > 4:
        return "***" + key[-4:]
    return key


def preserve_if_masked(new_val: str | None, old_val: str | None) -> str | None:
    """Don't overwrite with masked values."""
    if new_val and new_val.startswith("***"):
        return old_val
    return new_val


# ============ API Routes ============

@router.get("", response_model=AllSettings)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get all current settings."""
    settings = await load_settings_from_db(db)

    # Mask sensitive data
    response = settings.model_dump()

    # Mask API keys (show only last 4 chars)
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
    if response["ai"]["nvidia_api_key"]:
        response["ai"]["nvidia_api_key"] = mask_key(response["ai"]["nvidia_api_key"])
    if response["ai"]["openai_api_key"]:
        response["ai"]["openai_api_key"] = mask_key(response["ai"]["openai_api_key"])
    if response["ai"]["anthropic_api_key"]:
        response["ai"]["anthropic_api_key"] = mask_key(response["ai"]["anthropic_api_key"])
    if response["ai"]["google_api_key"]:
        response["ai"]["google_api_key"] = mask_key(response["ai"]["google_api_key"])
    if response["ai"]["groq_api_key"]:
        response["ai"]["groq_api_key"] = mask_key(response["ai"]["groq_api_key"])
    if response["ai"]["mistral_api_key"]:
        response["ai"]["mistral_api_key"] = mask_key(response["ai"]["mistral_api_key"])

    return response


@router.put("", response_model=dict)
async def update_all_settings(
    new_settings: AllSettings,
    db: AsyncSession = Depends(get_db)
):
    """Update all settings at once."""
    existing = await load_settings_from_db(db)

    # Preserve masked broker credentials
    new_settings.broker.oanda_api_key = preserve_if_masked(
        new_settings.broker.oanda_api_key, existing.broker.oanda_api_key
    )
    new_settings.broker.metaapi_token = preserve_if_masked(
        new_settings.broker.metaapi_token, existing.broker.metaapi_token
    )
    new_settings.broker.ig_api_key = preserve_if_masked(
        new_settings.broker.ig_api_key, existing.broker.ig_api_key
    )
    new_settings.broker.ig_password = preserve_if_masked(
        new_settings.broker.ig_password, existing.broker.ig_password
    )
    new_settings.broker.alpaca_api_key = preserve_if_masked(
        new_settings.broker.alpaca_api_key, existing.broker.alpaca_api_key
    )
    new_settings.broker.alpaca_secret_key = preserve_if_masked(
        new_settings.broker.alpaca_secret_key, existing.broker.alpaca_secret_key
    )

    # Preserve masked AI keys
    new_settings.ai.aiml_api_key = preserve_if_masked(
        new_settings.ai.aiml_api_key, existing.ai.aiml_api_key
    )
    new_settings.ai.nvidia_api_key = preserve_if_masked(
        new_settings.ai.nvidia_api_key, existing.ai.nvidia_api_key
    )
    new_settings.ai.openai_api_key = preserve_if_masked(
        new_settings.ai.openai_api_key, existing.ai.openai_api_key
    )
    new_settings.ai.anthropic_api_key = preserve_if_masked(
        new_settings.ai.anthropic_api_key, existing.ai.anthropic_api_key
    )
    new_settings.ai.google_api_key = preserve_if_masked(
        new_settings.ai.google_api_key, existing.ai.google_api_key
    )
    new_settings.ai.groq_api_key = preserve_if_masked(
        new_settings.ai.groq_api_key, existing.ai.groq_api_key
    )
    new_settings.ai.mistral_api_key = preserve_if_masked(
        new_settings.ai.mistral_api_key, existing.ai.mistral_api_key
    )

    # Save and apply
    await save_settings_to_db(db, new_settings)
    apply_settings_to_env(new_settings)

    return {"status": "success", "message": "Settings saved successfully"}


@router.put("/broker", response_model=dict)
async def update_broker_settings(
    broker: BrokerSettings,
    db: AsyncSession = Depends(get_db)
):
    """Update broker settings."""
    settings = await load_settings_from_db(db)
    existing_broker = settings.broker

    # Preserve masked values
    broker.oanda_api_key = preserve_if_masked(broker.oanda_api_key, existing_broker.oanda_api_key)
    broker.metaapi_token = preserve_if_masked(broker.metaapi_token, existing_broker.metaapi_token)
    broker.ig_api_key = preserve_if_masked(broker.ig_api_key, existing_broker.ig_api_key)
    broker.ig_password = preserve_if_masked(broker.ig_password, existing_broker.ig_password)
    broker.alpaca_api_key = preserve_if_masked(broker.alpaca_api_key, existing_broker.alpaca_api_key)
    broker.alpaca_secret_key = preserve_if_masked(broker.alpaca_secret_key, existing_broker.alpaca_secret_key)

    settings.broker = broker
    await save_settings_to_db(db, settings)
    apply_settings_to_env(settings)

    # Clear settings cache and reset all services to force reconnection with new broker
    clear_settings_cache()
    await BrokerFactory.reset_instance()
    await reset_trading_service()
    reset_price_streaming_service()  # Reset to pick up new broker for real-time prices

    return {"status": "success", "message": "Broker settings saved"}


@router.put("/ai", response_model=dict)
async def update_ai_settings(
    ai: AIProviderSettings,
    db: AsyncSession = Depends(get_db)
):
    """Update AI provider settings."""
    settings = await load_settings_from_db(db)
    existing_ai = settings.ai

    ai.aiml_api_key = preserve_if_masked(ai.aiml_api_key, existing_ai.aiml_api_key)
    ai.nvidia_api_key = preserve_if_masked(ai.nvidia_api_key, existing_ai.nvidia_api_key)
    ai.openai_api_key = preserve_if_masked(ai.openai_api_key, existing_ai.openai_api_key)
    ai.anthropic_api_key = preserve_if_masked(ai.anthropic_api_key, existing_ai.anthropic_api_key)
    ai.google_api_key = preserve_if_masked(ai.google_api_key, existing_ai.google_api_key)
    ai.groq_api_key = preserve_if_masked(ai.groq_api_key, existing_ai.groq_api_key)
    ai.mistral_api_key = preserve_if_masked(ai.mistral_api_key, existing_ai.mistral_api_key)

    settings.ai = ai
    await save_settings_to_db(db, settings)
    apply_settings_to_env(settings)

    # Clear settings cache and reinitialize AI service with new API keys
    clear_settings_cache()
    reset_ai_service()

    return {"status": "success", "message": "AI settings saved"}


@router.put("/risk", response_model=dict)
async def update_risk_settings(
    risk: RiskSettings,
    db: AsyncSession = Depends(get_db)
):
    """Update risk management settings."""
    settings = await load_settings_from_db(db)
    settings.risk = risk
    await save_settings_to_db(db, settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "Risk settings saved"}


@router.put("/notifications", response_model=dict)
async def update_notification_settings(
    notifications: NotificationSettings,
    db: AsyncSession = Depends(get_db)
):
    """Update notification settings."""
    settings = await load_settings_from_db(db)
    settings.notifications = notifications
    await save_settings_to_db(db, settings)
    apply_settings_to_env(settings)

    return {"status": "success", "message": "Notification settings saved"}


@router.post("/test-broker", response_model=dict)
async def test_broker_connection(db: AsyncSession = Depends(get_db)):
    """Test the broker connection with current settings."""
    settings = await load_settings_from_db(db)
    broker = settings.broker

    try:
        if broker.broker_type == "metatrader":
            if not broker.metaapi_token or not broker.metaapi_account_id:
                raise HTTPException(status_code=400, detail="MetaApi credentials not configured")

            # Test MetaApi connection with SSL verification disabled for cloud environments
            import httpx
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                response = await client.get(
                    f"https://mt-provisioning-api-v1.agiliumtrade.agiliumtrade.ai/users/current/accounts/{broker.metaapi_account_id}",
                    headers={"auth-token": broker.metaapi_token},
                )
                if response.status_code == 200:
                    account_info = response.json()
                    return {
                        "status": "success",
                        "message": "Connected to MetaTrader successfully",
                        "account_name": account_info.get("name", "Unknown"),
                        "platform": account_info.get("platform", broker.metaapi_platform),
                        "state": account_info.get("state", "Unknown"),
                    }
                elif response.status_code == 404:
                    error_data = response.json() if response.text else {}
                    raise HTTPException(
                        status_code=400,
                        detail=f"Account not found. Check your MetaApi Account ID. Error: {error_data.get('message', 'Unknown')}"
                    )
                elif response.status_code == 401:
                    raise HTTPException(status_code=400, detail="Invalid MetaApi Access Token")
                else:
                    raise HTTPException(status_code=400, detail=f"MetaApi error ({response.status_code}): {response.text}")

        elif broker.broker_type == "oanda":
            if not broker.oanda_api_key or not broker.oanda_account_id:
                raise HTTPException(status_code=400, detail="OANDA credentials not configured")

            # Test OANDA connection
            import httpx
            base_url = "https://api-fxpractice.oanda.com" if broker.oanda_environment == "practice" else "https://api-fxtrade.oanda.com"
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                response = await client.get(
                    f"{base_url}/v3/accounts/{broker.oanda_account_id}/summary",
                    headers={"Authorization": f"Bearer {broker.oanda_api_key}"},
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


@router.post("/init-db")
async def init_database(db: AsyncSession = Depends(get_db)):
    """Initialize database tables. Called on first startup."""
    from src.core.database import init_db
    await init_db()
    return {"status": "success", "message": "Database initialized"}
