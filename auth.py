import os
import hmac
import time
import hashlib
import urllib.parse as up

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

import db

# ────────────────────────────────────────────────────────────
#  Константы окружения
# ────────────────────────────────────────────────────────────
BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGO   = "HS256"

if not BOT_TOKEN:
    raise RuntimeError("env BOT_TOKEN not set")
if not JWT_SECRET:
    raise RuntimeError("env JWT_SECRET not set")

# ────────────────────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthIn(BaseModel):
    initData: str


# ────────────────────────────────────────────────────────────
def verify_telegram(init_data: str) -> dict:
    """
    Проверяем подпись Telegram (HMAC-SHA-256).
    Возвращаем dict c данными пользователя.
    """
    parsed = up.parse_qs(init_data, keep_blank_values=True)
    data_dict = {k: v[0] for k, v in parsed.items()}

    # ⚠️  Убираем оба контрольных поля
    hash_value = data_dict.pop("hash", None)
    data_dict.pop("signature", None)
    print("[AUTH] signature removed", flush=True)         # ← DEBUG-лог

    if not hash_value:
        raise HTTPException(400, "hash missing")

    check_string = "\n".join(f"{k}={data_dict[k]}" for k in sorted(data_dict))
    secret_key   = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc_hash    = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    print("[AUTH] check_string =", check_string, flush=True)
    print("[AUTH] client_hash  =", hash_value, flush=True)
    print("[AUTH] server_hash  =", calc_hash, flush=True)

    if calc_hash != hash_value:
        raise HTTPException(401, "bad signature")

    return data_dict


# ────────────────────────────────────────────────────────────
@router.post("/telegram")
async def auth_telegram(body: TelegramAuthIn):
    """
    Принимаем initData, проверяем подпись, записываем юзера в БД
    и возвращаем JWT access-token.
    """
    data = verify_telegram(body.initData)

    tg_id  = int(data["user_id"])
    first  = data.get("first_name", "")

    # Сохраняем пользователя (idempotent)
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

    payload = {
        "sub": tg_id,
        "first": first,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)
    return {"access_token": token}
