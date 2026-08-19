from fastapi import APIRouter, Depends

from app.core.supabase_auth import get_supabase_user

router = APIRouter(prefix="/supabase-auth", tags=["supabase-auth"])


@router.get("/me")
def supabase_me(user=Depends(get_supabase_user)):
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "active": user.active,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
    }
