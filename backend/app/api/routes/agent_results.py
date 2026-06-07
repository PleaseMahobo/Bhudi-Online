from fastapi import APIRouter
from pydantic import BaseModel
from app.services.command_service import CommandService

router = APIRouter()


class ResultPayload(BaseModel):
    command_id: int
    result: str


@router.post("/")
def submit_result(payload: ResultPayload):

    CommandService.save_result(
        command_id=payload.command_id,
        result=payload.result
    )

    return {"status": "saved"}