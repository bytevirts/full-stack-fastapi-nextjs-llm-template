
"""Stripe billing provider (placeholder)."""

from app.core.exceptions import ExternalServiceError


def create_checkout_session(*args, **kwargs):  # noqa: ANN002, ANN003
    """Stripe checkout placeholder."""
    raise ExternalServiceError(message="Stripe billing adapter not implemented yet")
