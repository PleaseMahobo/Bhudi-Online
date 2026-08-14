from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import event

from app.models.itsm import ServiceTicket


_DATETIME_FIELDS = ("created_at", "updated_at", "resolved_at", "closed_at")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize_ticket_datetimes(ticket: ServiceTicket) -> None:
    for field in _DATETIME_FIELDS:
        value = getattr(ticket, field, None)
        normalized = _as_utc(value)
        if normalized is not value:
            setattr(ticket, field, normalized)


@event.listens_for(ServiceTicket, "load")
def _normalize_on_load(ticket: ServiceTicket, _context: object) -> None:
    _normalize_ticket_datetimes(ticket)


@event.listens_for(ServiceTicket, "refresh")
def _normalize_on_refresh(
    ticket: ServiceTicket, _context: object, _attrs: object | None
) -> None:
    _normalize_ticket_datetimes(ticket)
