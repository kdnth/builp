"""Outbound transactional email through Resend's HTTP API.

Delivery is best effort. Every feedback submission is written to the
database before a send is attempted, so a bounced or unconfigured send
loses a notification, never the report itself.
"""

import logging

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_TIMEOUT_SECONDS = 10.0


def send_email(
    *,
    settings: Settings,
    to: str,
    subject: str,
    body: str,
    reply_to: str | None = None,
) -> bool:
    """Returns whether the message was handed off to Resend."""
    if not settings.email_configured:
        logger.info(
            "Email is not configured; skipped sending %r to %s", subject, to
        )
        return False

    payload: dict[str, object] = {
        "from": settings.feedback_from_email,
        "to": [to],
        "subject": subject,
        "text": body,
    }
    if reply_to:
        payload["reply_to"] = reply_to

    try:
        response = httpx.post(
            _RESEND_ENDPOINT,
            json=payload,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        # Logged without the payload: feedback bodies are user-submitted text
        # and reply_to is a personal address.
        logger.exception("Could not send %r to %s", subject, to)
        return False
    return True
