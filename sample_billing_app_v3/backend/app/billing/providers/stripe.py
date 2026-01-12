"""Stripe billing provider (placeholder)."""

from app.core.exceptions import ExternalServiceError


def create_checkout_session(*args, **kwargs):
    """Stripe checkout placeholder."""
    raise ExternalServiceError(message="Stripe billing adapter not implemented yet")
