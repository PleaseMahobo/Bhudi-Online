"""Email delivery via Resend (preferred) with SMTP fallback.

Resend uses HTTPS (works reliably on Railway).
SMTP is only used when Resend is not configured.
"""
from __future__ import annotations

import base64
import logging
import random
import re
import smtplib
import ssl
import time
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any, Sequence

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")

_RETRYABLE_SMTP_CODES = frozenset(range(400, 500))
_RETRYABLE_EXC_TYPES = (
    smtplib.SMTPServerDisconnected,
    smtplib.SMTPConnectError,
    smtplib.SMTPHeloError,
    TimeoutError,
    ConnectionError,
    OSError,
)

RESEND_API_URL = "https://api.resend.com/emails"


def is_valid_email(addr: str) -> bool:
    return bool(addr and _EMAIL_RE.match(addr.strip()))


def normalize_recipients(raw: Sequence[Any] | None) -> list[str]:
    if not raw:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        if isinstance(item, dict):
            addr = str(item.get("email") or item.get("address") or "").strip()
        else:
            addr = str(item).strip()
        if not addr or not is_valid_email(addr):
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(addr)
    return out


def is_retryable_error(exc: BaseException) -> bool:
    if isinstance(exc, smtplib.SMTPResponseException):
        return int(getattr(exc, "smtp_code", 0) or 0) in _RETRYABLE_SMTP_CODES
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return False
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return False
    if isinstance(exc, smtplib.SMTPDataError):
        code = int(getattr(exc, "smtp_code", 0) or 0)
        return code in _RETRYABLE_SMTP_CODES
    if isinstance(exc, _RETRYABLE_EXC_TYPES):
        return True
    if isinstance(exc, smtplib.SMTPException):
        return True
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (408, 429, 500, 502, 503, 504)
    return False


@dataclass
class EmailDeliveryResult:
    ok: bool
    recipients: list[str] = field(default_factory=list)
    message_id: str | None = None
    error: str | None = None
    skipped: bool = False
    attempts: int = 0
    retried: bool = False
    last_error: str | None = None
    provider: str | None = None


class EmailService:
    """Resend-first email client with optional SMTP fallback."""

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool | None = None,
        use_ssl: bool | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        enabled: bool | None = None,
        max_retries: int | None = None,
        retry_base_delay: float | None = None,
        retry_max_delay: float | None = None,
        resend_api_key: str | None = None,
        resend_from_email: str | None = None,
        resend_from_name: str | None = None,
        resend_enabled: bool | None = None,
    ) -> None:
        self.resend_api_key = resend_api_key if resend_api_key is not None else settings.RESEND_API_KEY
        self.resend_from_email = resend_from_email if resend_from_email is not None else (settings.RESEND_FROM_EMAIL or settings.SMTP_FROM_EMAIL)
        self.resend_from_name = resend_from_name if resend_from_name is not None else (settings.RESEND_FROM_NAME or settings.SMTP_FROM_NAME or "Bhudi RMM")
        self.resend_enabled = resend_enabled if resend_enabled is not None else settings.RESEND_ENABLED

        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.SMTP_USE_SSL
        self.from_email = from_email if from_email is not None else settings.SMTP_FROM_EMAIL
        self.from_name = from_name if from_name is not None else settings.SMTP_FROM_NAME
        self.smtp_enabled = enabled if enabled is not None else settings.SMTP_ENABLED

        self.max_retries = max_retries if max_retries is not None else int(getattr(settings, "SMTP_MAX_RETRIES", 3))
        self.retry_base_delay = retry_base_delay if retry_base_delay is not None else float(getattr(settings, "SMTP_RETRY_BASE_DELAY", 1.0))
        self.retry_max_delay = retry_max_delay if retry_max_delay is not None else float(getattr(settings, "SMTP_RETRY_MAX_DELAY", 30.0))

    @property
    def resend_configured(self) -> bool:
        return bool(self.resend_enabled and self.resend_api_key and self.resend_from_email)

    @property
    def smtp_configured(self) -> bool:
        return bool(self.smtp_enabled and self.host and self.from_email)

    @property
    def configured(self) -> bool:
        return self.resend_configured or self.smtp_configured

    def _backoff_seconds(self, attempt: int) -> float:
        delay = min(self.retry_max_delay, self.retry_base_delay * (2 ** max(0, attempt)))
        return delay * random.random()

    def _format_from(self, email: str, name: str) -> str:
        name = (name or "").strip()
        return formataddr((name, email)) if name else email

    def send(
        self,
        *,
        to: Sequence[Any],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        attachments: list[tuple] | None = None,
        reply_to: str | None = None,
    ) -> EmailDeliveryResult:
        recipients = normalize_recipients(to)
        if not recipients:
            return EmailDeliveryResult(ok=False, error="No valid recipients", skipped=True)

        if not self.configured:
            logger.warning("Email not configured; skipping send to %s", recipients)
            return EmailDeliveryResult(ok=False, recipients=recipients, error="Email not configured", skipped=True)

        if self.resend_configured:
            result = self._send_resend(recipients=recipients, subject=subject, body_text=body_text, body_html=body_html, attachments=attachments, reply_to=reply_to)
            if result.ok or not self.smtp_configured:
                return result
            logger.warning("Resend failed (%s); falling back to SMTP", result.error)

        return self._send_smtp(recipients=recipients, subject=subject, body_text=body_text, body_html=body_html, attachments=attachments, reply_to=reply_to)

    @staticmethod
    def _attachment_parts(attachment: tuple) -> tuple[str, bytes, str, str | None]:
        name = str(attachment[0])
        data = bytes(attachment[1])
        content_type = str(attachment[2] or "application/octet-stream")
        content_id = str(attachment[3]) if len(attachment) > 3 and attachment[3] else None
        return name, data, content_type, content_id

    def _send_resend(self, *, recipients: list[str], subject: str, body_text: str, body_html: str | None, attachments: list[tuple] | None, reply_to: str | None) -> EmailDeliveryResult:
        payload: dict[str, Any] = {
            "from": self._format_from(self.resend_from_email, self.resend_from_name),
            "to": recipients,
            "subject": subject,
            "text": body_text or "",
        }
        if body_html:
            payload["html"] = body_html
        if reply_to and is_valid_email(reply_to):
            payload["reply_to"] = reply_to
        if attachments:
            resend_attachments = []
            for attachment in attachments:
                name, data, content_type, content_id = self._attachment_parts(attachment)
                item: dict[str, Any] = {
                    "filename": name,
                    "content": base64.b64encode(data).decode("ascii"),
                    "content_type": content_type,
                }
                if content_id:
                    item["content_id"] = content_id
                resend_attachments.append(item)
            payload["attachments"] = resend_attachments

        headers = {
            "Authorization": f"Bearer {self.resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Bhudi-RMM/1.0",
        }

        max_attempts = max(1, self.max_retries + 1)
        last_exc: BaseException | None = None
        attempts_done = 0
        for attempt in range(max_attempts):
            attempts_done = attempt + 1
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(RESEND_API_URL, headers=headers, json=payload)
                    if resp.status_code >= 400:
                        try:
                            resp.raise_for_status()
                        except httpx.HTTPStatusError:
                            body = (resp.text or "")[:500]
                            if resp.status_code in (408, 429, 500, 502, 503, 504):
                                raise
                            return EmailDeliveryResult(ok=False, recipients=recipients, error=f"Resend {resp.status_code}: {body}", attempts=attempts_done, provider="resend")
                    data = resp.json() if resp.content else {}
                    message_id = str(data.get("id") or "")
                    logger.info("Resend send ok attempt %s/%s to %s id=%s", attempts_done, max_attempts, recipients, message_id)
                    return EmailDeliveryResult(ok=True, recipients=recipients, message_id=message_id or None, attempts=attempts_done, retried=attempt > 0, provider="resend")
            except Exception as exc:
                last_exc = exc
                retryable = is_retryable_error(exc)
                if retryable and attempt < max_attempts - 1:
                    delay = self._backoff_seconds(attempt)
                    logger.warning("Resend failed (attempt %s/%s, retryable): %s; retrying in %.2fs", attempts_done, max_attempts, exc, delay)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                logger.exception("Resend failed (attempt %s/%s)", attempts_done, max_attempts)
                break

        err = str(last_exc)[:1000] if last_exc else "Unknown Resend error"
        return EmailDeliveryResult(ok=False, recipients=recipients, error=err, attempts=attempts_done, retried=attempts_done > 1, last_error=err, provider="resend")

    def _send_smtp(self, *, recipients: list[str], subject: str, body_text: str, body_html: str | None, attachments: list[tuple] | None, reply_to: str | None) -> EmailDeliveryResult:
        msg = EmailMessage()
        msg["From"] = self._format_from(self.from_email, self.from_name or "Bhudi RMM")
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = subject
        msg["Message-ID"] = make_msgid(domain=(self.from_email.split("@")[-1] if "@" in self.from_email else "bhudi.online"))
        if reply_to and is_valid_email(reply_to):
            msg["Reply-To"] = reply_to
        if body_html:
            msg.set_content(body_text or "")
            html_part = msg.add_alternative(body_html, subtype="html")
        else:
            msg.set_content(body_text or "")
            html_part = None

        for attachment in attachments or []:
            filename, data, content_type, content_id = self._attachment_parts(attachment)
            maintype, _, subtype = content_type.partition("/")
            msg.add_attachment(data, maintype=maintype or "application", subtype=subtype or "octet-stream", filename=filename)
            if content_id:
                part = msg.get_payload()[-1]
                part["Content-ID"] = f"<{content_id}>"
                part.replace_header("Content-Disposition", "inline") if part.get("Content-Disposition") else part.add_header("Content-Disposition", "inline", filename=filename)

        max_attempts = max(1, self.max_retries + 1)
        last_exc: BaseException | None = None
        attempts_done = 0
        for attempt in range(max_attempts):
            attempts_done = attempt + 1
            try:
                self._smtp_send(msg, recipients)
                logger.info("SMTP send succeeded on attempt %s/%s to %s", attempts_done, max_attempts, recipients)
                return EmailDeliveryResult(ok=True, recipients=recipients, message_id=str(msg["Message-ID"]), attempts=attempts_done, retried=attempt > 0, provider="smtp")
            except Exception as exc:
                last_exc = exc
                retryable = is_retryable_error(exc)
                if retryable and attempt < max_attempts - 1:
                    delay = self._backoff_seconds(attempt)
                    logger.warning("SMTP send failed (attempt %s/%s, retryable): %s; retrying in %.2fs", attempts_done, max_attempts, exc, delay)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                logger.exception("SMTP send failed (attempt %s/%s, %s)", attempts_done, max_attempts, "permanent" if not retryable else "exhausted retries")
                break

        err = str(last_exc)[:1000] if last_exc else "Unknown SMTP error"
        return EmailDeliveryResult(ok=False, recipients=recipients, error=err, attempts=attempts_done, retried=attempts_done > 1, last_error=err, provider="smtp")

    def _smtp_send(self, msg: EmailMessage, recipients: list[str]) -> None:
        timeout = getattr(settings, "SMTP_TIMEOUT", 30)
        if self.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.host, self.port, timeout=timeout, context=context) as server:
                if self.username:
                    server.login(self.username, self.password or "")
                server.send_message(msg, to_addrs=recipients)
            return
        with smtplib.SMTP(self.host, self.port, timeout=timeout) as server:
            server.ehlo()
            if self.use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            if self.username:
                server.login(self.username, self.password or "")
            server.send_message(msg, to_addrs=recipients)

    def send_report(self, *, recipients: Sequence[Any], report_name: str, report_type: str, format: str, attachment_bytes: bytes, filename: str, content_type: str, summary_lines: list[str] | None = None, schedule_name: str | None = None) -> EmailDeliveryResult:
        to = normalize_recipients(recipients)
        subject = f"[Bhudi] {report_name}"
        if schedule_name:
            subject = f"[Bhudi] Scheduled: {schedule_name}"
        lines = [f"Report: {report_name}", f"Type: {report_type}", f"Format: {format}"]
        if schedule_name:
            lines.insert(0, f"Schedule: {schedule_name}")
        if summary_lines:
            lines.append("")
            lines.append("Summary:")
            lines.extend(f"  - {s}" for s in summary_lines[:20])
        lines.extend(["", "The report is attached to this email.", "", "— Bhudi Online RMM"])
        body_text = "\n".join(lines)
        html_items = "".join(f"<li>{s}</li>" for s in (summary_lines or [])[:20])
        body_html = f"""<html><body style=\"font-family:sans-serif;color:#222\"><h2 style=\"margin-bottom:4px\">{report_name}</h2><p style=\"color:#555;margin-top:0\">Type: <strong>{report_type}</strong> · Format: <strong>{format}</strong>{f' · Schedule: <strong>{schedule_name}</strong>' if schedule_name else ''}</p>{'<h3>Summary</h3><ul>' + html_items + '</ul>' if html_items else ''}<p>The report is attached to this email.</p><p style=\"color:#888;font-size:12px\">— Bhudi Online RMM</p></body></html>"""
        return self.send(to=to, subject=subject, body_text=body_text, body_html=body_html, attachments=[(filename, attachment_bytes, content_type)])
