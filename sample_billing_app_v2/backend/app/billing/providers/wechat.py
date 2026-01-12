
"""WeChat Pay billing provider (placeholder)."""

from app.core.exceptions import ExternalServiceError


def create_checkout_session(*args, **kwargs):  # noqa: ANN002, ANN003
    """WeChat Pay checkout placeholder."""
    raise ExternalServiceError(message="WeChat Pay billing adapter not implemented yet")
