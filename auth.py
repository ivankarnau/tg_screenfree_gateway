# auth.py
import os
import time
import json
import urllib.parse as up

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
    raise RuntimeError("BOT_TOKEN и JWT_SECRET должны быть заданы")

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    init_data: str

def verify_init_data(raw: str) -> dict:
    """
    Парсит и валидирует init_data от Telegram.
    Если подпись или срок годности не проходят — бросает HTTPException(401).
    Возвращает payload.user из Telegram.
    """
    try:
        obj = InitData.parse(raw)
        obj.validate(BOT_TOKEN, lifetime=24 * 3600)
    except (SignInvalidError, SignMissingError,
            AuthDateMissingError, ExpiredError,
            UnexpectedFormatError) as e:
        raise HTTPException(401, f"Invalid init_data: {e}")

    # Внутри InitData.payload хранится словарь со всеми полями, включая 'user' — строку JSON.
    user_json = obj.payload.get("user")
    if not user_json:
        raise HTTPException(400, "No user info in init_data")

    # user_json приходит закодированной, поэтому декодируем
    try:
        user = json.loads(user_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "Bad user JSON")

    return user

@router.post("/telegram")
async def auth_telegram(body: AuthRequest):
    # 1) разбираем и проверяем init_data
    user = verify_init_data(body.init_data)
    telegram_id = int(user["id"])
    first_name = user.get("first_name", "")

    # 2) создаём/апдейтим запись в users + гарантия строки wallets
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
        await conn.execute(
            """
            INSERT INTO wallets (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            user_id
        )

    # 3) генерируем JWT
    now = int(time.time())
    payload = {
        "sub": str(telegram_id),
        "iat": now,
        "exp": now + 7 * 24 * 3600  # например, токен живёт неделю
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGO)
    return {"access_token": token}
