# deps.py
from fastapi import Header, HTTPException
from jose import jwt, JWTError
import os

SECRET = os.getenv("JWT_SECRET")
ALGO   = "HS256"

def current_user(auth: str = Header(None, alias="Authorization")):
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing JWT")
    token = auth.split()[1]
    try:
        payload = jwt.decode(token, SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(401, "Invalid JWT")
    return payload              # {sub: <telegram_id>, first: ...}
