from fastapi import APIRouter, Depends

from app.core.dependencies import require_permission
from app.services.device_service import get_devices


router = APIRouter()


@router.get(
    "/",
    dependencies=[
        Depends(
            require_permission(
                "device.read"
            )
        )
    ],
)
def list_devices():
    result = get_devices()

    return result.data