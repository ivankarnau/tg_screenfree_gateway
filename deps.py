# deps.py
import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET не задана в окружении")

ALGO = "HS256"
bearer_scheme = HTTPBearer()

def current_user(
    cred: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    token = cred.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
        return payload
    except JWTError:
        raise HTTPException(401, detail="Invalid JWT")
