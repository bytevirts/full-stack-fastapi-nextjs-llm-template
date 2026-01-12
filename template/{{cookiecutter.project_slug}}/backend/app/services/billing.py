{%- if cookiecutter.enable_billing and cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy %}
"""Billing service (PostgreSQL async)."""

from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.providers import creem
from app.core.config import settings
from app.core.exceptions import BadRequestError, PaymentRequiredError
from app.db.models.billing import CreditWallet, Subscription, TokenLedger
from app.repositories import billing_repo


def estimate_tokens_from_text(text: str) -> int:
    """Rough token estimation based on character count."""
    if not text:
        return 0
    chars_per_token = max(settings.BILLING_CHARS_PER_TOKEN, 1)
    return max(1, math.ceil(len(text) / chars_per_token))


def estimate_prompt_tokens(history: list[dict[str, str]], user_message: str) -> int:
    """Estimate prompt tokens using history + current message."""
    total_chars = sum(len(msg.get("content", "")) for msg in history) + len(user_message)
    if total_chars <= 0:
        return 0
    chars_per_token = max(settings.BILLING_CHARS_PER_TOKEN, 1)
    return max(1, math.ceil(total_chars / chars_per_token))


def get_model_multiplier(model_name: str | None) -> float:
    """Get the billing multiplier for a model."""
    multipliers = settings.BILLING_MODEL_MULTIPLIERS
    if model_name and model_name in multipliers:
        return float(multipliers[model_name])
    return float(multipliers.get("default", 1.0))


def calculate_cost_credits(total_tokens: int, model_name: str | None) -> int:
    """Convert token usage to billable credits."""
    if total_tokens <= 0:
        return 0
    tokens_per_credit = max(settings.BILLING_TOKENS_PER_CREDIT, 1)
    multiplier = get_model_multiplier(model_name)
    return math.ceil((total_tokens / tokens_per_credit) * multiplier)


class BillingService:
    """Service for billing, credits, and usage tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_wallet(self, user_id: UUID) -> CreditWallet:
        """Fetch or create a wallet for the user."""
        wallet = await billing_repo.get_wallet_by_user_id(self.db, user_id)
        if not wallet:
            wallet = await billing_repo.create_wallet(self.db, user_id=user_id)
        return wallet

    async def get_subscription(self, user_id: UUID) -> Subscription | None:
        """Get latest subscription for a user."""
        return await billing_repo.get_latest_subscription(self.db, user_id)

    async def list_ledger(self, user_id: UUID, limit: int = 20) -> list[TokenLedger]:
        """List recent token ledger entries."""
        return await billing_repo.list_ledger_entries(self.db, user_id=user_id, limit=limit)

    def get_credit_packs(self) -> list[dict]:
        """Return configured credit packs."""
        return settings.BILLING_CREDIT_PACKS

    async def precheck(self, user_id: UUID, model_name: str | None, estimated_tokens: int) -> int:
        """Ensure user has enough credits for estimated usage."""
        wallet = await self.get_wallet(user_id)
        cost = calculate_cost_credits(estimated_tokens, model_name)
        available = wallet.monthly_remaining + wallet.prepaid_balance
        if available < cost:
            raise PaymentRequiredError(
                message="Insufficient credits for this request",
                details={"required_credits": cost, "available_credits": available},
            )
        return cost

    async def commit_usage(
        self,
        *,
        user_id: UUID,
        model_name: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int,
        provider_request_id: str | None = None,
        metadata: dict | None = None,
    ) -> TokenLedger:
        """Deduct credits and record token usage."""
        wallet = await self.get_wallet(user_id)
        cost = calculate_cost_credits(total_tokens, model_name)

        monthly_deducted = min(wallet.monthly_remaining, cost)
        remaining = cost - monthly_deducted
        prepaid_deducted = min(wallet.prepaid_balance, remaining)
        overage = cost - monthly_deducted - prepaid_deducted

        wallet.monthly_remaining -= monthly_deducted
        wallet.prepaid_balance -= prepaid_deducted
        await billing_repo.update_wallet(self.db, wallet)

        return await billing_repo.create_ledger_entry(
            self.db,
            user_id=user_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_credits=cost,
            overage_credits=overage,
            provider_request_id=provider_request_id,
            metadata=metadata,
        )

    async def grant_monthly_allowance(
        self,
        *,
        user_id: UUID,
        provider: str,
        provider_subscription_id: str | None,
        status: str,
        plan_name: str | None,
        current_period_start: datetime | None,
        current_period_end: datetime | None,
        metadata: dict | None,
    ) -> Subscription:
        """Grant monthly credits and upsert subscription."""
        wallet = await self.get_wallet(user_id)
        wallet.monthly_remaining = settings.BILLING_MONTHLY_CREDITS
        await billing_repo.update_wallet(self.db, wallet)

        return await billing_repo.upsert_subscription(
            self.db,
            user_id=user_id,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            status=status,
            plan_name=plan_name,
            monthly_credits=settings.BILLING_MONTHLY_CREDITS,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            metadata=metadata,
        )

    async def apply_pack_purchase(
        self,
        *,
        user_id: UUID,
        provider: str,
        external_id: str,
        credits: int,
        amount: float | None,
        currency: str | None,
        metadata: dict | None,
    ) -> None:
        """Add prepaid credits and record transaction."""
        existing = await billing_repo.get_transaction_by_external_id(self.db, external_id)
        if existing:
            return

        wallet = await self.get_wallet(user_id)
        wallet.prepaid_balance += credits
        await billing_repo.update_wallet(self.db, wallet)

        await billing_repo.create_transaction(
            self.db,
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            kind="credit_pack",
            status="completed",
            amount=amount,
            currency=currency,
            credits_granted=credits,
            metadata=metadata,
        )

    async def record_subscription_payment(
        self,
        *,
        user_id: UUID,
        provider: str,
        external_id: str,
        amount: float | None,
        currency: str | None,
        metadata: dict | None,
    ) -> None:
        """Record a subscription payment transaction."""
        existing = await billing_repo.get_transaction_by_external_id(self.db, external_id)
        if existing:
            return

        await billing_repo.create_transaction(
            self.db,
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            kind="subscription",
            status="completed",
            amount=amount,
            currency=currency,
            credits_granted=settings.BILLING_MONTHLY_CREDITS,
            metadata=metadata,
        )

    async def create_checkout(
        self,
        *,
        user_id: UUID,
        user_email: str | None,
        kind: str,
        pack_credits: int | None = None,
    ) -> str:
        """Create a checkout session and return the checkout URL."""
        provider = settings.BILLING_PROVIDER
        if provider != "creem":
            raise BadRequestError(message=f"Billing provider '{provider}' not configured yet")

        metadata = {"user_id": str(user_id)}
        if kind == "subscription":
            product_id = settings.CREEM_SUBSCRIPTION_PRODUCT_ID
            if not product_id:
                raise BadRequestError(message="CREEM_SUBSCRIPTION_PRODUCT_ID is not set")
        elif kind == "credit_pack":
            if pack_credits is None:
                raise BadRequestError(message="pack_credits is required for credit_pack checkout")
            pack = next(
                (
                    item
                    for item in settings.BILLING_CREDIT_PACKS
                    if int(item.get("credits", 0)) == int(pack_credits)
                ),
                None,
            )
            if not pack:
                raise BadRequestError(message="Unknown credit pack selected")
            product_id = pack.get("provider_product_id") or ""
            if not product_id:
                raise BadRequestError(message="Credit pack product_id is not configured")
        else:
            raise BadRequestError(message="Invalid checkout type")

        response = await creem.create_checkout_session(
            product_id=product_id,
            customer_email=user_email,
            metadata=metadata,
            success_url=settings.CREEM_SUCCESS_URL,
            cancel_url=settings.CREEM_CANCEL_URL,
        )
        return response["checkout_url"]

{%- elif cookiecutter.enable_billing and cookiecutter.use_sqlite and cookiecutter.use_sqlalchemy %}
"""Billing service (SQLite sync)."""

from __future__ import annotations

import math
from datetime import datetime

from sqlalchemy.orm import Session

from app.billing.providers import creem
from app.core.config import settings
from app.core.exceptions import BadRequestError, PaymentRequiredError
from app.db.models.billing import CreditWallet, Subscription, TokenLedger
from app.repositories import billing_repo


def estimate_tokens_from_text(text: str) -> int:
    """Rough token estimation based on character count."""
    if not text:
        return 0
    chars_per_token = max(settings.BILLING_CHARS_PER_TOKEN, 1)
    return max(1, math.ceil(len(text) / chars_per_token))


def estimate_prompt_tokens(history: list[dict[str, str]], user_message: str) -> int:
    """Estimate prompt tokens using history + current message."""
    total_chars = sum(len(msg.get("content", "")) for msg in history) + len(user_message)
    if total_chars <= 0:
        return 0
    chars_per_token = max(settings.BILLING_CHARS_PER_TOKEN, 1)
    return max(1, math.ceil(total_chars / chars_per_token))


def get_model_multiplier(model_name: str | None) -> float:
    """Get the billing multiplier for a model."""
    multipliers = settings.BILLING_MODEL_MULTIPLIERS
    if model_name and model_name in multipliers:
        return float(multipliers[model_name])
    return float(multipliers.get("default", 1.0))


def calculate_cost_credits(total_tokens: int, model_name: str | None) -> int:
    """Convert token usage to billable credits."""
    if total_tokens <= 0:
        return 0
    tokens_per_credit = max(settings.BILLING_TOKENS_PER_CREDIT, 1)
    multiplier = get_model_multiplier(model_name)
    return math.ceil((total_tokens / tokens_per_credit) * multiplier)


class BillingService:
    """Service for billing, credits, and usage tracking."""

    def __init__(self, db: Session):
        self.db = db

    def get_wallet(self, user_id: str) -> CreditWallet:
        """Fetch or create a wallet for the user."""
        wallet = billing_repo.get_wallet_by_user_id(self.db, user_id)
        if not wallet:
            wallet = billing_repo.create_wallet(self.db, user_id=user_id)
        return wallet

    def get_subscription(self, user_id: str) -> Subscription | None:
        """Get latest subscription for a user."""
        return billing_repo.get_latest_subscription(self.db, user_id)

    def list_ledger(self, user_id: str, limit: int = 20) -> list[TokenLedger]:
        """List recent token ledger entries."""
        return billing_repo.list_ledger_entries(self.db, user_id=user_id, limit=limit)

    def get_credit_packs(self) -> list[dict]:
        """Return configured credit packs."""
        return settings.BILLING_CREDIT_PACKS

    def precheck(self, user_id: str, model_name: str | None, estimated_tokens: int) -> int:
        """Ensure user has enough credits for estimated usage."""
        wallet = self.get_wallet(user_id)
        cost = calculate_cost_credits(estimated_tokens, model_name)
        available = wallet.monthly_remaining + wallet.prepaid_balance
        if available < cost:
            raise PaymentRequiredError(
                message="Insufficient credits for this request",
                details={"required_credits": cost, "available_credits": available},
            )
        return cost

    def commit_usage(
        self,
        *,
        user_id: str,
        model_name: str | None,
        prompt_tokens: int | None,
        completion_tokens: int | None,
        total_tokens: int,
        provider_request_id: str | None = None,
        metadata: dict | None = None,
    ) -> TokenLedger:
        """Deduct credits and record token usage."""
        wallet = self.get_wallet(user_id)
        cost = calculate_cost_credits(total_tokens, model_name)

        monthly_deducted = min(wallet.monthly_remaining, cost)
        remaining = cost - monthly_deducted
        prepaid_deducted = min(wallet.prepaid_balance, remaining)
        overage = cost - monthly_deducted - prepaid_deducted

        wallet.monthly_remaining -= monthly_deducted
        wallet.prepaid_balance -= prepaid_deducted
        billing_repo.update_wallet(self.db, wallet)

        return billing_repo.create_ledger_entry(
            self.db,
            user_id=user_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_credits=cost,
            overage_credits=overage,
            provider_request_id=provider_request_id,
            metadata=metadata,
        )

    def grant_monthly_allowance(
        self,
        *,
        user_id: str,
        provider: str,
        provider_subscription_id: str | None,
        status: str,
        plan_name: str | None,
        current_period_start: datetime | None,
        current_period_end: datetime | None,
        metadata: dict | None,
    ) -> Subscription:
        """Grant monthly credits and upsert subscription."""
        wallet = self.get_wallet(user_id)
        wallet.monthly_remaining = settings.BILLING_MONTHLY_CREDITS
        billing_repo.update_wallet(self.db, wallet)

        return billing_repo.upsert_subscription(
            self.db,
            user_id=user_id,
            provider=provider,
            provider_subscription_id=provider_subscription_id,
            status=status,
            plan_name=plan_name,
            monthly_credits=settings.BILLING_MONTHLY_CREDITS,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            metadata=metadata,
        )

    def apply_pack_purchase(
        self,
        *,
        user_id: str,
        provider: str,
        external_id: str,
        credits: int,
        amount: float | None,
        currency: str | None,
        metadata: dict | None,
    ) -> None:
        """Add prepaid credits and record transaction."""
        existing = billing_repo.get_transaction_by_external_id(self.db, external_id)
        if existing:
            return

        wallet = self.get_wallet(user_id)
        wallet.prepaid_balance += credits
        billing_repo.update_wallet(self.db, wallet)

        billing_repo.create_transaction(
            self.db,
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            kind="credit_pack",
            status="completed",
            amount=amount,
            currency=currency,
            credits_granted=credits,
            metadata=metadata,
        )

    def record_subscription_payment(
        self,
        *,
        user_id: str,
        provider: str,
        external_id: str,
        amount: float | None,
        currency: str | None,
        metadata: dict | None,
    ) -> None:
        """Record a subscription payment transaction."""
        existing = billing_repo.get_transaction_by_external_id(self.db, external_id)
        if existing:
            return

        billing_repo.create_transaction(
            self.db,
            user_id=user_id,
            provider=provider,
            external_id=external_id,
            kind="subscription",
            status="completed",
            amount=amount,
            currency=currency,
            credits_granted=settings.BILLING_MONTHLY_CREDITS,
            metadata=metadata,
        )

    def create_checkout(
        self,
        *,
        user_id: str,
        user_email: str | None,
        kind: str,
        pack_credits: int | None = None,
    ) -> str:
        """Create a checkout session and return the checkout URL."""
        provider = settings.BILLING_PROVIDER
        if provider != "creem":
            raise BadRequestError(message=f"Billing provider '{provider}' not configured yet")

        metadata = {"user_id": str(user_id)}
        if kind == "subscription":
            product_id = settings.CREEM_SUBSCRIPTION_PRODUCT_ID
            if not product_id:
                raise BadRequestError(message="CREEM_SUBSCRIPTION_PRODUCT_ID is not set")
        elif kind == "credit_pack":
            if pack_credits is None:
                raise BadRequestError(message="pack_credits is required for credit_pack checkout")
            pack = next(
                (
                    item
                    for item in settings.BILLING_CREDIT_PACKS
                    if int(item.get("credits", 0)) == int(pack_credits)
                ),
                None,
            )
            if not pack:
                raise BadRequestError(message="Unknown credit pack selected")
            product_id = pack.get("provider_product_id") or ""
            if not product_id:
                raise BadRequestError(message="Credit pack product_id is not configured")
        else:
            raise BadRequestError(message="Invalid checkout type")

        response = creem.create_checkout_session_sync(
            product_id=product_id,
            customer_email=user_email,
            metadata=metadata,
            success_url=settings.CREEM_SUCCESS_URL,
            cancel_url=settings.CREEM_CANCEL_URL,
        )
        return response["checkout_url"]

{%- else %}
"""Billing service - not configured."""
{%- endif %}
