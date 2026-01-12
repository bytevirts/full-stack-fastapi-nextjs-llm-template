{%- if cookiecutter.enable_billing %}
"""Alipay billing provider (placeholder)."""

from app.core.exceptions import ExternalServiceError


def create_checkout_session(*args, **kwargs):  # noqa: ANN002, ANN003
    """Alipay checkout placeholder."""
    raise ExternalServiceError(message="Alipay billing adapter not implemented yet")

{%- else %}
"""Alipay provider - not configured."""
{%- endif %}
