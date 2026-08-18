from __future__ import annotations

import secrets
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.agent import Agent
from app.schemas.itsm import ServiceTicketCreate, ServiceTicketResponse
from app.services.itsm_service import ITSMService

router = APIRouter(prefix="/agent-support", tags=["Agent Support"])

class AgentTicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None
    priority: str = "medium"
    category: str | None = None
    requester: str | None = None

class AgentTicketList(BaseModel):
    tickets: list[ServiceTicketResponse]

def _authenticate_agent(agent_id: UUID, agent_token: str, db: Session) -> Agent:
    agent = db.get(Agent, agent_id)
    stored = agent.enrollment_token if agent else None
    if agent is None or not agent.enabled or agent.revoked or not stored or not secrets.compare_digest(str(stored), agent_token):
        raise HTTPException(status_code=401, detail="Invalid agent credentials")
    if agent.tenant_id is None:
        raise HTTPException(status_code=409, detail="Agent is not assigned to a customer tenant")
    return agent

def _response(ticket) -> ServiceTicketResponse:
    return ServiceTicketResponse.model_validate(ticket)

def _token(agent_token: str | None) -> str:
    if not agent_token:
        raise HTTPException(status_code=401, detail="Missing agent credentials")
    return agent_token

@router.post("/tickets", response_model=ServiceTicketResponse, status_code=status.HTTP_201_CREATED)
def create_support_ticket(payload: AgentTicketCreate, agent_id: UUID = Query(...), agent_token: str | None = Header(None, alias="X-Bhudi-Agent-Token"), db: Session = Depends(get_db)):
    agent = _authenticate_agent(agent_id, _token(agent_token), db)
    ticket_payload = ServiceTicketCreate(title=payload.title, description=payload.description, ticket_type="incident", status="open", priority=payload.priority, category=payload.category, requester=payload.requester or agent.hostname, source="endpoint_support", source_ref=str(agent.id), tenant_id=agent.tenant_id, device_id=agent.device_id)
    try:
        ticket = ITSMService(db).create_ticket(ticket_payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(ticket)

@router.get("/tickets", response_model=AgentTicketList)
def list_support_tickets(agent_id: UUID = Query(...), agent_token: str | None = Header(None, alias="X-Bhudi-Agent-Token"), db: Session = Depends(get_db)):
    agent = _authenticate_agent(agent_id, _token(agent_token), db)
    tickets = ITSMService(db).list_tickets(tenant_id=agent.tenant_id, device_id=agent.device_id, q=None)
    return AgentTicketList(tickets=[_response(ticket) for ticket in tickets])

@router.get("/tickets/{ticket_id}", response_model=ServiceTicketResponse)
def get_support_ticket(ticket_id: UUID, agent_id: UUID = Query(...), agent_token: str | None = Header(None, alias="X-Bhudi-Agent-Token"), db: Session = Depends(get_db)):
    agent = _authenticate_agent(agent_id, _token(agent_token), db)
    ticket = ITSMService(db).get_ticket(ticket_id, tenant_id=agent.tenant_id)
    if ticket is None or ticket.device_id != agent.device_id:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return _response(ticket)
