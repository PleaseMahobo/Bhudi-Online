from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from uuid import UUID

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


class ITSMService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _ticket_number(ticket_type: str) -> str:
        prefix = PREFIX_MAP.get(ticket_type, "TKT")
        day = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{prefix}-{day}-{secrets.token_hex(2).upper()}"

    def _enrich_links(self, ticket: ServiceTicket) -> ServiceTicket:
        # Load asset summaries onto link objects for response shaping
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
        data = payload.model_dump(exclude={"asset_ids", "asset_links"})
        ticket = ServiceTicket(
            **data,
            number=self._ticket_number(payload.ticket_type),
        )
        self.db.add(ticket)
        self.db.flush()

        # Link assets from asset_ids (primary) and explicit links
        seen: set[UUID] = set()
        for aid in payload.asset_ids:
            if aid in seen:
                continue
            seen.add(aid)
            self.db.add(
                TicketAssetLink(ticket_id=ticket.id, asset_id=aid, role="primary")
            )
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
    ) -> list[ServiceTicket]:
        q = self.db.query(ServiceTicket).options(
            joinedload(ServiceTicket.asset_links).joinedload(TicketAssetLink.asset)
        )
        if status:
            q = q.filter(ServiceTicket.status == status)
        if ticket_type:
            q = q.filter(ServiceTicket.ticket_type == ticket_type)
        if device_id:
            q = q.filter(ServiceTicket.device_id == device_id)
        if priority:
            q = q.filter(ServiceTicket.priority == priority)
        if asset_id:
            q = q.join(TicketAssetLink).filter(TicketAssetLink.asset_id == asset_id)
        tickets = q.order_by(ServiceTicket.created_at.desc()).all()
        return [self._enrich_links(t) for t in tickets]

    def get_ticket(self, ticket_id: UUID) -> ServiceTicket | None:
        ticket = (
            self.db.query(ServiceTicket)
            .options(
                joinedload(ServiceTicket.asset_links).joinedload(TicketAssetLink.asset),
                joinedload(ServiceTicket.work_notes),
            )
            .filter(ServiceTicket.id == ticket_id)
            .first()
        )
        if ticket:
            self._enrich_links(ticket)
        return ticket

    def get_ticket_by_number(self, number: str) -> ServiceTicket | None:
        ticket = (
            self.db.query(ServiceTicket)
            .options(
                joinedload(ServiceTicket.asset_links).joinedload(TicketAssetLink.asset)
            )
            .filter(ServiceTicket.number == number)
            .first()
        )
        if ticket:
            self._enrich_links(ticket)
        return ticket

    def update_ticket(
        self, ticket_id: UUID, payload: ServiceTicketUpdate
    ) -> ServiceTicket | None:
        ticket = self.db.get(ServiceTicket, ticket_id)
        if not ticket:
            return None
        data = payload.model_dump(exclude_unset=True)
        old_status = ticket.status
        for k, v in data.items():
            setattr(ticket, k, v)

        if "status" in data and data["status"] != old_status:
            self._apply_status_side_effects(ticket, old_status, data["status"], actor=None)

        self.db.commit()
        return self.get_ticket(ticket_id)

    def set_status(
        self, ticket_id: UUID, payload: TicketStatusUpdate
    ) -> ServiceTicket | None:
        ticket = self.db.get(ServiceTicket, ticket_id)
        if not ticket:
            return None
        old = ticket.status
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
        return self.get_ticket(ticket_id)

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

        # When repair/maintenance ticket closes, return linked assets from in_repair → deployed/in_stock
        if new_status in ("resolved", "closed") and ticket.ticket_type in (
            "maintenance",
            "incident",
            "change",
        ):
            links = (
                self.db.query(TicketAssetLink)
                .filter(TicketAssetLink.ticket_id == ticket.id)
                .all()
            )
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

    def delete_ticket(self, ticket_id: UUID) -> bool:
        ticket = self.db.get(ServiceTicket, ticket_id)
        if not ticket:
            return False
        self.db.delete(ticket)
        self.db.commit()
        return True

    # ---------- Asset integration ----------

    def create_ticket_for_asset(
        self, asset_id: UUID, payload: AssetTicketCreateRequest
    ) -> ServiceTicket:
        asset = self.db.get(Asset, asset_id)
        if not asset:
            raise ValueError("Asset not found")

        create = ServiceTicketCreate(
            title=payload.title,
            description=payload.description
            or f"Asset: {asset.name} ({asset.asset_tag or asset.serial_number or asset.id})",
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

        return self.get_ticket(ticket.id)  # type: ignore[return-value]

    def link_asset(
        self, ticket_id: UUID, link: TicketAssetLinkCreate
    ) -> TicketAssetLink:
        ticket = self.db.get(ServiceTicket, ticket_id)
        if not ticket:
            raise ValueError("Ticket not found")
        asset = self.db.get(Asset, link.asset_id)
        if not asset:
            raise ValueError("Asset not found")

        existing = (
            self.db.query(TicketAssetLink)
            .filter(
                TicketAssetLink.ticket_id == ticket_id,
                TicketAssetLink.asset_id == link.asset_id,
            )
            .first()
        )
        if existing:
            existing.role = link.role
            existing.notes = link.notes
            self.db.commit()
            return existing

        row = TicketAssetLink(
            ticket_id=ticket_id,
            asset_id=link.asset_id,
            role=link.role,
            notes=link.notes,
        )
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

    def unlink_asset(self, ticket_id: UUID, asset_id: UUID) -> bool:
        row = (
            self.db.query(TicketAssetLink)
            .filter(
                TicketAssetLink.ticket_id == ticket_id,
                TicketAssetLink.asset_id == asset_id,
            )
            .first()
        )
        if not row:
            return False
        self.db.delete(row)
        self.db.commit()
        return True

    def add_work_note(self, ticket_id: UUID, payload: WorkNoteCreate) -> TicketWorkNote:
        if not self.db.get(ServiceTicket, ticket_id):
            raise ValueError("Ticket not found")
        note = TicketWorkNote(
            ticket_id=ticket_id,
            author=payload.author,
            body=payload.body,
            is_public=payload.is_public,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_work_notes(self, ticket_id: UUID) -> list[TicketWorkNote]:
        return (
            self.db.query(TicketWorkNote)
            .filter(TicketWorkNote.ticket_id == ticket_id)
            .order_by(TicketWorkNote.created_at.asc())
            .all()
        )

    def tickets_for_asset(self, asset_id: UUID) -> list[ServiceTicket]:
        return self.list_tickets(asset_id=asset_id)

    # ---------- Automated integrations ----------

    def open_ticket_on_asset_status(
        self,
        asset: Asset,
        from_status: str,
        to_status: str,
        actor: str | None = None,
    ) -> ServiceTicket | None:
        """
        Called from AssetService when status changes.
        Creates ITSM tickets for operationally meaningful transitions.
        """
        if to_status == "in_repair":
            return self.create_ticket(
                ServiceTicketCreate(
                    title=f"Repair: {asset.name}",
                    description=(
                        f"Asset moved to in_repair from {from_status}.\n"
                        f"Tag: {asset.asset_tag} | SN: {asset.serial_number}"
                    ),
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
        today = date.today()
        from datetime import timedelta

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
            # Skip if an open warranty ticket already exists for this asset
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

            ticket = self.create_ticket(
                ServiceTicketCreate(
                    title=f"Warranty expiring: {asset.name}",
                    description=(
                        f"Warranty ends {asset.warranty_end}. "
                        f"Provider: {asset.warranty_provider or 'n/a'}. "
                        f"Ref: {asset.warranty_lookup_ref or 'n/a'}."
                    ),
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
            created.append(ticket)
        return created
