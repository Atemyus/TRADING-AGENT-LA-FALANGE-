"""
Whop webhook routes for receiving payment notifications.
Handles order creation and automatic license generation.
"""

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.models import License, LicenseStatus, WhopOrder, WhopOrderStatus, WhopProduct

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# Webhook Payload Models
# ============================================================================

class WhopWebhookPayload(BaseModel):
    """Whop webhook payload structure."""
    action: str  # membership.went_valid, membership.went_invalid, payment.succeeded, etc.
    data: dict


# ============================================================================
# Helper Functions
# ============================================================================

def verify_whop_signature(payload: bytes, signature: str | None, secret: str) -> bool:
    """Verify Whop webhook signature."""
    if not signature or not secret:
        return False

    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


async def create_license_for_order(
    db: AsyncSession,
    order: WhopOrder,
    product: WhopProduct | None
) -> License | None:
    """Create a license for a completed order."""
    # Determine license parameters
    if product:
        duration_days = product.license_duration_days
        max_uses = product.license_max_uses
        name = product.license_name_template.format(
            product_name=product.name,
            customer_email=order.customer_email,
            order_id=order.whop_order_id
        )
    else:
        # Default values if product not mapped
        duration_days = 30
        max_uses = 1
        name = f"Whop License - {order.product_name}"

    # Create license
    license = License(
        key=License.generate_key(prefix="WHOP"),
        name=name,
        description=f"Auto-generated from Whop order {order.whop_order_id}",
        max_uses=max_uses,
        expires_at=datetime.now(UTC) + timedelta(days=duration_days),
        status=LicenseStatus.ACTIVE,
        is_active=True,
    )

    db.add(license)
    await db.flush()
    await db.refresh(license)

    # Link license to order
    order.license_id = license.id
    order.license_created = True

    logger.info(f"Created license {license.key} for order {order.whop_order_id}")

    return license


# ============================================================================
# Webhook Endpoints
# ============================================================================

@router.post("/webhook")
async def whop_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_whop_signature: str | None = Header(None, alias="X-Whop-Signature"),
):
    """
    Handle Whop webhooks.

    Supported events:
    - membership.went_valid: New purchase/subscription activated
    - membership.went_invalid: Subscription cancelled/expired
    - payment.succeeded: Payment completed
    - payment.failed: Payment failed
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature in production
    whop_secret = getattr(settings, 'WHOP_WEBHOOK_SECRET', None)
    if whop_secret and not verify_whop_signature(body, x_whop_signature, whop_secret):
        logger.warning("Invalid Whop webhook signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload"
        )

    action = payload.get("action", "")
    data = payload.get("data", {})

    logger.info(f"Received Whop webhook: {action}")

    # Handle different webhook events
    if action == "membership.went_valid":
        await handle_membership_valid(db, data, body.decode())
    elif action == "membership.went_invalid":
        await handle_membership_invalid(db, data)
    elif action == "payment.succeeded":
        await handle_payment_succeeded(db, data, body.decode())
    elif action == "payment.failed":
        await handle_payment_failed(db, data)
    else:
        logger.info(f"Unhandled Whop webhook action: {action}")

    await db.commit()

    return {"status": "ok", "action": action}


async def handle_membership_valid(db: AsyncSession, data: dict, raw_data: str):
    """Handle new membership/purchase."""
    # Extract relevant data
    membership_id = data.get("id", "")
    user_data = data.get("user", {})
    product_data = data.get("product", {})
    plan_data = data.get("plan", {})

    # Check if order already exists
    existing = await db.execute(
        select(WhopOrder).where(WhopOrder.whop_membership_id == membership_id)
    )
    if existing.scalar_one_or_none():
        logger.info(f"Order for membership {membership_id} already exists")
        return

    # Find matching product configuration
    product_result = await db.execute(
        select(WhopProduct).where(WhopProduct.whop_product_id == product_data.get("id", ""))
    )
    product = product_result.scalar_one_or_none()

    # Create order record
    order = WhopOrder(
        whop_order_id=f"mem_{membership_id}",
        whop_membership_id=membership_id,
        whop_user_id=user_data.get("id"),
        customer_email=user_data.get("email", "unknown@example.com"),
        customer_name=user_data.get("name"),
        customer_username=user_data.get("username"),
        product_id=product.id if product else None,
        product_name=product_data.get("name", "Unknown Product"),
        plan_name=plan_data.get("name"),
        amount=float(plan_data.get("initial_price", 0)) / 100,  # Whop prices are in cents
        currency=plan_data.get("currency", "EUR").upper(),
        payment_method=data.get("payment_method"),
        status=WhopOrderStatus.COMPLETED,
        raw_webhook_data=raw_data,
        whop_created_at=datetime.now(UTC),
    )

    db.add(order)
    await db.flush()
    await db.refresh(order)

    # Auto-create license
    await create_license_for_order(db, order, product)

    logger.info(f"Created order {order.id} for membership {membership_id}")


async def handle_membership_invalid(db: AsyncSession, data: dict):
    """Handle membership cancellation/expiration."""
    membership_id = data.get("id", "")

    # Find the order
    result = await db.execute(
        select(WhopOrder).where(WhopOrder.whop_membership_id == membership_id)
    )
    order = result.scalar_one_or_none()

    if order:
        order.status = WhopOrderStatus.REFUNDED

        # Optionally revoke the license
        if order.license:
            order.license.status = LicenseStatus.REVOKED
            order.license.is_active = False

        logger.info(f"Marked order {order.id} as refunded/cancelled")


async def handle_payment_succeeded(db: AsyncSession, data: dict, raw_data: str):
    """Handle successful payment (for one-time purchases)."""
    payment_id = data.get("id", "")
    user_data = data.get("user", {})
    product_data = data.get("product", {})

    # Check if order already exists
    existing = await db.execute(
        select(WhopOrder).where(WhopOrder.whop_order_id == f"pay_{payment_id}")
    )
    if existing.scalar_one_or_none():
        logger.info(f"Order for payment {payment_id} already exists")
        return

    # Find matching product configuration
    product_result = await db.execute(
        select(WhopProduct).where(WhopProduct.whop_product_id == product_data.get("id", ""))
    )
    product = product_result.scalar_one_or_none()

    # Create order record
    order = WhopOrder(
        whop_order_id=f"pay_{payment_id}",
        whop_user_id=user_data.get("id"),
        customer_email=user_data.get("email", "unknown@example.com"),
        customer_name=user_data.get("name"),
        customer_username=user_data.get("username"),
        product_id=product.id if product else None,
        product_name=product_data.get("name", "Unknown Product"),
        amount=float(data.get("final_amount", 0)) / 100,
        currency=data.get("currency", "EUR").upper(),
        payment_method=data.get("payment_method"),
        status=WhopOrderStatus.COMPLETED,
        raw_webhook_data=raw_data,
        whop_created_at=datetime.now(UTC),
    )

    db.add(order)
    await db.flush()
    await db.refresh(order)

    # Auto-create license
    await create_license_for_order(db, order, product)

    logger.info(f"Created order {order.id} for payment {payment_id}")


async def handle_payment_failed(db: AsyncSession, data: dict):
    """Handle failed payment."""
    payment_id = data.get("id", "")

    # Find the order if it exists
    result = await db.execute(
        select(WhopOrder).where(WhopOrder.whop_order_id == f"pay_{payment_id}")
    )
    order = result.scalar_one_or_none()

    if order:
        order.status = WhopOrderStatus.FAILED
        logger.info(f"Marked order {order.id} as failed")
