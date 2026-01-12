"""Alipay billing provider (placeholder)."""

from app.core.exceptions import ExternalServiceError


def create_checkout_session(*args, **kwargs):
    """Alipay checkout placeholder."""
    raise ExternalServiceError(message="Alipay billing adapter not implemented yet")
