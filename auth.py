import os
import hmac
import time
import hashlib
import urllib.parse as up

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

import db

# ---------------------------------------------------------------------
# Константы окружения
# ---------------------------------------------------------------------
BOT_TOKEN: str | None  = os.getenv("BOT_TOKEN")
JWT_SECRET: str | None = os.getenv("JWT_SECRET")
ALGO = "HS256"

if not BOT_TOKEN:
    raise RuntimeError("env BOT_TOKEN not set")
if not JWT_SECRET:
    raise RuntimeError("env JWT_SECRET not set")

# ---------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthIn(BaseModel):
    initData: str


# ---------------------------------------------------------------------
def verify_telegram(init_data: str) -> dict:
    """
    Проверяем подпись Telegram (HMAC-SHA-256).
    Принимаем строку initData, возвращаем dict с данными пользователя.
    """
    parsed = up.parse_qs(init_data, keep_blank_values=True)
    data_dict = {k: v[0] for k, v in parsed.items()}

    # ⚠️ Убираем оба контрольных поля, оставляем только «чистые» данные
    hash_value = data_dict.pop("hash", None)
    data_dict.pop("signature", None)           # ← новая проверка ‼
    if not hash_value:
        raise HTTPException(400, "hash missing")

    check_string = "\n".join(f"{k}={data_dict[k]}" for k in sorted(data_dict))
    secret_key   = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc_hash    = hmac.new(
        secret_key, check_string.encode(), hashlib.sha256
    ).hexdigest()

    if calc_hash != hash_value:
        raise HTTPException(401, "bad signature")

    return data_dict


# ---------------------------------------------------------------------
@router.post("/telegram")
async def auth_telegram(body: TelegramAuthIn):
    """
    Принимаем initData, проверяем подпись, записываем юзера в БД и
    отдаём access-token (JWT).
    """
    data = verify_telegram(body.initData)

    tg_id = int(data["user_id"])
    first = data.get("first_name", "")

    # --- сохраняем юзера ------------------------------------------------
    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO users (telegram_id, first_name)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING
            """,
            tg_id,
            first,
        )

    # --- генерируем JWT -------------------------------------------------
    payload = {
        "sub": tg_id,
        "first": first,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGO)
    return {"access_token": token}
