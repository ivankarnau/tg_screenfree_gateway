import os, hmac, time, hashlib, json
import urllib.parse as up
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel
import db

# ──────────────────── env
BOT_TOKEN  = os.getenv("BOT_TOKEN") or ""
JWT_SECRET = os.getenv("JWT_SECRET") or ""
ALGO       = "HS256"

if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN / JWT_SECRET not set")

# ──────────────────── router
router = APIRouter(prefix="/auth", tags=["auth"])

class TelegramAuthIn(BaseModel):
    initData: str


# ──────────────────── helpers
def _build_check_string(init_data: str) -> tuple[str, str]:
    """
    Возвращает кортеж (check_string, hash_value).
    check_string формируется БЕЗ URL-декодирования,
    строго по правилам Telegram.
    """
    parts = init_data.split("&")
    hash_value = ""
    filtered: list[str] = []

    for p in parts:
        if p.startswith("hash="):
            hash_value = p.split("=", 1)[1]
        elif p.startswith("signature="):
            # игнорируем новое поле
            continue
        else:
            filtered.append(p)

    # сортируем по ключу (до '=')
    filtered.sort(key=lambda s: s.split("=", 1)[0])
    check_string = "\n".join(filtered)
    return check_string, hash_value


def _parse_user(init_data: str) -> dict:
    """Декодируем только чтобы достать user_id / first_name."""
    parsed = up.parse_qs(init_data, keep_blank_values=True)
    user_json = parsed["user"][0]
    return json.loads(user_json)


def verify_telegram(init_data: str) -> dict:
    check_string, client_hash = _build_check_string(init_data)
    if not client_hash:
        raise HTTPException(400, "hash missing")

    secret = hashlib.sha256(BOT_TOKEN.encode()).digest()
    server_hash = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()

    print("[AUTH] BOT", BOT_TOKEN[:10], "...", BOT_TOKEN[-5:], flush=True)
    print("[AUTH] client", client_hash, flush=True)
    print("[AUTH] server", server_hash, flush=True)

    if server_hash != client_hash:
        raise HTTPException(401, "bad signature")

    return _parse_user(init_data)


# ──────────────────── endpoint
@router.post("/telegram")
async def auth_telegram(body: TelegramAuthIn):
    data = verify_telegram(body.initData)

    tg_id  = int(data["id"])
    first  = data.get("first_name", "")

    pool = await db.get_pool()
    async with pool.acquire() as c:
        await c.execute(
            """
            INSERT INTO users (telegram_id, first_name)
            VALUES ($1,$2)
            ON CONFLICT (telegram_id) DO NOTHING
            """,
            tg_id, first
        )

    token = jwt.encode({"sub": tg_id, "first": first, "iat": int(time.time())},
                       JWT_SECRET, algorithm=ALGO)
    return {"access_token": token}
