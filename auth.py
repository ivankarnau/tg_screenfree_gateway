import os, hmac, time, hashlib, json, urllib.parse as up
from fastapi import APIRouter, HTTPException
from jose import jwt
from pydantic import BaseModel
import db

BOT_TOKEN  = os.getenv("BOT_TOKEN")  or ""
JWT_SECRET = os.getenv("JWT_SECRET") or ""
ALGO       = "HS256"

if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN or JWT_SECRET missing")

router = APIRouter(prefix="/auth", tags=["auth"])

class TelegramAuthIn(BaseModel):
    initData: str


# ────────────────────────────────────────────────────────────
def verify_telegram(init_data: str) -> dict:
    """
    Проверяем подпись Telegram (HMAC-SHA-256).
    Возвращаем dict user с id / имёнем.
    """
    # 1. разбираем (URL-декодирует!) → dict key → value
    parsed = up.parse_qs(init_data, keep_blank_values=True)
    data   = {k: v[0] for k, v in parsed.items()}

    hash_client = data.pop("hash", None)
    data.pop("signature", None)           # игнорируем новое поле

    if not hash_client:
        raise HTTPException(400, "hash missing")

    # 2. формируем check-string «key=value» (уже декодировано)
    check_string = "\n".join(
        f"{k}={data[k]}" for k in sorted(data)
    )

    secret   = hashlib.sha256(BOT_TOKEN.encode()).digest()
    hash_srv = hmac.new(secret, check_string.encode(),
                        hashlib.sha256).hexdigest()

    # DEBUG
    print("[AUTH] BOT", BOT_TOKEN[:10], "...", BOT_TOKEN[-5:], flush=True)
    print("[AUTH] client", hash_client, flush=True)
    print("[AUTH] server", hash_srv,      flush=True)

    if hash_srv != hash_client:
        raise HTTPException(401, "bad signature")

    return json.loads(data["user"])


# ────────────────────────────────────────────────────────────
@router.post("/telegram")
async def auth_telegram(payload: TelegramAuthIn):
    user = verify_telegram(payload.initData)

    tg_id = int(user["id"])
    first = user.get("first_name", "")

    pool = await db.get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO users (telegram_id, first_name)
               VALUES ($1,$2)
               ON CONFLICT (telegram_id) DO NOTHING""",
            tg_id, first
        )

    token = jwt.encode(
        {"sub": tg_id, "first": first, "iat": int(time.time())},
        JWT_SECRET, algorithm=ALGO
    )
    return {"access_token": token}
