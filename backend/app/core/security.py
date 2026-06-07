import os
import time
import jwt
import hashlib

SECRET_KEY = "CHANGE_ME_SUPER_SECRET"
ALGORITHM = "HS256"

# -------------------------
# JWT (Dashboard users)
# -------------------------

def create_jwt(data: dict, expires_in: int = 3600):
    payload = data.copy()
    payload["exp"] = time.time() + expires_in
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_jwt(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None


# -------------------------
# API KEY (Agents)
# -------------------------

def hash_api_key(key: str):
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(provided: str, stored_hash: str):
    return hash_api_key(provided) == stored_hash