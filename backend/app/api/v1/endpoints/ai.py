from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.ai import (
    AICapacityRequest,
    AIKnowledgeSearchRequest,
    AIPredictiveRequest,
    AIRemediationRequest,
    AIRootCauseRequest,
    AIRunResponse,
    AIScriptRequest,
    AITicketSummaryRequest,
    KnowledgeArticleCreate,
    KnowledgeArticleResponse,
)
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["AI"])


class AssistantChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    history: list[dict[str, str]] | None = None


class AssistantChatResponse(BaseModel):
    reply: str
    mode: str = "heuristic"
    latency_ms: int | None = None
    suggestions: list[str] = []


@router.post("/chat", response_model=AssistantChatResponse)
def assistant_chat(payload: AssistantChatRequest, db: Session = Depends(get_db)):
    """In-app Bhudi AI assistant panel."""
    from app.services.assistant_service import AssistantService

    result = AssistantService().chat(payload.message, history=payload.history)
    return AssistantChatResponse(**result)


@router.post("/root-cause", response_model=AIRunResponse)
def root_cause(payload: AIRootCauseRequest, db: Session = Depends(get_db)):
    return AIService(db).root_cause(payload)


@router.post("/script", response_model=AIRunResponse)
def generate_script(payload: AIScriptRequest, db: Session = Depends(get_db)):
    return AIService(db).generate_script(payload)


@router.post("/remediation", response_model=AIRunResponse)
def remediation(payload: AIRemediationRequest, db: Session = Depends(get_db)):
    return AIService(db).remediation(payload)


@router.post("/ticket-summary", response_model=AIRunResponse)
def ticket_summary(payload: AITicketSummaryRequest, db: Session = Depends(get_db)):
    return AIService(db).ticket_summary(payload)


@router.post("/knowledge/search")
def knowledge_search(payload: AIKnowledgeSearchRequest, db: Session = Depends(get_db)):
    return AIService(db).knowledge_search(payload)


@router.post("/predictive-failure", response_model=AIRunResponse)
def predictive_failure(payload: AIPredictiveRequest, db: Session = Depends(get_db)):
    return AIService(db).predictive_failure(payload)


@router.post("/capacity-forecast", response_model=AIRunResponse)
def capacity_forecast(payload: AICapacityRequest, db: Session = Depends(get_db)):
    return AIService(db).capacity_forecast(payload)


@router.post("/knowledge", response_model=KnowledgeArticleResponse, status_code=201)
def create_article(payload: KnowledgeArticleCreate, db: Session = Depends(get_db)):
    return AIService(db).create_article(payload)


@router.get("/knowledge", response_model=list[KnowledgeArticleResponse])
def list_articles(
    tenant_id: UUID | None = None,
    published_only: bool = True,
    db: Session = Depends(get_db),
):
    return AIService(db).list_articles(tenant_id=tenant_id, published_only=published_only)


@router.get("/runs", response_model=list[AIRunResponse])
def list_runs(
    task_type: str | None = None, limit: int = 50, db: Session = Depends(get_db)
):
    return AIService(db).list_runs(task_type=task_type, limit=min(limit, 200))
