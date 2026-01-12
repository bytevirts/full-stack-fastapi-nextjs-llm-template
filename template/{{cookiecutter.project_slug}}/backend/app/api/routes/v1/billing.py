{%- if cookiecutter.enable_billing and cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy and cookiecutter.use_jwt %}
"""Billing API routes (PostgreSQL async)."""

from fastapi import APIRouter, Depends

from app.api.deps import BillingSvc, get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.schemas.billing import BillingCreditPack, BillingSummary, CheckoutRequest, CheckoutResponse

router = APIRouter()


@router.get("/billing/summary", response_model=BillingSummary)
async def get_billing_summary(
    billing_service: BillingSvc,
    user: User = Depends(get_current_user),
) -> BillingSummary:
    """Get billing summary for the current user."""
    wallet = await billing_service.get_wallet(user.id)
    subscription = await billing_service.get_subscription(user.id)
    ledger = await billing_service.list_ledger(user.id, limit=20)
    packs = [BillingCreditPack(**pack) for pack in billing_service.get_credit_packs()]
    return BillingSummary(
        wallet=wallet,
        subscription=subscription,
        credit_packs=packs,
        recent_ledger=ledger,
    )


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    billing_service: BillingSvc,
    user: User = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a checkout session for subscriptions or credit packs."""
    checkout_url = await billing_service.create_checkout(
        user_id=user.id,
        user_email=user.email,
        kind=request.kind,
        pack_credits=request.pack_credits,
    )
    return CheckoutResponse(provider=settings.BILLING_PROVIDER, checkout_url=checkout_url)

{%- elif cookiecutter.enable_billing and cookiecutter.use_sqlite and cookiecutter.use_sqlalchemy and cookiecutter.use_jwt %}
"""Billing API routes (SQLite sync)."""

from fastapi import APIRouter, Depends

from app.api.deps import BillingSvc, get_current_user
from app.core.config import settings
from app.db.models.user import User
from app.schemas.billing import BillingCreditPack, BillingSummary, CheckoutRequest, CheckoutResponse

router = APIRouter()


@router.get("/billing/summary", response_model=BillingSummary)
def get_billing_summary(
    billing_service: BillingSvc,
    user: User = Depends(get_current_user),
) -> BillingSummary:
    """Get billing summary for the current user."""
    wallet = billing_service.get_wallet(user.id)
    subscription = billing_service.get_subscription(user.id)
    ledger = billing_service.list_ledger(user.id, limit=20)
    packs = [BillingCreditPack(**pack) for pack in billing_service.get_credit_packs()]
    return BillingSummary(
        wallet=wallet,
        subscription=subscription,
        credit_packs=packs,
        recent_ledger=ledger,
    )


@router.post("/billing/checkout", response_model=CheckoutResponse)
def create_checkout(
    request: CheckoutRequest,
    billing_service: BillingSvc,
    user: User = Depends(get_current_user),
) -> CheckoutResponse:
    """Create a checkout session for subscriptions or credit packs."""
    checkout_url = billing_service.create_checkout(
        user_id=user.id,
        user_email=user.email,
        kind=request.kind,
        pack_credits=request.pack_credits,
    )
    return CheckoutResponse(provider=settings.BILLING_PROVIDER, checkout_url=checkout_url)

{%- else %}
"""Billing API routes - not configured."""
{%- endif %}
