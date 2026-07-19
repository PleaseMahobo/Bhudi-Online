from __future__ import annotations

from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.core.jwt import get_subject
from app.repositories.user_repository import UserRepository



def get_access_token(
    request: Request,
) -> str:

    """
    Extract JWT access token.

    Priority:
    1. Authorization Bearer header
    2. HttpOnly access_token cookie

    Supports:
    - Browser clients
    - API clients
    """


    # ----------------------------------------
    # 1. Authorization Header
    # ----------------------------------------

    authorization = request.headers.get(
        "Authorization"
    )


    if authorization:

        scheme, _, token = authorization.partition(
            " "
        )


        if scheme.lower() == "bearer" and token:

            return token



    # ----------------------------------------
    # 2. Browser Cookie
    # ----------------------------------------

    cookie_token = request.cookies.get(
        "access_token"
    )


    if cookie_token:

        return cookie_token



    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials missing",
        headers={
            "WWW-Authenticate": "Bearer"
        },
    )




def get_current_user(
    token: str = Depends(get_access_token),
    db: Session = Depends(get_db),
):

    """
    Resolve authenticated user from JWT.

    Supports:
    - Authorization header
    - Secure HttpOnly cookie
    """


    try:

        user_id = get_subject(token)


    except Exception:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )



    repository = UserRepository(db)


    user = repository.get_by_id(
        user_id
    )


    if user is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )



    # Existing Bhudi schema uses "active"
    if not user.active:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )



    return user