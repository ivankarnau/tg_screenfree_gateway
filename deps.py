# deps.py
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET не задана в окружении")

ALGO = "HS256"
bearer = HTTPBearer()

def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer)
):
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid JWT",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid token: missing sub",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"user_id": int(sub)}
