"""Billing repository (PostgreSQL async)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import CreditWallet, PaymentTransaction, Subscription, TokenLedger


async def get_wallet_by_user_id(db: AsyncSession, user_id: UUID) -> CreditWallet | None:
    """Get wallet by user ID."""
    result = await db.execute(select(CreditWallet).where(CreditWallet.user_id == user_id))
    return result.scalar_one_or_none()


async def create_wallet(
    db: AsyncSession,
    *,
    user_id: UUID,
    monthly_remaining: int = 0,
    prepaid_balance: int = 0,
) -> CreditWallet:
    """Create a wallet for a user."""
    wallet = CreditWallet(
        user_id=user_id,
        monthly_remaining=monthly_remaining,
        prepaid_balance=prepaid_balance,
    )
    db.add(wallet)
    await db.flush()
    await db.refresh(wallet)
    return wallet


async def update_wallet(db: AsyncSession, wallet: CreditWallet) -> CreditWallet:
    """Persist wallet changes."""
    db.add(wallet)
    await db.flush()
    await db.refresh(wallet)
    return wallet


async def get_latest_subscription(
    db: AsyncSession,
    user_id: UUID,
) -> Subscription | None:
    """Get the most recent subscription for a user."""
    result = await db.execute(
        select(Subscription)
        .where(Subscription.user_id == user_id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def upsert_subscription(
    db: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
    provider_subscription_id: str | None,
    status: str,
    plan_name: str | None,
    monthly_credits: int,
    current_period_start: datetime | None,
    current_period_end: datetime | None,
    metadata: dict | None,
) -> Subscription:
    """Create or update the latest subscription for a user."""
    subscription = await get_latest_subscription(db, user_id)
    if subscription:
        subscription.provider = provider
        subscription.provider_subscription_id = provider_subscription_id
        subscription.status = status
        subscription.plan_name = plan_name
        subscription.monthly_credits = monthly_credits
        subscription.current_period_start = current_period_start
        subscription.current_period_end = current_period_end
        subscription.metadata_ = metadata
        db.add(subscription)
        await db.flush()
        await db.refresh(subscription)
        return subscription

    subscription = Subscription(
        user_id=user_id,
        provider=provider,
        provider_subscription_id=provider_subscription_id,
        status=status,
        plan_name=plan_name,
        monthly_credits=monthly_credits,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        metadata_=metadata,
    )
    db.add(subscription)
    await db.flush()
    await db.refresh(subscription)
    return subscription


async def create_ledger_entry(
    db: AsyncSession,
    *,
    user_id: UUID,
    model_name: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int,
    cost_credits: int,
    overage_credits: int,
    provider_request_id: str | None,
    metadata: dict | None,
) -> TokenLedger:
    """Create a token usage ledger entry."""
    entry = TokenLedger(
        user_id=user_id,
        model_name=model_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_credits=cost_credits,
        overage_credits=overage_credits,
        provider_request_id=provider_request_id,
        metadata_=metadata,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def list_ledger_entries(
    db: AsyncSession,
    *,
    user_id: UUID,
    limit: int = 20,
) -> list[TokenLedger]:
    """List recent ledger entries for a user."""
    result = await db.execute(
        select(TokenLedger)
        .where(TokenLedger.user_id == user_id)
        .order_by(desc(TokenLedger.created_at))
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_transaction_by_external_id(
    db: AsyncSession,
    external_id: str,
) -> PaymentTransaction | None:
    """Get payment transaction by external ID."""
    result = await db.execute(
        select(PaymentTransaction).where(PaymentTransaction.external_id == external_id)
    )
    return result.scalar_one_or_none()


async def create_transaction(
    db: AsyncSession,
    *,
    user_id: UUID,
    provider: str,
    external_id: str,
    kind: str,
    status: str,
    amount: float | None,
    currency: str | None,
    credits_granted: int,
    metadata: dict | None,
) -> PaymentTransaction:
    """Create a payment transaction entry."""
    transaction = PaymentTransaction(
        user_id=user_id,
        provider=provider,
        external_id=external_id,
        kind=kind,
        status=status,
        amount=amount,
        currency=currency,
        credits_granted=credits_granted,
        metadata_=metadata,
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)
    return transaction
