{%- if cookiecutter.enable_billing %}
"""Creem billing provider integration."""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ExternalServiceError

CREEM_SIGNATURE_HEADER = "creem-signature"


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Creem webhook signature using HMAC-SHA256."""
    if not secret:
        return False
    computed = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, signature)


def parse_event(payload: bytes) -> dict[str, Any]:
    """Parse a webhook payload."""
    return json.loads(payload.decode("utf-8"))


async def create_checkout_session(
    *,
    product_id: str,
    customer_email: str | None,
    metadata: dict[str, Any] | None,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Create a Creem checkout session (async)."""
    if not settings.CREEM_API_KEY:
        raise ExternalServiceError(message="CREEM_API_KEY is not configured")

    payload: dict[str, Any] = {
        "product_id": product_id,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata or {},
    }
    if customer_email:
        payload["customer"] = {"email": customer_email}

    url = f"{settings.CREEM_API_BASE_URL}/v1/checkouts"
    headers = {"x-api-key": settings.CREEM_API_KEY}

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ExternalServiceError(
                message=f"Creem checkout failed: {response.text}",
                details={"status": response.status_code},
            )
        return response.json()


def create_checkout_session_sync(
    *,
    product_id: str,
    customer_email: str | None,
    metadata: dict[str, Any] | None,
    success_url: str,
    cancel_url: str,
) -> dict[str, Any]:
    """Create a Creem checkout session (sync)."""
    if not settings.CREEM_API_KEY:
        raise ExternalServiceError(message="CREEM_API_KEY is not configured")

    payload: dict[str, Any] = {
        "product_id": product_id,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": metadata or {},
    }
    if customer_email:
        payload["customer"] = {"email": customer_email}

    url = f"{settings.CREEM_API_BASE_URL}/v1/checkouts"
    headers = {"x-api-key": settings.CREEM_API_KEY}

    with httpx.Client(timeout=15) as client:
        response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 400:
            raise ExternalServiceError(
                message=f"Creem checkout failed: {response.text}",
                details={"status": response.status_code},
            )
        return response.json()

{%- else %}
"""Creem provider - not configured."""
{%- endif %}
