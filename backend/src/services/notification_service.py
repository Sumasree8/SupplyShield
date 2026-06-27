"""
Alert notification dispatch — Slack and email.

Channels are optional: each is used only when the relevant settings are
configured. Every successful send is recorded so the caller can persist it on
`Alert.notifications_sent` for the audit trail. Blocking I/O (SMTP) is offloaded
to a worker thread so this is safe to call from async request handlers.
"""
from __future__ import annotations

import asyncio
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import List, Optional

import httpx
import structlog

from src.config.settings import get_settings

log = structlog.get_logger()
settings = get_settings()


async def send_slack(text: str) -> bool:
    """Post a message to the configured Slack webhook. Returns True on success."""
    if not settings.SLACK_WEBHOOK_URL:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(settings.SLACK_WEBHOOK_URL, json={"text": text})
            resp.raise_for_status()
        return True
    except httpx.HTTPError as e:
        log.warning("notification.slack_failed", error=str(e))
        return False


def _send_email_sync(to_addrs: List[str], subject: str, body: str) -> bool:
    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
        server.starttls()
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
    return True


async def send_email(to_addrs: List[str], subject: str, body: str) -> bool:
    """Send an email via SMTP if configured. Returns True on success."""
    if not settings.SMTP_HOST or not to_addrs:
        return False
    try:
        return await asyncio.to_thread(_send_email_sync, to_addrs, subject, body)
    except Exception as e:  # smtplib raises a variety of exceptions
        log.warning("notification.email_failed", error=str(e))
        return False


async def dispatch_alert_notifications(
    *,
    title: str,
    body: str,
    email_recipients: Optional[List[str]] = None,
) -> List[dict]:
    """
    Send an alert across all configured channels and return a list of records
    describing what was sent — suitable for appending to Alert.notifications_sent.
    """
    sent: List[dict] = []
    now = datetime.now(timezone.utc).isoformat()

    if await send_slack(f"*{title}*\n{body}"):
        sent.append({"channel": "slack", "sent_at": now})

    if email_recipients and await send_email(email_recipients, title, body):
        sent.append({"channel": "email", "to": email_recipients, "sent_at": now})

    return sent
