# auth.py
import os
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt

from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError,
    SignMissingError,
    AuthDateMissingError,
    ExpiredError,
    UnexpectedFormatError,
)

from deps import JWT_SECRET, ALGO
from db import get_pool

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN и JWT_SECRET должны быть заданы в окружении")

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    init_data: str

def verify_init_data(raw: str):
    """
    Парсит и валидирует init_data от Telegram.
    Возвращает объект User (из init_data_py.types), у которого есть .id, .first_name и т.д.
    """
    try:
        init = InitData.parse(raw)
        # lifetime в секундах, например, сутки
        init.validate(bot_token=BOT_TOKEN, lifetime=24 * 3600)
    except (
        SignInvalidError,
        SignMissingError,
        AuthDateMissingError,
        ExpiredError,
        UnexpectedFormatError,
    ) as e:
        raise HTTPException(401, f"Invalid init_data: {e}")

    user = init.user  # здесь — Typed User объект
    if not user or not hasattr(user, "id"):
        raise HTTPException(400, "No user info in init_data")
    return user

@router.post("/telegram")
async def auth_telegram(body: AuthRequest):
    # 1) Распарсили и проверили init_data
    user = verify_init_data(body.init_data)
    telegram_id = int(user.id)
    first_name = user.first_name or ""

    # 2) Сохраняем пользователя и кошелёк
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
            telegram_id, first_name
        )
        user_id = rec["id"]
        # гарантируем, что у него есть запись в wallets
        await conn.execute(
            """
            INSERT INTO wallets (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id
        )

    # 3) Генерируем JWT
    now = int(time.time())
    payload = {
        "sub": str(telegram_id),
        "iat": now,
        "exp": now + 7 * 24 * 3600,
    }
    access_token = jwt.encode(payload, JWT_SECRET, algorithm=ALGO)
    return {"access_token": access_token}
