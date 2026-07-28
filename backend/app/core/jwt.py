from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.core.config import settings


# ==========================================================
# JWT Configuration
# ==========================================================

SECRET_KEY = settings.JWT_SECRET_KEY

ALGORITHM = settings.JWT_ALGORITHM


ACCESS_TOKEN_TYPE = "access"

REFRESH_TOKEN_TYPE = "refresh"


ACCESS_TOKEN_EXPIRE = timedelta(
    minutes=settings.JWT_ACCESS_EXPIRE_MINUTES,
)


REFRESH_TOKEN_EXPIRE = timedelta(
    days=settings.JWT_REFRESH_EXPIRE_DAYS,
)


#
# Allows small clock differences between:
#
# - API servers
# - database servers
# - clients
#
CLOCK_SKEW_SECONDS = 30


JWT_ISSUER = getattr(
    settings,
    "JWT_ISSUER",
    "bhudi-api",
)


JWT_AUDIENCE = getattr(
    settings,
    "JWT_AUDIENCE",
    "bhudi-client",
)



# ==========================================================
# Time Helpers
# ==========================================================


def utcnow() -> datetime:
    """
    Returns timezone-aware UTC time.
    """

    return datetime.now(
        timezone.utc
    )



def utc_timestamp(
    value: datetime,
) -> int:
    """
    Convert datetime into Unix timestamp.
    """

    return int(
        value.timestamp()
    )



def expiry_time(
    delta: timedelta,
) -> datetime:
    """
    Calculate absolute expiry datetime.
    """

    return utcnow() + delta



# ==========================================================
# Base JWT Claims
# ==========================================================


def _base_claims(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    jwt_id: str | None = None,
) -> dict[str, Any]:
    """
    Common claims shared by all Bhudi JWT tokens.

    Claims:

        sub
        type
        iat
        nbf
        exp
        iss
        aud
        jti
    """

    issued = utcnow()

    expires = expiry_time(
        expires_delta
    )


    return {

        #
        # Authenticated user identifier
        #

        "sub": subject,


        #
        # access / refresh
        #

        "type": token_type,


        #
        # issued at
        #

        "iat": utc_timestamp(
            issued
        ),


        #
        # not valid before
        #

        "nbf": utc_timestamp(
            issued
        ),


        #
        # expiration
        #

        "exp": utc_timestamp(
            expires
        ),


        #
        # token origin
        #

        "iss": JWT_ISSUER,


        #
        # intended consumer
        #

        "aud": JWT_AUDIENCE,


        #
        # unique token identifier
        #

        "jti": jwt_id or str(
            uuid4()
        ),
    }
    
# ==========================================================
# Internal JWT Creator
# ==========================================================


def _create_token(
    *,
    subject: str,
    token_type: str,
    expires_delta: timedelta,
    session_id: str | None = None,
    token_family: str | None = None,
    generation: int = 1,
    jwt_id: str | None = None,
) -> str:
    """
    Internal JWT creation engine.

    Access token claims:

        sub
        type
        iat
        nbf
        exp
        iss
        aud
        jti


    Refresh token additional claims:

        sid
        fam
        gen
    """

    claims = _base_claims(
        subject=subject,
        token_type=token_type,
        expires_delta=expires_delta,
        jwt_id=jwt_id,
    )


    #
    # Refresh token specific claims
    #

    if token_type == REFRESH_TOKEN_TYPE:

        claims.update(
            {
                #
                # Authentication session ID
                #

                "sid": (
                    session_id
                    or str(uuid4())
                ),


                #
                # Token rotation family
                #

                "fam": (
                    token_family
                    or str(uuid4())
                ),


                #
                # Rotation generation number
                #

                "gen": generation,
            }
        )


    return jwt.encode(
        claims,
        SECRET_KEY,
        algorithm=ALGORITHM,
    )



# ==========================================================
# Access Token Creation
# ==========================================================


def create_access_token(
    *,
    subject: str,
) -> str:
    """
    Creates a short-lived access token.

    Used for API authorization.
    """

    return _create_token(

        subject=subject,

        token_type=ACCESS_TOKEN_TYPE,

        expires_delta=ACCESS_TOKEN_EXPIRE,
    )



# ==========================================================
# Refresh Token Creation
# ==========================================================


def create_refresh_token(
    *,
    subject: str,
    session_id: str | None = None,
    token_family: str | None = None,
    generation: int = 1,
) -> str:
    """
    Creates a refresh token.

    Supports:

    - first login
    - refresh rotation
    - session continuity
    - token-family tracking
    """

    return _create_token(

        subject=subject,

        token_type=REFRESH_TOKEN_TYPE,

        expires_delta=REFRESH_TOKEN_EXPIRE,

        session_id=session_id,

        token_family=token_family,

        generation=generation,
    )



# ==========================================================
# Refresh Token Rotation Helper
# ==========================================================


def rotate_refresh_token(
    *,
    subject: str,
    session_id: str,
    token_family: str,
    generation: int,
) -> str:
    """
    Creates the next refresh token
    in an existing token family.

    The caller provides the next
    generation number.

    Example:

        generation=1

            becomes

        generation=2
    """

    return create_refresh_token(

        subject=subject,

        session_id=session_id,

        token_family=token_family,

        generation=generation,
    )
    
# ==========================================================
# Enterprise JWT Decoder
# ==========================================================


def decode_token(
    token: str,
) -> dict[str, Any]:
    """
    Decode and validate a JWT.

    Validation:

    - Signature
    - Expiration
    - Not before
    - Issuer
    - Audience

    Any failure returns HTTP 401.
    """

    try:

        payload = jwt.decode(

            token,

            SECRET_KEY,

            algorithms=[
                ALGORITHM
            ],

            issuer=JWT_ISSUER,

            audience=JWT_AUDIENCE,

            options={

                "verify_exp": True,

                "verify_nbf": True,

                "verify_aud": True,

                "verify_iss": True,

                "require": [

                    "exp",

                    "iat",

                    "nbf",

                    "iss",

                    "aud",

                    "sub",

                    "type",

                    "jti",
                ],
            },

            leeway=CLOCK_SKEW_SECONDS,
        )


        return payload


    except JWTError as exc:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Invalid or expired authentication token",

            headers={
                "WWW-Authenticate": "Bearer",
            },

        ) from exc



# ==========================================================
# Claim Validation Helpers
# ==========================================================


def validate_token_type(
    payload: dict[str, Any],
    expected_type: str,
) -> None:
    """
    Ensure token is the expected type.

    Prevents:

        access token
            |
            X
        refresh endpoint


        refresh token
            |
            X
        API authorization
    """

    token_type = payload.get(
        "type"
    )


    if token_type != expected_type:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=(
                f"Expected {expected_type} token."
            ),

            headers={
                "WWW-Authenticate": "Bearer",
            },
        )



def validate_subject(
    payload: dict[str, Any],
) -> str:
    """
    Validate and return JWT subject.
    """

    subject = payload.get(
        "sub"
    )


    if not subject:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Token subject missing.",

            headers={
                "WWW-Authenticate": "Bearer",
            },
        )


    return subject



# ==========================================================
# Access Token Verification
# ==========================================================


def verify_access_token(
    token: str,
) -> dict[str, Any]:
    """
    Validate an access token.

    Checks:

    - signature
    - expiry
    - issuer
    - audience
    - subject
    - token type
    """

    payload = decode_token(
        token
    )


    validate_token_type(
        payload,
        ACCESS_TOKEN_TYPE,
    )


    validate_subject(
        payload
    )


    validate_access_claims(
        payload
    )


    return payload



# ==========================================================
# Refresh Token Verification
# ==========================================================


def verify_refresh_token(
    token: str,
) -> dict[str, Any]:
    """
    Validate a refresh token.

    Required refresh claims:

        sid
        fam
        gen
        jti
        sub
        exp
    """

    payload = decode_token(
        token
    )


    validate_token_type(
        payload,
        REFRESH_TOKEN_TYPE,
    )


    validate_subject(
        payload
    )


    validate_refresh_claims(
        payload
    )


    return payload



# ==========================================================
# Access Claim Validation
# ==========================================================


def validate_access_claims(
    payload: dict[str, Any],
) -> None:
    """
    Validate minimum access token claims.
    """

    required = (

        "sub",

        "jti",

    )


    missing = [

        claim

        for claim in required

        if payload.get(claim) is None

    ]


    if missing:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=(
                "Access token missing claims: "
                + ", ".join(missing)
            ),

            headers={
                "WWW-Authenticate": "Bearer",
            },
        )



# ==========================================================
# Refresh Claim Validation
# ==========================================================


def validate_refresh_claims(
    payload: dict[str, Any],
) -> None:
    """
    Validate enterprise refresh claims.
    """

    required = (

        "sid",

        "fam",

        "gen",

        "jti",

        "sub",

    )


    missing = [

        claim

        for claim in required

        if payload.get(claim) is None

    ]


    if missing:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail=(
                "Refresh token missing claims: "
                + ", ".join(missing)
            ),

            headers={
                "WWW-Authenticate": "Bearer",
            },
        )
        
    # ==========================================================
# Generic Token Helpers
# ==========================================================


def get_subject(
    token: str,
) -> str:
    """
    Returns the authenticated user ID.

    For access tokens this validates
    the access token type.
    """

    payload = verify_access_token(
        token
    )

    return payload["sub"]



def get_user_id(
    token: str,
) -> str:
    """
    Returns the user identifier from
    any valid JWT.
    """

    payload = decode_token(
        token
    )

    return payload["sub"]



def get_token_id(
    token: str,
) -> str:
    """
    Returns JWT ID (jti).
    """

    payload = decode_token(
        token
    )

    return payload["jti"]



def get_jwt_id(
    token: str,
) -> str:
    """
    Compatibility alias for JWT ID.

    Keeps compatibility with older
    service code.
    """

    return get_token_id(
        token
    )



def get_token_type(
    token: str,
) -> str:
    """
    Returns:

        access

    or

        refresh
    """

    payload = decode_token(
        token
    )

    return payload["type"]



# ==========================================================
# Refresh Token Metadata
# ==========================================================


def get_refresh_token_details(
    token: str,
) -> dict[str, Any]:
    """
    Returns metadata required for
    refresh-token rotation.

    Used by:

        AuthService.login()

        AuthService.refresh_access_token()
    """

    payload = verify_refresh_token(
        token
    )


    expiry = datetime.fromtimestamp(
        payload["exp"],
        tz=timezone.utc,
    )


    return {

        "user_id": payload["sub"],

        "jti": payload["jti"],

        #
        # Compatibility with older code
        #

        "jwt_id": payload["jti"],


        "session_id": payload["sid"],

        "token_family": payload["fam"],

        "generation": int(
            payload["gen"]
        ),


        "issued_at": datetime.fromtimestamp(
            payload["iat"],
            tz=timezone.utc,
        ),


        #
        # AuthService expects this
        #

        "expires": expiry,


        #
        # Explicit metadata name
        #

        "expires_at": expiry,


        "issuer": payload["iss"],

        "audience": payload["aud"],

        "type": payload["type"],
    }



# ==========================================================
# Refresh Token Claim Helpers
# ==========================================================


def get_session_id(
    token: str,
) -> str:
    """
    Returns refresh session identifier.
    """

    payload = verify_refresh_token(
        token
    )

    return payload["sid"]



def get_token_family(
    token: str,
) -> str:
    """
    Returns refresh token family.
    """

    payload = verify_refresh_token(
        token
    )

    return payload["fam"]



def get_generation(
    token: str,
) -> int:
    """
    Returns refresh generation number.
    """

    payload = verify_refresh_token(
        token
    )

    return int(
        payload["gen"]
    )



# ==========================================================
# Token Time Helpers
# ==========================================================


def get_expiration(
    token: str,
) -> datetime:
    """
    Returns token expiry timestamp.
    """

    payload = decode_token(
        token
    )

    return datetime.fromtimestamp(
        payload["exp"],
        tz=timezone.utc,
    )



def get_issued_at(
    token: str,
) -> datetime:
    """
    Returns token creation timestamp.
    """

    payload = decode_token(
        token
    )

    return datetime.fromtimestamp(
        payload["iat"],
        tz=timezone.utc,
    )



def seconds_until_expiry(
    token: str,
) -> int:
    """
    Returns remaining token lifetime.
    """

    remaining = (
        get_expiration(token)
        - utcnow()
    )


    return max(
        0,
        int(
            remaining.total_seconds()
        ),
    )



def token_remaining_lifetime(
    token: str,
) -> timedelta:
    """
    Returns remaining lifetime.
    """

    remaining = (
        get_expiration(token)
        - utcnow()
    )


    if remaining.total_seconds() < 0:

        return timedelta(
            seconds=0
        )


    return remaining



def is_expired(
    token: str,
) -> bool:
    """
    Returns True when JWT is expired.
    """

    return (
        get_expiration(token)
        <= utcnow()
    )
    
# ==========================================================
# Token State Helpers
# ==========================================================


def is_access_token(
    token: str,
) -> bool:
    """
    Returns True if token is a valid
    access token.
    """

    try:

        payload = verify_access_token(
            token
        )

        return (
            payload["type"]
            == ACCESS_TOKEN_TYPE
        )

    except HTTPException:

        return False



def is_refresh_token(
    token: str,
) -> bool:
    """
    Returns True if token is a valid
    refresh token.
    """

    try:

        payload = verify_refresh_token(
            token
        )

        return (
            payload["type"]
            == REFRESH_TOKEN_TYPE
        )

    except HTTPException:

        return False



def token_is_valid(
    token: str,
) -> bool:
    """
    Returns True when JWT passes
    signature and claim validation.
    """

    try:

        decode_token(
            token
        )

        return True


    except HTTPException:

        return False



def token_is_active(
    token: str,
) -> bool:
    """
    Returns True when JWT is valid
    and has not expired.
    """

    return (
        token_is_valid(token)
        and not is_expired(token)
    )



# ==========================================================
# Generic Claim Helpers
# ==========================================================


def get_claim(
    token: str,
    claim: str,
    default: Any = None,
) -> Any:
    """
    Return a claim from any valid JWT.
    """

    payload = decode_token(
        token
    )

    return payload.get(
        claim,
        default,
    )



def token_type(
    token: str,
) -> str:
    """
    Return JWT token type.
    """

    return str(
        get_claim(
            token,
            "type",
        )
    )



def token_jti(
    token: str,
) -> str:
    """
    Return JWT identifier.
    """

    return str(
        get_claim(
            token,
            "jti",
        )
    )



def session_id(
    token: str,
) -> str | None:
    """
    Return refresh session ID.
    """

    return get_claim(
        token,
        "sid",
    )



def token_family(
    token: str,
) -> str | None:
    """
    Return refresh token family.
    """

    return get_claim(
        token,
        "fam",
    )



def generation(
    token: str,
) -> int | None:
    """
    Return refresh token generation.
    """

    value = get_claim(
        token,
        "gen",
    )


    if value is None:

        return None


    return int(value)



# ==========================================================
# Dependency Compatibility Helpers
# ==========================================================


def extract_access_token_subject(
    token: str,
) -> str:
    """
    Extract authenticated user ID
    from an access token.

    Used by FastAPI dependencies.
    """

    return validate_subject(
        verify_access_token(
            token
        )
    )



def extract_refresh_token_subject(
    token: str,
) -> str:
    """
    Extract user ID from refresh token.
    """

    return validate_subject(
        verify_refresh_token(
            token
        )
    )



# ==========================================================
# Module Public API
# ==========================================================


__all__ = [

    #
    # Creation
    #

    "create_access_token",

    "create_refresh_token",

    "rotate_refresh_token",


    #
    # Verification
    #

    "verify_access_token",

    "verify_refresh_token",

    "decode_token",


    #
    # Metadata
    #

    "get_subject",

    "get_user_id",

    "get_token_id",

    "get_refresh_token_details",

    "get_session_id",

    "get_token_family",

    "get_generation",


    #
    # Expiry
    #

    "get_expiration",

    "seconds_until_expiry",

    "is_expired",


    #
    # Validation
    #

    "is_access_token",

    "is_refresh_token",

    "token_is_valid",

    "token_is_active",
]