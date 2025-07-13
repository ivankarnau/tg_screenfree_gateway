import os
import hmac
import time
import hashlib
import urllib.parse as up

from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel

import db  # наш модуль с пулом соединений

# -----------------------------------------------------------------------------
# Константы и переменные окружения
# -----------------------------------------------------------------------------
BOT_TOKEN: str | None  = os.getenv("BOT_TOKEN")
JWT_SECRET: str | None = os.getenv("JWT_SECRET")
ALGO = "HS256"

if not BOT_TOKEN:
    raise RuntimeError("Переменная окружения BOT_TOKEN не найдена.")
if not JWT_SECRET:
    raise RuntimeError("Переменная окружения JWT_SECRET не найдена.")

# -----------------------------------------------------------------------------
# FastAPI-роутер
# -----------------------------------------------------------------------------
router = APIRouter(prefix="/auth", tags=["auth"])


# -----------------------------------------------------------------------------
# Pydantic-модель входных данных
# -----------------------------------------------------------------------------
class TelegramAuthIn(BaseModel):
    initData: str


# -----------------------------------------------------------------------------
# Проверка подписи Telegram
# -----------------------------------------------------------------------------
def verify_telegram(init_data: str) -> dict:
    """
    Проверяем подпись Telegram Mini-App.
    Возвращаем словарь с данными пользователя, если всё ок,
    иначе кидаем HTTP 401.
    """
    parsed = up.parse_qs(init_data, keep_blank_values=True)
    data_dict = {k: v[0] for k, v in parsed.items()}

    hash_ = data_dict.pop("hash", None)
    if not hash_:
        raise HTTPException(400, "field 'hash' missing")

    # Сортируем ключи по алфавиту и собираем check_string
    check_string = "\n".join(f"{k}={data_dict[k]}" for k in sorted(data_dict))

    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc_hash  = hmac.new(secret_key, check_string.encode(),
                          hashlib.sha256).hexdigest()

    if calc_hash != hash_:
        raise HTTPException(401, "bad signature")

    return data_dict


# -----------------------------------------------------------------------------
# POST /auth/telegram  →  выдаём JWT
# -----------------------------------------------------------------------------
@router.post("/telegram")
async def auth_telegram(body: TelegramAuthIn):
    """
    Принимаем initData из Telegram, проверяем подпись и
    записываем пользователя в БД. Возвращаем JWT.
    """
    data = verify_telegram(body.initData)

    tg_id  = int(data["user_id"])
    first  = data.get("first_name", "")

    # --- сохраняем пользователя в БД ----------------------------------------
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

    # --- формируем JWT -------------------------------------------------------
    payload = {
        "sub": tg_id,
        "first": first,
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGO)

    return {"access_token": token}
