import os
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from db import get_pool

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET не задана")

ALGO = "HS256"
bearer = HTTPBearer()

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(401, "Invalid token")
    telegram_id = int(payload["sub"])
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "INSERT INTO users (telegram_id, first_name) VALUES ($1,$2) "
            "ON CONFLICT (telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name "
            "RETURNING id",
            telegram_id, payload.get("first","")
        )
        uid = rec["id"]
        await conn.execute(
            "INSERT INTO wallets (user_id) VALUES ($1) "
            "ON CONFLICT (user_id) DO NOTHING",
            uid
        )
    return {"user_id": uid}
