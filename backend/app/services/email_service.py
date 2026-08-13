"""Transactional email delivery for Bhudi.

The recommended production provider is an HTTPS email API (Resend), which works
from Railway environments where outbound SMTP ports are restricted. SMTP remains
available as an explicit legacy provider for environments that permit it.
"""
from __future__ import annotations

import base64
import json
import logging
import random
import re
import smtplib
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any, Sequence

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
    return isinstance(exc, smtplib.SMTPException)


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


class EmailService:
    """Provider-neutral transactional email service.

    Resend is the default production provider because it uses HTTPS/443.
    SMTP can be selected explicitly with EMAIL_PROVIDER=smtp.
    """

    def __init__(self) -> None:
        self.provider = settings.EMAIL_PROVIDER
        self.max_retries = max(0, int(settings.EMAIL_MAX_RETRIES))
        self.retry_base_delay = max(0.0, float(settings.EMAIL_RETRY_BASE_DELAY))
        self.retry_max_delay = max(0.0, float(settings.EMAIL_RETRY_MAX_DELAY))
        self.http_timeout = max(1, int(settings.EMAIL_HTTP_TIMEOUT))

    @property
    def configured(self) -> bool:
        if self.provider == "resend":
            return bool(settings.RESEND_API_KEY and settings.SMTP_FROM_EMAIL)
        if self.provider == "smtp":
            return bool(settings.SMTP_ENABLED and settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)
        return False

    def _backoff_seconds(self, attempt: int) -> float:
        capped = min(self.retry_base_delay * (2**attempt), self.retry_max_delay)
        return random.uniform(0, capped) if capped > 0 else 0.0

    def send(
        self,
        *,
        to: Sequence[str],
        subject: str,
        body_text: str,
        body_html: str | None = None,
        attachments: list[tuple[str, bytes, str]] | None = None,
        reply_to: str | None = None,
    ) -> EmailDeliveryResult:
        recipients = normalize_recipients(list(to))
        if not recipients:
            return EmailDeliveryResult(ok=False, error="No valid recipients", skipped=True)

        if not self.configured:
            logger.error(
                "Email provider '%s' is not configured; refusing to send to %s",
                self.provider,
                recipients,
            )
            return EmailDeliveryResult(
                ok=False,
                recipients=recipients,
                error=f"Email provider '{self.provider}' is not configured",
                skipped=True,
            )

        if self.provider == "resend":
            return self._send_resend(
                recipients, subject, body_text, body_html, attachments, reply_to
            )
        if self.provider == "smtp":
            return self._send_smtp(
                recipients, subject, body_text, body_html, attachments, reply_to
            )

        return EmailDeliveryResult(
            ok=False,
            recipients=recipients,
            error=f"Unsupported EMAIL_PROVIDER: {self.provider}",
        )

    def _send_resend(
        self,
        recipients: list[str],
        subject: str,
        body_text: str,
        body_html: str | None,
        attachments: list[tuple[str, bytes, str]] | None,
        reply_to: str | None,
    ) -> EmailDeliveryResult:
        payload: dict[str, Any] = {
            "from": formataddr((settings.SMTP_FROM_NAME or "Bhudi RMM", settings.SMTP_FROM_EMAIL)),
            "to": recipients,
            "subject": subject,
            "text": body_text,
        }
        if body_html:
            payload["html"] = body_html
        if reply_to:
            payload["reply_to"] = reply_to
        if attachments:
            payload["attachments"] = [
                {
                    "filename": filename,
                    "content": base64.b64encode(content).decode("ascii"),
                }
                for filename, content, _content_type in attachments
            ]

        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            settings.RESEND_API_URL,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Bhudi-RMM/1.0",
            },
        )

        max_attempts = self.max_retries + 1
        last_error: str | None = None
        attempts_done = 0

        for attempt in range(max_attempts):
            attempts_done = attempt + 1
            try:
                with urllib.request.urlopen(request, timeout=self.http_timeout) as response:
                    response_body = response.read().decode("utf-8", errors="replace")
                    if not 200 <= response.status < 300:
                        raise RuntimeError(f"Resend HTTP {response.status}: {response_body[:500]}")
                    result = json.loads(response_body or "{}")

                message_id = str(result.get("id") or make_msgid(domain="bhudi.online"))
                logger.info(
                    "Transactional email sent via Resend on attempt %s/%s to %s message_id=%s",
                    attempts_done,
                    max_attempts,
                    recipients,
                    message_id,
                )
                return EmailDeliveryResult(
                    ok=True,
                    recipients=recipients,
                    message_id=message_id,
                    attempts=attempts_done,
                    retried=attempt > 0,
                )
            except urllib.error.HTTPError as exc:
                response_body = exc.read().decode("utf-8", errors="replace")[:1000]
                last_error = f"Resend HTTP {exc.code}: {response_body}"
                retryable = exc.code == 429 or exc.code >= 500
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
                last_error = f"Resend network error: {exc}"
                retryable = True
            except (json.JSONDecodeError, RuntimeError) as exc:
                last_error = str(exc)[:1000]
                retryable = False
            except Exception as exc:
                last_error = str(exc)[:1000]
                retryable = False

            will_retry = retryable and attempt < max_attempts - 1
            if will_retry:
                delay = self._backoff_seconds(attempt)
                logger.warning(
                    "Resend send failed (attempt %s/%s, retryable): %s; retrying in %.2fs",
                    attempts_done,
                    max_attempts,
                    last_error,
                    delay,
                )
                if delay:
                    time.sleep(delay)
                continue
            logger.error(
                "Resend send failed (attempt %s/%s): %s",
                attempts_done,
                max_attempts,
                last_error,
            )
            break

        return EmailDeliveryResult(
            ok=False,
            recipients=recipients,
            error=last_error or "Unknown Resend error",
            attempts=attempts_done,
            retried=attempts_done > 1,
            last_error=last_error,
        )

    def _send_smtp(
        self,
        recipients: list[str],
        subject: str,
        body_text: str,
        body_html: str | None,
        attachments: list[tuple[str, bytes, str]] | None,
        reply_to: str | None,
    ) -> EmailDeliveryResult:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.SMTP_FROM_NAME or "Bhudi RMM", settings.SMTP_FROM_EMAIL))
        msg["To"] = ", ".join(recipients)
        domain = settings.SMTP_FROM_EMAIL.split("@")[-1] if "@" in settings.SMTP_FROM_EMAIL else "bhudi.local"
        msg["Message-ID"] = make_msgid(domain=domain)
        if reply_to:
            msg["Reply-To"] = reply_to
        msg.set_content(body_text)
        if body_html:
            msg.add_alternative(body_html, subtype="html")
        for filename, content, content_type in attachments or []:
            maintype, _, subtype = (content_type or "application/octet-stream").partition("/")
            if not subtype:
                maintype, subtype = "application", "octet-stream"
            msg.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)

        max_attempts = max(1, int(settings.SMTP_MAX_RETRIES) + 1)
        last_exc: BaseException | None = None
        for attempt in range(max_attempts):
            try:
                timeout = getattr(settings, "SMTP_TIMEOUT", 30)
                if settings.SMTP_USE_SSL:
                    context = ssl.create_default_context()
                    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout, context=context) as server:
                        if settings.SMTP_USERNAME:
                            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                        server.send_message(msg, to_addrs=recipients)
                else:
                    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout) as server:
                        server.ehlo()
                        if settings.SMTP_USE_TLS:
                            server.starttls(context=ssl.create_default_context())
                            server.ehlo()
                        if settings.SMTP_USERNAME:
                            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                        server.send_message(msg, to_addrs=recipients)
                return EmailDeliveryResult(ok=True, recipients=recipients, message_id=str(msg["Message-ID"]), attempts=attempt + 1, retried=attempt > 0)
            except Exception as exc:
                last_exc = exc
                retryable = is_retryable_error(exc)
                if retryable and attempt < max_attempts - 1:
                    delay = self._backoff_seconds(attempt)
                    logger.warning("SMTP send failed (attempt %s/%s): %s; retrying in %.2fs", attempt + 1, max_attempts, exc, delay)
                    if delay:
                        time.sleep(delay)
                    continue
                logger.exception("SMTP send failed (attempt %s/%s)", attempt + 1, max_attempts)
                break

        return EmailDeliveryResult(
            ok=False,
            recipients=recipients,
            error=str(last_exc)[:1000] if last_exc else "Unknown SMTP error",
            attempts=max_attempts,
            retried=max_attempts > 1,
            last_error=str(last_exc)[:1000] if last_exc else None,
        )

    def send_report(
        self,
        *,
        recipients: Sequence[Any],
        report_name: str,
        report_type: str,
        format: str,
        attachment_bytes: bytes,
        filename: str,
        content_type: str,
        summary_lines: list[str] | None = None,
        schedule_name: str | None = None,
    ) -> EmailDeliveryResult:
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
        body_html = f"""<html><body style=\"font-family:sans-serif;color:#222\">
<h2 style=\"margin-bottom:4px\">{report_name}</h2>
<p style=\"color:#555;margin-top:0\">Type: <strong>{report_type}</strong> · Format: <strong>{format}</strong>{f' · Schedule: <strong>{schedule_name}</strong>' if schedule_name else ''}</p>
{"<h3>Summary</h3><ul>" + html_items + "</ul>" if html_items else ""}
<p>The report is attached to this email.</p>
<p style=\"color:#888;font-size:12px\">— Bhudi Online RMM</p>
</body></html>"""
        return self.send(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=[(filename, attachment_bytes, content_type)],
        )
