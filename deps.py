# deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from db import get_pool

JWT_SECRET = ...
ALGORITHM = "HS256"

bearer = HTTPBearer()

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    telegram_id = int(payload["sub"])
    first = payload.get("first","")
    pool = get_pool()
    async with pool.acquire() as conn:
        # upsert user
        rec = await conn.fetchrow(
            "INSERT INTO users (telegram_id, first_name) VALUES ($1,$2) "
            "ON CONFLICT (telegram_id) DO UPDATE SET first_name=EXCLUDED.first_name "
            "RETURNING id",
            telegram_id, first
        )
        uid = rec["id"]
        # ensure wallet row
        await conn.execute(
            "INSERT INTO wallets (user_id) VALUES ($1) "
            "ON CONFLICT (user_id) DO NOTHING",
            uid
        )
    return {"user_id": uid}
