from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TicketAssignmentRequest(BaseModel):
    technician_id: UUID
    assignment_group_id: UUID | None = None


class TicketAssignmentResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    technician_id: UUID
    assignment_group_id: UUID | None
    tenant_id: UUID | None
    assigned_by: str | None
    active: bool
    assigned_at: datetime
    unassigned_at: datetime | None

    class Config:
        from_attributes = True


class SLAEscalationResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    tenant_id: UUID | None
    breach_type: str
    level: int
    recipient: str | None
    notification_status: str
    error: str | None
    created_at: datetime
    notified_at: datetime | None

    class Config:
        from_attributes = True


class AttachmentUploadResponse(BaseModel):
    id: UUID
    ticket_id: UUID
    tenant_id: UUID | None
    filename: str
    content_type: str | None
    size_bytes: int | None
    uploaded_by: str | None
    created_at: datetime
    download_url: str

    class Config:
        from_attributes = True
