"""Billing schemas."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema, TimestampSchema


class BillingWalletRead(BaseSchema):
    """Wallet balances for a user."""

    monthly_remaining: int = Field(..., ge=0)
    prepaid_balance: int = Field(..., ge=0)


class BillingSubscriptionRead(BaseSchema):
    """Subscription details."""

    status: str
    plan_name: str | None = None
    monthly_credits: int = 0
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    provider: str | None = None


class BillingCreditPack(BaseSchema):
    """Available credit pack."""

    credits: int
    price_usd: float


class TokenLedgerRead(TimestampSchema, BaseSchema):
    """Token usage ledger entry."""

    id: UUID
    model_name: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int
    cost_credits: int
    overage_credits: int = 0


class BillingSummary(BaseSchema):
    """Billing summary response."""

    wallet: BillingWalletRead
    subscription: BillingSubscriptionRead | None
    credit_packs: list[BillingCreditPack]
    recent_ledger: list[TokenLedgerRead]


class CheckoutRequest(BaseSchema):
    """Checkout request."""

    kind: Literal["subscription", "credit_pack"]
    pack_credits: int | None = Field(default=None, description="Required for credit_pack")


class CheckoutResponse(BaseSchema):
    """Checkout response."""

    provider: str
    checkout_url: str
