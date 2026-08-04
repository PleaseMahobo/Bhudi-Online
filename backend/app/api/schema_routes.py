from fastapi import APIRouter

from app.services.schema_service import SchemaService


router = APIRouter(
    prefix="/api/schema",
    tags=["Schema Sync"]
)

service = SchemaService()


@router.get("/status")
def schema_status():

    return service.get_status()