"""Async email sender using stdlib smtplib via asyncio.to_thread."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import settings

logger = logging.getLogger(__name__)


def _send_sync(subject: str, body: str, to: str) -> None:
    """Synchronous SMTP send — runs in a thread pool."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_user
    msg["To"] = to
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        server.ehlo()
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, [to], msg.as_string())


async def send_email(subject: str, body: str, to: str | None = None) -> bool:
    """Send an email; returns True on success, False if skipped or failed.

    Skips silently when SMTP credentials are not configured.
    """
    recipient = to or settings.alert_email_to
    if not all([settings.smtp_user, settings.smtp_password, recipient]):
        logger.info("send_email: SMTP not configured, skipping")
        return False
    try:
        await asyncio.to_thread(_send_sync, subject, body, recipient)
        logger.info("send_email: sent '%s' to %s", subject, recipient)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("send_email: failed — %s", exc)
        return False
