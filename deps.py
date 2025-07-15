from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from db import get_pool

JWT_SECRET = os.getenv("JWT_SECRET")  # должен быть задан в Railway
ALGORITHM = "HS256"
bearer = HTTPBearer()

async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer)
):
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(401, "Invalid token")

    tg_id = int(payload.get("sub", 0))
    first = payload.get("first", "")

    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            """
            INSERT INTO users (telegram_id, first_name)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE
              SET first_name = EXCLUDED.first_name
            RETURNING id
            """,
            tg_id, first
        )
        uid = rec["id"]
        await conn.execute(
            "INSERT INTO wallets (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
            uid
        )
    return {"user_id": uid}
