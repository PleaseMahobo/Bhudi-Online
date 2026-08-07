"""SMTP email delivery for scheduled reports (stdlib only)."""
from __future__ import annotations

import logging
import re
import smtplib
import ssl
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
from typing import Any, Sequence

from app.core.config import settings

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


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


@dataclass
class EmailDeliveryResult:
    ok: bool
    recipients: list[str] = field(default_factory=list)
    message_id: str | None = None
    error: str | None = None
    skipped: bool = False


class EmailService:
    """Thin SMTP client driven by Settings."""

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
    ) -> None:
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.username = username if username is not None else settings.SMTP_USERNAME
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.use_ssl = use_ssl if use_ssl is not None else settings.SMTP_USE_SSL
        self.from_email = from_email if from_email is not None else settings.SMTP_FROM_EMAIL
        self.from_name = from_name if from_name is not None else settings.SMTP_FROM_NAME
        self.enabled = enabled if enabled is not None else settings.SMTP_ENABLED

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.host and self.from_email)

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
            logger.warning("SMTP not configured; skipping email to %s", recipients)
            return EmailDeliveryResult(
                ok=False,
                recipients=recipients,
                error="SMTP not configured (set SMTP_HOST, SMTP_FROM_EMAIL, SMTP_ENABLED=true)",
                skipped=True,
            )

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = formataddr((self.from_name or "Bhudi Reports", self.from_email))
        msg["To"] = ", ".join(recipients)
        domain = self.from_email.split("@")[-1] if "@" in self.from_email else "bhudi.local"
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
            msg.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )

        try:
            self._smtp_send(msg, recipients)
            return EmailDeliveryResult(
                ok=True,
                recipients=recipients,
                message_id=str(msg["Message-ID"]),
            )
        except Exception as exc:
            logger.exception("SMTP send failed")
            return EmailDeliveryResult(
                ok=False,
                recipients=recipients,
                error=str(exc)[:1000],
            )

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

        lines = [
            f"Report: {report_name}",
            f"Type: {report_type}",
            f"Format: {format}",
        ]
        if schedule_name:
            lines.insert(0, f"Schedule: {schedule_name}")
        if summary_lines:
            lines.append("")
            lines.append("Summary:")
            lines.extend(f"  - {s}" for s in summary_lines[:20])
        lines.extend(
            [
                "",
                "The report is attached to this email.",
                "",
                "— Bhudi Online RMM",
            ]
        )
        body_text = "\n".join(lines)

        html_items = "".join(f"<li>{s}</li>" for s in (summary_lines or [])[:20])
        body_html = f"""\
<html><body style="font-family:sans-serif;color:#222">
  <h2 style="margin-bottom:4px">{report_name}</h2>
  <p style="color:#555;margin-top:0">
    Type: <strong>{report_type}</strong> · Format: <strong>{format}</strong>
    {f' · Schedule: <strong>{schedule_name}</strong>' if schedule_name else ''}
  </p>
  {"<h3>Summary</h3><ul>" + html_items + "</ul>" if html_items else ""}
  <p>The report is attached to this email.</p>
  <p style="color:#888;font-size:12px">— Bhudi Online RMM</p>
</body></html>"""

        return self.send(
            to=to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=[(filename, attachment_bytes, content_type)],
        )
