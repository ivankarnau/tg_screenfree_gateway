import os, time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError,
    UnexpectedFormatError
)
from db import get_pool

BOT_TOKEN = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
ALGO = "HS256"
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN и JWT_SECRET должны быть заданы")

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    init_data: str

def verify_init_data(raw: str):
    try:
        init = InitData.parse(raw)
        init.validate(bot_token=BOT_TOKEN, lifetime=24*3600)
    except (
        SignInvalidError, SignMissingError,
        AuthDateMissingError, ExpiredError,
        UnexpectedFormatError
    ) as e:
        raise HTTPException(401, f"Invalid init_data: {e}")
    user = init.user
    if not user or not hasattr(user, "id"):
        raise HTTPException(400, "Нет информации о пользователе")
    return user

@router.post("/telegram")
async def auth_telegram(body: AuthRequest):
    user = verify_init_data(body.init_data)
    telegram_id = int(user.id)
    first = user.first_name or ""

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
            telegram_id, first
        )
        uid = rec["id"]
        await conn.execute(
            "INSERT INTO wallets (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
            uid
        )

    now = int(time.time())
    token = jwt.encode(
        {"sub": str(telegram_id), "first": first, "iat": now, "exp": now + 7*24*3600},
        JWT_SECRET, algorithm=ALGO
    )
    return {"access_token": token}
