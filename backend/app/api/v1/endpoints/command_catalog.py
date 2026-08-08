from fastapi import APIRouter

from app.commands.catalog import get_command_catalog

router = APIRouter(prefix="/command-catalog", tags=["Command Catalog"])


@router.get("")
def command_catalog() -> dict:
    return {"commands": get_command_catalog()}
