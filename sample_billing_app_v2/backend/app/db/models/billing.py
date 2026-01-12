
"""Billing models for token usage and payments."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base, TimestampMixin
from app.db.models.user import User


class CreditWallet(Base, TimestampMixin):
    """User credit balances (monthly + prepaid)."""

    __tablename__ = "credit_wallets"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True
    )
    monthly_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prepaid_balance: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<CreditWallet(user_id={self.user_id}, "
            f"monthly_remaining={self.monthly_remaining}, prepaid_balance={self.prepaid_balance})>"
        )


class Subscription(Base, TimestampMixin):
    """Subscription state for monthly credit grants."""

    __tablename__ = "subscriptions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="creem", index=True)
    provider_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    plan_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    monthly_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Subscription(user_id={self.user_id}, provider={self.provider}, status={self.status})>"


class TokenLedger(Base, TimestampMixin):
    """Ledger entry for token usage and cost."""

    __tablename__ = "token_ledgers"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overage_credits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provider_request_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<TokenLedger(user_id={self.user_id}, total_tokens={self.total_tokens}, "
            f"cost_credits={self.cost_credits})>"
        )


class PaymentTransaction(Base, TimestampMixin):
    """Payment transactions (subscriptions and credit packs)."""

    __tablename__ = "payment_transactions"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default="creem", index=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(50), default="credit_pack")
    status: Mapped[str] = mapped_column(String(50), default="completed")
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    credits_granted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)

    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<PaymentTransaction(user_id={self.user_id}, provider={self.provider}, "
            f"kind={self.kind}, status={self.status})>"
        )
