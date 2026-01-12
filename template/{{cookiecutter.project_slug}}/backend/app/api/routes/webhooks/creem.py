{%- if cookiecutter.enable_billing and cookiecutter.use_billing_creem and cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy %}
"""Creem webhook handler (PostgreSQL async)."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.billing.providers import creem
from app.core.config import settings
from app.db.session import get_db_context
from app.services.billing import BillingService

router = APIRouter()


def _resolve_pack_credits(product_id: str | None) -> int | None:
    if not product_id:
        return None
    for pack in settings.BILLING_CREDIT_PACKS:
        if pack.get("provider_product_id") == product_id:
            return int(pack.get("credits", 0))
    return None


@router.post("/webhooks/creem")
async def creem_webhook(request: Request) -> dict:
    """Handle Creem checkout.completed events."""
    payload = await request.body()
    signature = request.headers.get(creem.CREEM_SIGNATURE_HEADER, "")

    if not creem.verify_signature(payload, signature, settings.CREEM_WEBHOOK_SECRET):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = creem.parse_event(payload)
    if event.get("eventType") != "checkout.completed":
        return {"status": "ignored"}

    data = event.get("object", {})
    metadata = data.get("metadata") or {}
    subscription_meta = None
    if isinstance(data.get("subscription"), dict):
        subscription_meta = data["subscription"].get("metadata")
    if subscription_meta:
        metadata.update(subscription_meta)

    user_id_raw = metadata.get("user_id") or metadata.get("internal_customer_id")
    if not user_id_raw:
        return {"status": "ignored", "reason": "missing_user_id"}

    product = data.get("product") or {}
    order = data.get("order") or {}
    product_id = product.get("id")
    billing_type = product.get("billing_type") or order.get("type")
    amount_raw = order.get("amount")
    currency = order.get("currency")
    amount = None
    if isinstance(amount_raw, (int, float)):
        amount = float(amount_raw) / 100

    try:
        user_id = UUID(user_id_raw)
    except ValueError:
        return {"status": "ignored", "reason": "invalid_user_id"}

    async with get_db_context() as db:
        service = BillingService(db)

        if billing_type == "recurring" or product_id == settings.CREEM_SUBSCRIPTION_PRODUCT_ID:
            await service.grant_monthly_allowance(
                user_id=user_id,
                provider="creem",
                provider_subscription_id=(data.get("subscription") or {}).get("id")
                if isinstance(data.get("subscription"), dict)
                else None,
                status="active",
                plan_name=product.get("name"),
                current_period_start=None,
                current_period_end=None,
                metadata=metadata,
            )
            await service.record_subscription_payment(
                user_id=user_id,
                provider="creem",
                external_id=event.get("id", ""),
                amount=amount,
                currency=currency,
                metadata=metadata,
            )
        else:
            credits = _resolve_pack_credits(product_id)
            if not credits:
                return {"status": "ignored", "reason": "unknown_pack"}
            await service.apply_pack_purchase(
                user_id=user_id,
                provider="creem",
                external_id=event.get("id", ""),
                credits=credits,
                amount=amount,
                currency=currency,
                metadata=metadata,
            )

    return {"status": "ok"}

{%- elif cookiecutter.enable_billing and cookiecutter.use_billing_creem and cookiecutter.use_sqlite and cookiecutter.use_sqlalchemy %}
"""Creem webhook handler (SQLite sync)."""

from fastapi import APIRouter, HTTPException, Request

from app.billing.providers import creem
from app.core.config import settings
from app.db.session import get_db_session
from app.services.billing import BillingService

router = APIRouter()


def _resolve_pack_credits(product_id: str | None) -> int | None:
    if not product_id:
        return None
    for pack in settings.BILLING_CREDIT_PACKS:
        if pack.get("provider_product_id") == product_id:
            return int(pack.get("credits", 0))
    return None


@router.post("/webhooks/creem")
async def creem_webhook(request: Request) -> dict:
    """Handle Creem checkout.completed events."""
    payload = await request.body()
    signature = request.headers.get(creem.CREEM_SIGNATURE_HEADER, "")

    if not creem.verify_signature(payload, signature, settings.CREEM_WEBHOOK_SECRET):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = creem.parse_event(payload)
    if event.get("eventType") != "checkout.completed":
        return {"status": "ignored"}

    data = event.get("object", {})
    metadata = data.get("metadata") or {}
    subscription_meta = None
    if isinstance(data.get("subscription"), dict):
        subscription_meta = data["subscription"].get("metadata")
    if subscription_meta:
        metadata.update(subscription_meta)

    user_id = metadata.get("user_id") or metadata.get("internal_customer_id")
    if not user_id:
        return {"status": "ignored", "reason": "missing_user_id"}

    product = data.get("product") or {}
    order = data.get("order") or {}
    product_id = product.get("id")
    billing_type = product.get("billing_type") or order.get("type")
    amount_raw = order.get("amount")
    currency = order.get("currency")
    amount = None
    if isinstance(amount_raw, (int, float)):
        amount = float(amount_raw) / 100

    with get_db_session() as db:
        service = BillingService(db)

        if billing_type == "recurring" or product_id == settings.CREEM_SUBSCRIPTION_PRODUCT_ID:
            service.grant_monthly_allowance(
                user_id=user_id,
                provider="creem",
                provider_subscription_id=(data.get("subscription") or {}).get("id")
                if isinstance(data.get("subscription"), dict)
                else None,
                status="active",
                plan_name=product.get("name"),
                current_period_start=None,
                current_period_end=None,
                metadata=metadata,
            )
            service.record_subscription_payment(
                user_id=user_id,
                provider="creem",
                external_id=event.get("id", ""),
                amount=amount,
                currency=currency,
                metadata=metadata,
            )
        else:
            credits = _resolve_pack_credits(product_id)
            if not credits:
                return {"status": "ignored", "reason": "unknown_pack"}
            service.apply_pack_purchase(
                user_id=user_id,
                provider="creem",
                external_id=event.get("id", ""),
                credits=credits,
                amount=amount,
                currency=currency,
                metadata=metadata,
            )

    return {"status": "ok"}

{%- else %}
"""Creem webhook - not configured."""
{%- endif %}
