from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.asset_management import Asset, AssetLifecycleEvent
from app.models.itsm import ServiceTicket, TicketAssetLink, TicketWorkNote
from app.schemas.itsm import (
    AssetTicketCreateRequest,
    ServiceTicketCreate,
    ServiceTicketUpdate,
    TicketAssetLinkCreate,
    TicketStatusUpdate,
    WorkNoteCreate,
)


PREFIX_MAP = {
    "incident": "INC",
    "service_request": "SR",
    "problem": "PRB",
    "change": "CHG",
    "maintenance": "MNT",
}

VALID_STATUSES = {"new", "open", "in_progress", "on_hold", "resolved", "closed", "cancelled"}
VALID_TYPES = set(PREFIX_MAP)
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


class ITSMService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _ticket_number(ticket_type: str) -> str:
        prefix = PREFIX_MAP.get(ticket_type, "TKT")
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{prefix}-{day}-{secrets.token_hex(2).upper()}"

    @staticmethod
    def _validate_ticket_fields(ticket_type: str, status: str, priority: str) -> None:
        if ticket_type not in VALID_TYPES:
            raise ValueError(f"Invalid ticket type: {ticket_type}")
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid ticket status: {status}")
        if priority not in VALID_PRIORITIES:
            raise ValueError(f"Invalid ticket priority: {priority}")

    @staticmethod
    def _refresh_sla(ticket: ServiceTicket) -> ServiceTicket:
        """Calculate SLA breach state from persisted SLA targets without a worker."""
        if ticket.sla_resolve_minutes is None or ticket.sla_breached:
            return ticket
        if ticket.status in {"resolved", "closed", "cancelled"}:
            return ticket
        elapsed = datetime.now(timezone.utc) - ticket.created_at
        ticket.sla_breached = elapsed.total_seconds() >= ticket.sla_resolve_minutes * 60
        return ticket

    def _enrich_links(self, ticket: ServiceTicket) -> ServiceTicket:
        self._refresh_sla(ticket)
        for link in ticket.asset_links or []:
            if link.asset is not None:
                setattr(link, "asset_name", link.asset.name)
                setattr(link, "asset_tag", link.asset.asset_tag)
                setattr(link, "asset_status", link.asset.status)
        return ticket

    def _log_asset_lifecycle(
        self,
        asset_id: UUID,
        event_type: str,
        *,
        detail: str | None = None,
        actor: str | None = None,
        from_status: str | None = None,
        to_status: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self.db.add(
            AssetLifecycleEvent(
                asset_id=asset_id,
                event_type=event_type,
                from_status=from_status,
                to_status=to_status,
                actor=actor,
                detail=detail,
                metadata_json=metadata,
            )
        )

    # ---------- CRUD ----------

    def create_ticket(self, payload: ServiceTicketCreate) -> ServiceTicket:
        self._validate_ticket_fields(payload.ticket_type, payload.status, payload.priority)
        data = payload.model_dump(exclude={"asset_ids", "asset_links"})
        ticket = ServiceTicket(
            **data,
            number=self._ticket_number(payload.ticket_type),
        )
        self.db.add(ticket)
        self.db.flush()

        seen: set[UUID] = set()
        for aid in payload.asset_ids:
            if aid in seen:
                continue
            seen.add(aid)
            self.db.add(TicketAssetLink(ticket_id=ticket.id, asset_id=aid, role="primary"))
            self._log_asset_lifecycle(
                aid,
                "itsm_linked",
                detail=f"Linked to {ticket.number}",
                metadata={"ticket_id": str(ticket.id), "ticket_number": ticket.number},
            )

        for link in payload.asset_links:
            if link.asset_id in seen:
                continue
            seen.add(link.asset_id)
            self.db.add(
                TicketAssetLink(
                    ticket_id=ticket.id,
                    asset_id=link.asset_id,
                    role=link.role,
                    notes=link.notes,
                )
            )
            self._log_asset_lifecycle(
                link.asset_id,
                "itsm_linked",
                detail=f"Linked to {ticket.number} ({link.role})",
                metadata={"ticket_id": str(ticket.id), "ticket_number": ticket.number},
            )

        self.db.add(
            TicketWorkNote(
                ticket_id=ticket.id,
                author=payload.requester or "system",
                body=f"Ticket {ticket.number} created (source={ticket.source}).",
                is_public=False,
            )
        )
        self.db.commit()
        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def list_tickets(
        self,
        *,
        status: str | None = None,
        ticket_type: str | None = None,
        asset_id: UUID | None = None,
        device_id: UUID | None = None,
        priority: str | None = None,
        q: str | None = None,
        tenant_id: UUID | None = None,
    ) -> list[ServiceTicket]:
        query = self.db.query(ServiceTicket).options(
            joinedload(ServiceTicket.asset_links).joinedload(TicketAssetLink.asset)
        )
        if tenant_id is not None:
            query = query.filter(ServiceTicket.tenant_id == tenant_id)
        if status:
            query = query.filter(ServiceTicket.status == status)
        if ticket_type:
            query = query.filter(ServiceTicket.ticket_type == ticket_type)
        if device_id:
            query = query.filter(ServiceTicket.device_id == device_id)
        if priority:
            query = query.filter(ServiceTicket.priority == priority)
        if asset_id:
            query = query.join(TicketAssetLink).filter(TicketAssetLink.asset_id == asset_id)
        if q and q.strip():
            term = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    ServiceTicket.number.ilike(term),
                    ServiceTicket.title.ilike(term),
                    ServiceTicket.description.ilike(term),
                    ServiceTicket.requester.ilike(term),
                    ServiceTicket.assignee.ilike(term),
                )
            )
        tickets = query.order_by(ServiceTicket.created_at.desc()).all()
        return [self._enrich_links(t) for t in tickets]

    def get_ticket(self, ticket_id: UUID, tenant_id: UUID | None = None) -> ServiceTicket | None:
        query = (
            self.db.query(ServiceTicket)
            .options(
                joinedload(ServiceTicket.asset_links).joinedload(TicketAssetLink.asset),
                joinedload(ServiceTicket.work_notes),
            )
            .filter(ServiceTicket.id == ticket_id)
        )
        if tenant_id is not None:
            query = query.filter(ServiceTicket.tenant_id == tenant_id)
        ticket = query.first()
        if ticket:
            self._enrich_links(ticket)
        return ticket

    def get_ticket_by_number(self, number: str, tenant_id: UUID | None = None) -> ServiceTicket | None:
        query = (
            self.db.query(ServiceTicket)
            .options(joinedload(ServiceTicket.asset_links).joinedload(TicketAssetLink.asset))
            .filter(ServiceTicket.number == number)
        )
        if tenant_id is not None:
            query = query.filter(ServiceTicket.tenant_id == tenant_id)
        ticket = query.first()
        if ticket:
            self._enrich_links(ticket)
        return ticket

    def update_ticket(
        self, ticket_id: UUID, payload: ServiceTicketUpdate, tenant_id: UUID | None = None
    ) -> ServiceTicket | None:
        ticket = self.get_ticket(ticket_id, tenant_id=tenant_id)
        if not ticket:
            return None
        data = payload.model_dump(exclude_unset=True)
        new_type = data.get("ticket_type", ticket.ticket_type)
        new_status = data.get("status", ticket.status)
        new_priority = data.get("priority", ticket.priority)
        self._validate_ticket_fields(new_type, new_status, new_priority)
        old_status = ticket.status
        for k, v in data.items():
            setattr(ticket, k, v)
        if "status" in data and data["status"] != old_status:
            self._apply_status_side_effects(ticket, old_status, data["status"], actor=None)
            self.db.add(
                TicketWorkNote(
                    ticket_id=ticket.id,
                    author="system",
                    body=f"Status changed {old_status} → {data['status']}",
                    is_public=False,
                )
            )
        self.db.commit()
        return self.get_ticket(ticket_id, tenant_id=tenant_id)

    def set_status(
        self, ticket_id: UUID, payload: TicketStatusUpdate, tenant_id: UUID | None = None
    ) -> ServiceTicket | None:
        if payload.status not in VALID_STATUSES:
            raise ValueError(f"Invalid ticket status: {payload.status}")
        ticket = self.get_ticket(ticket_id, tenant_id=tenant_id)
        if not ticket:
            return None
        old = ticket.status
        if old == payload.status and payload.resolution is None:
            return ticket
        ticket.status = payload.status
        if payload.resolution is not None:
            ticket.resolution = payload.resolution
        self._apply_status_side_effects(ticket, old, payload.status, actor=payload.actor)
        self.db.add(
            TicketWorkNote(
                ticket_id=ticket.id,
                author=payload.actor or "system",
                body=f"Status changed {old} → {payload.status}"
                + (f": {payload.resolution}" if payload.resolution else ""),
            )
        )
        self.db.commit()
        return self.get_ticket(ticket_id, tenant_id=tenant_id)

    def _apply_status_side_effects(
        self,
        ticket: ServiceTicket,
        old_status: str,
        new_status: str,
        actor: str | None,
    ) -> None:
        now = datetime.now(timezone.utc)
        if new_status == "resolved" and ticket.resolved_at is None:
            ticket.resolved_at = now
        if new_status == "closed" and ticket.closed_at is None:
            ticket.closed_at = now
            if ticket.resolved_at is None:
                ticket.resolved_at = now
        if new_status in ("resolved", "closed") and ticket.ticket_type in ("maintenance", "incident", "change"):
            links = self.db.query(TicketAssetLink).filter(TicketAssetLink.ticket_id == ticket.id).all()
            for link in links:
                asset = self.db.get(Asset, link.asset_id)
                if asset and asset.status == "in_repair":
                    prev = asset.status
                    asset.status = "deployed" if asset.deployed_at else "in_stock"
                    self._log_asset_lifecycle(
                        asset.id,
                        "status_change",
                        from_status=prev,
                        to_status=asset.status,
                        actor=actor or "itsm",
                        detail=f"Auto-restored on ticket {ticket.number} close",
                        metadata={"ticket_number": ticket.number},
                    )

    def delete_ticket(self, ticket_id: UUID, tenant_id: UUID | None = None) -> bool:
        ticket = self.get_ticket(ticket_id, tenant_id=tenant_id)
        if not ticket:
            return False
        self.db.delete(ticket)
        self.db.commit()
        return True

    # ---------- Asset integration ----------

    def create_ticket_for_asset(
        self, asset_id: UUID, payload: AssetTicketCreateRequest, tenant_id: UUID | None = None
    ) -> ServiceTicket:
        asset = self.db.get(Asset, asset_id)
        if not asset or (tenant_id is not None and asset.tenant_id != tenant_id):
            raise ValueError("Asset not found")
        create = ServiceTicketCreate(
            title=payload.title,
            description=payload.description or f"Asset: {asset.name} ({asset.asset_tag or asset.serial_number or asset.id})",
            ticket_type=payload.ticket_type,
            priority=payload.priority,
            category=payload.category or "asset",
            requester=payload.requester,
            assignee=payload.assignee,
            device_id=asset.device_id,
            tenant_id=asset.tenant_id,
            source="asset_lifecycle",
            source_ref=str(asset.id),
            asset_ids=[asset.id],
        )
        ticket = self.create_ticket(create)
        if payload.set_asset_in_repair and asset.status != "in_repair":
            prev = asset.status
            asset.status = "in_repair"
            self._log_asset_lifecycle(
                asset.id,
                "status_change",
                from_status=prev,
                to_status="in_repair",
                actor=payload.requester or "itsm",
                detail=f"Set in_repair via {ticket.number}",
                metadata={"ticket_number": ticket.number},
            )
            self.db.commit()
        return self.get_ticket(ticket.id, tenant_id=tenant_id)  # type: ignore[return-value]

    def link_asset(
        self, ticket_id: UUID, link: TicketAssetLinkCreate, tenant_id: UUID | None = None
    ) -> TicketAssetLink:
        ticket = self.get_ticket(ticket_id, tenant_id=tenant_id)
        if not ticket:
            raise ValueError("Ticket not found")
        asset = self.db.get(Asset, link.asset_id)
        if not asset or (tenant_id is not None and asset.tenant_id != tenant_id):
            raise ValueError("Asset not found")
        existing = self.db.query(TicketAssetLink).filter(
            TicketAssetLink.ticket_id == ticket_id,
            TicketAssetLink.asset_id == link.asset_id,
        ).first()
        if existing:
            existing.role = link.role
            existing.notes = link.notes
            self.db.commit()
            return existing
        row = TicketAssetLink(ticket_id=ticket_id, asset_id=link.asset_id, role=link.role, notes=link.notes)
        self.db.add(row)
        self._log_asset_lifecycle(
            link.asset_id,
            "itsm_linked",
            detail=f"Linked to {ticket.number}",
            metadata={"ticket_id": str(ticket_id), "ticket_number": ticket.number},
        )
        self.db.commit()
        self.db.refresh(row)
        return row

    def unlink_asset(self, ticket_id: UUID, asset_id: UUID, tenant_id: UUID | None = None) -> bool:
        if not self.get_ticket(ticket_id, tenant_id=tenant_id):
            return False
        row = self.db.query(TicketAssetLink).filter(
            TicketAssetLink.ticket_id == ticket_id,
            TicketAssetLink.asset_id == asset_id,
        ).first()
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def add_work_note(self, ticket_id: UUID, payload: WorkNoteCreate, tenant_id: UUID | None = None) -> TicketWorkNote:
        if not self.get_ticket(ticket_id, tenant_id=tenant_id):
            raise ValueError("Ticket not found")
        note = TicketWorkNote(ticket_id=ticket_id, author=payload.author, body=payload.body, is_public=payload.is_public)
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_work_notes(self, ticket_id: UUID, tenant_id: UUID | None = None) -> list[TicketWorkNote]:
        if not self.get_ticket(ticket_id, tenant_id=tenant_id):
            return []
        return (
            self.db.query(TicketWorkNote)
            .filter(TicketWorkNote.ticket_id == ticket_id)
            .order_by(TicketWorkNote.created_at.asc())
            .all()
        )

    def tickets_for_asset(self, asset_id: UUID, tenant_id: UUID | None = None) -> list[ServiceTicket]:
        return self.list_tickets(asset_id=asset_id, tenant_id=tenant_id)

    # ---------- Automated integrations ----------

    def open_ticket_on_asset_status(
        self,
        asset: Asset,
        from_status: str,
        to_status: str,
        actor: str | None = None,
    ) -> ServiceTicket | None:
        if to_status == "in_repair":
            return self.create_ticket(
                ServiceTicketCreate(
                    title=f"Repair: {asset.name}",
                    description=f"Asset moved to in_repair from {from_status}.\nTag: {asset.asset_tag} | SN: {asset.serial_number}",
                    ticket_type="maintenance",
                    priority="high",
                    category="repair",
                    requester=actor,
                    device_id=asset.device_id,
                    tenant_id=asset.tenant_id,
                    source="asset_lifecycle",
                    source_ref=str(asset.id),
                    asset_ids=[asset.id],
                )
            )
        if to_status == "disposed":
            return self.create_ticket(
                ServiceTicketCreate(
                    title=f"Disposal: {asset.name}",
                    description=f"Asset disposed (was {from_status}).",
                    ticket_type="change",
                    priority="medium",
                    category="disposal",
                    requester=actor,
                    device_id=asset.device_id,
                    tenant_id=asset.tenant_id,
                    source="asset_lifecycle",
                    source_ref=str(asset.id),
                    asset_ids=[asset.id],
                )
            )
        return None

    def open_warranty_expiry_tickets(self, within_days: int = 30) -> list[ServiceTicket]:
        """Create service requests for assets whose warranty ends within N days."""
        if within_days < 0 or within_days > 3650:
            raise ValueError("within_days must be between 0 and 3650")
        today = date.today()
        cutoff = today + timedelta(days=within_days)
        assets = (
            self.db.query(Asset)
            .filter(
                Asset.warranty_end.isnot(None),
                Asset.warranty_end >= today,
                Asset.warranty_end <= cutoff,
                Asset.status.notin_(["disposed", "retired"]),
            )
            .all()
        )
        created: list[ServiceTicket] = []
        for asset in assets:
            existing = (
                self.db.query(ServiceTicket)
                .join(TicketAssetLink)
                .filter(
                    TicketAssetLink.asset_id == asset.id,
                    ServiceTicket.source == "warranty",
                    ServiceTicket.status.in_(["open", "in_progress", "on_hold"]),
                )
                .first()
            )
            if existing:
                continue
            created.append(
                self.create_ticket(
                    ServiceTicketCreate(
                        title=f"Warranty expiring: {asset.name}",
                        description=f"Warranty ends {asset.warranty_end}. Provider: {asset.warranty_provider or 'n/a'}. Ref: {asset.warranty_lookup_ref or 'n/a'}.",
                        ticket_type="service_request",
                        priority="medium",
                        category="warranty",
                        device_id=asset.device_id,
                        tenant_id=asset.tenant_id,
                        source="warranty",
                        source_ref=str(asset.id),
                        asset_ids=[asset.id],
                    )
                )
            )
        return created
