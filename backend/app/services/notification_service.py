from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import (
    NOTIFICATION_CHANNELS,
    NotificationChannel,
    NotificationDelivery,
    NotificationTemplate,
)
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelUpdate,
    NotificationSendRequest,
    NotificationTemplateCreate,
    NotificationTemplateUpdate,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


CHANNEL_CATALOG = [
    {"channel_type": "email", "display_name": "Email (SMTP)", "required_config": ["from_email"]},
    {"channel_type": "sms", "display_name": "SMS (Twilio-compatible)", "required_config": ["account_sid", "auth_token", "from_number"]},
    {"channel_type": "teams", "display_name": "Microsoft Teams", "required_config": ["webhook_url"]},
    {"channel_type": "slack", "display_name": "Slack", "required_config": ["webhook_url"]},
    {"channel_type": "discord", "display_name": "Discord", "required_config": ["webhook_url"]},
    {"channel_type": "whatsapp", "display_name": "WhatsApp (Twilio)", "required_config": ["account_sid", "auth_token", "from_number"]},
    {"channel_type": "push", "display_name": "Push (FCM/APNs stub)", "required_config": ["server_key"]},
    {"channel_type": "webhook", "display_name": "Generic Webhook", "required_config": ["url"]},
]


def _render(template: str, variables: dict[str, Any] | None) -> str:
    if not variables:
        return template

    def repl(m: re.Match[str]) -> str:
        key = m.group(1).strip()
        return str(variables.get(key, m.group(0)))

    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", repl, template)


def _http_json(method: str, url: str, body: dict[str, Any] | None = None, headers: dict[str, str] | None = None, timeout: float = 20.0) -> tuple[int, str]:
    data = None
    hdrs = {"Content-Type": "application/json", **(headers or {})}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(resp.status), resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return int(e.code), e.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Network error: {e.reason}") from e


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_catalog(self):
        return CHANNEL_CATALOG

    # ---- channels ----

    def create_channel(self, payload: NotificationChannelCreate) -> NotificationChannel:
        ctype = payload.channel_type.strip().lower()
        if ctype not in NOTIFICATION_CHANNELS:
            raise ValueError(f"Unsupported channel_type. Allowed: {', '.join(NOTIFICATION_CHANNELS)}")
        row = NotificationChannel(
            channel_type=ctype,
            name=payload.name,
            enabled=payload.enabled,
            tenant_id=payload.tenant_id,
            config=payload.config,
            notes=payload.notes,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_channels(self, *, tenant_id: UUID | None = None, enabled_only: bool = False):
        q = self.db.query(NotificationChannel)
        if tenant_id is not None:
            q = q.filter(NotificationChannel.tenant_id == tenant_id)
        if enabled_only:
            q = q.filter(NotificationChannel.enabled.is_(True))
        return q.order_by(NotificationChannel.name.asc()).all()

    def get_channel(self, channel_id: UUID) -> NotificationChannel | None:
        return self.db.get(NotificationChannel, channel_id)

    def update_channel(self, channel_id: UUID, payload: NotificationChannelUpdate):
        row = self.get_channel(channel_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_channel(self, channel_id: UUID) -> bool:
        row = self.get_channel(channel_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---- templates ----

    def create_template(self, payload: NotificationTemplateCreate) -> NotificationTemplate:
        row = NotificationTemplate(
            code=payload.code.strip().lower(),
            name=payload.name,
            subject=payload.subject,
            body=payload.body,
            channel_bodies=payload.channel_bodies,
            variables=payload.variables,
            enabled=payload.enabled,
            tenant_id=payload.tenant_id,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def list_templates(self, *, tenant_id: UUID | None = None):
        q = self.db.query(NotificationTemplate)
        if tenant_id is not None:
            q = q.filter(NotificationTemplate.tenant_id == tenant_id)
        return q.order_by(NotificationTemplate.code.asc()).all()

    def update_template(self, template_id: UUID, payload: NotificationTemplateUpdate):
        row = self.db.get(NotificationTemplate, template_id)
        if not row:
            return None
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        self.db.commit()
        self.db.refresh(row)
        return row

    def delete_template(self, template_id: UUID) -> bool:
        row = self.db.get(NotificationTemplate, template_id)
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    # ---- send ----

    def send(self, payload: NotificationSendRequest) -> NotificationDelivery:
        channel = self.get_channel(payload.channel_id)
        if not channel:
            raise ValueError("Channel not found")
        if not channel.enabled:
            raise ValueError("Channel is disabled")

        subject = payload.subject
        body = payload.body or ""
        template_id = None
        if payload.template_code:
            tmpl = (
                self.db.query(NotificationTemplate)
                .filter(
                    NotificationTemplate.code == payload.template_code.strip().lower(),
                    NotificationTemplate.enabled.is_(True),
                )
                .first()
            )
            if not tmpl:
                raise ValueError(f"Template not found: {payload.template_code}")
            template_id = tmpl.id
            vars_ = payload.template_vars or {}
            subject = _render(tmpl.subject or subject or "", vars_)
            body_src = (tmpl.channel_bodies or {}).get(channel.channel_type) or tmpl.body
            body = _render(body_src, vars_)

        if not body:
            raise ValueError("body or template_code required")

        delivery = NotificationDelivery(
            channel_id=channel.id,
            tenant_id=channel.tenant_id,
            template_id=template_id,
            recipient=payload.recipient,
            subject=subject,
            body=body,
            status="pending",
            metadata_json=payload.metadata,
        )
        self.db.add(delivery)
        self.db.flush()

        try:
            result = self._dispatch(channel, delivery)
            delivery.status = result.get("status", "sent")
            delivery.provider_ref = result.get("provider_ref")
            delivery.attempts = 1
            delivery.sent_at = _utcnow()
            channel.last_used_at = _utcnow()
            channel.last_error = None
        except Exception as e:
            delivery.status = "failed"
            delivery.error = str(e)
            delivery.attempts = 1
            channel.last_error = str(e)

        self.db.commit()
        self.db.refresh(delivery)
        return delivery

    def list_deliveries(
        self,
        *,
        channel_id: UUID | None = None,
        status: str | None = None,
        limit: int = 50,
    ):
        q = self.db.query(NotificationDelivery)
        if channel_id:
            q = q.filter(NotificationDelivery.channel_id == channel_id)
        if status:
            q = q.filter(NotificationDelivery.status == status)
        return q.order_by(NotificationDelivery.created_at.desc()).limit(limit).all()

    def _dispatch(self, channel: NotificationChannel, delivery: NotificationDelivery) -> dict[str, Any]:
        cfg = dict(channel.config or {})
        ctype = channel.channel_type

        if cfg.get("dry_run") is True:
            return {"status": "dry_run", "provider_ref": f"dry_{ctype}"}

        if ctype == "email":
            return self._send_email(cfg, delivery)
        if ctype == "sms":
            return self._send_twilio(cfg, delivery, whatsapp=False)
        if ctype == "whatsapp":
            return self._send_twilio(cfg, delivery, whatsapp=True)
        if ctype in ("teams", "slack", "discord", "webhook"):
            return self._send_webhook(ctype, cfg, delivery)
        if ctype == "push":
            return self._send_push(cfg, delivery)
        raise ValueError(f"No dispatcher for {ctype}")

    def _send_email(self, cfg: dict[str, Any], delivery: NotificationDelivery) -> dict[str, Any]:
        # Prefer channel config; fall back to global SMTP settings
        host = cfg.get("smtp_host") or settings.SMTP_HOST
        if not host or not (cfg.get("from_email") or settings.SMTP_FROM_EMAIL):
            if not settings.SMTP_ENABLED:
                return {"status": "dry_run", "provider_ref": "email_no_smtp"}
        try:
            from app.services.email_service import EmailService

            svc = EmailService()
            # Minimal path: use EmailService if available methods exist
            if hasattr(svc, "send_simple"):
                svc.send_simple(
                    to=delivery.recipient,
                    subject=delivery.subject or "Notification",
                    body=delivery.body,
                )
            else:
                # stdlib fallback via settings
                import smtplib
                from email.message import EmailMessage

                msg = EmailMessage()
                msg["Subject"] = delivery.subject or "Notification"
                msg["From"] = cfg.get("from_email") or settings.SMTP_FROM_EMAIL
                msg["To"] = delivery.recipient
                msg.set_content(delivery.body)
                port = int(cfg.get("smtp_port") or settings.SMTP_PORT)
                user = cfg.get("smtp_username") or settings.SMTP_USERNAME
                password = cfg.get("smtp_password") or settings.SMTP_PASSWORD
                if settings.SMTP_USE_SSL:
                    with smtplib.SMTP_SSL(host, port, timeout=settings.SMTP_TIMEOUT) as s:
                        if user:
                            s.login(user, password)
                        s.send_message(msg)
                else:
                    with smtplib.SMTP(host, port, timeout=settings.SMTP_TIMEOUT) as s:
                        if settings.SMTP_USE_TLS:
                            s.starttls()
                        if user:
                            s.login(user, password)
                        s.send_message(msg)
            return {"status": "sent", "provider_ref": "smtp"}
        except Exception as e:
            raise RuntimeError(f"Email send failed: {e}") from e

    def _send_twilio(self, cfg: dict[str, Any], delivery: NotificationDelivery, *, whatsapp: bool) -> dict[str, Any]:
        sid = cfg.get("account_sid")
        token = cfg.get("auth_token")
        from_num = cfg.get("from_number")
        if not (sid and token and from_num):
            return {"status": "dry_run", "provider_ref": "twilio_missing_config"}
        to = delivery.recipient
        if whatsapp and not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"
        if whatsapp and not str(from_num).startswith("whatsapp:"):
            from_num = f"whatsapp:{from_num}"
        import base64

        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        form = f"To={urllib.request.quote(to)}&From={urllib.request.quote(str(from_num))}&Body={urllib.request.quote(delivery.body)}"
        req = urllib.request.Request(
            url,
            data=form.encode("utf-8"),
            headers={
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            return {"status": "sent", "provider_ref": str(data.get("sid") or "twilio")}

    def _send_webhook(self, ctype: str, cfg: dict[str, Any], delivery: NotificationDelivery) -> dict[str, Any]:
        url = cfg.get("webhook_url") or cfg.get("url")
        if not url:
            return {"status": "dry_run", "provider_ref": f"{ctype}_missing_url"}

        if ctype == "slack":
            body = {"text": f"*{delivery.subject or 'Alert'}*\n{delivery.body}"}
        elif ctype == "teams":
            body = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": delivery.subject or "Notification",
                "themeColor": cfg.get("theme_color", "0076D7"),
                "title": delivery.subject or "Notification",
                "text": delivery.body,
            }
        elif ctype == "discord":
            body = {"content": f"**{delivery.subject or 'Alert'}**\n{delivery.body}"[:2000]}
        else:
            body = {
                "recipient": delivery.recipient,
                "subject": delivery.subject,
                "body": delivery.body,
                "metadata": delivery.metadata_json,
            }

        code, raw = _http_json("POST", str(url), body=body)
        if code >= 400:
            raise RuntimeError(f"{ctype} webhook HTTP {code}: {raw[:300]}")
        return {"status": "sent", "provider_ref": f"{ctype}:{code}"}

    def _send_push(self, cfg: dict[str, Any], delivery: NotificationDelivery) -> dict[str, Any]:
        # FCM legacy HTTP — dry-run without server_key
        key = cfg.get("server_key")
        if not key:
            return {"status": "dry_run", "provider_ref": "push_missing_key"}
        body = {
            "to": delivery.recipient,
            "notification": {
                "title": delivery.subject or "Notification",
                "body": delivery.body[:1024],
            },
            "data": delivery.metadata_json or {},
        }
        code, raw = _http_json(
            "POST",
            "https://fcm.googleapis.com/fcm/send",
            body=body,
            headers={"Authorization": f"key={key}"},
        )
        if code >= 400:
            raise RuntimeError(f"FCM HTTP {code}: {raw[:300]}")
        return {"status": "sent", "provider_ref": f"fcm:{code}"}
