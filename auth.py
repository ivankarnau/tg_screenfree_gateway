import hmac, hashlib, urllib.parse as up, os, time
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel
from fastapi import Depends
from fastapi import Request   # оставить, если нужно, можно убрать
from jose import jwt

import db    

router = APIRouter(prefix="/auth", tags=["auth"])

BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
ALGO = "HS256"

# ---------- NEW: модель тела запроса --------------------------------
class TelegramAuthIn(BaseModel):
    initData: str
# --------------------------------------------------------------------

def verify_telegram(init_data: str) -> dict:
    parsed = up.parse_qs(init_data, keep_blank_values=True)
    data_dict = {k: v[0] for k, v in parsed.items()}
    hash_ = data_dict.pop("hash", None)
    if not hash_:
        raise HTTPException(400, "hash missing")

    check_string = "\n".join(f"{k}={data_dict[k]}" for k in sorted(data_dict))
    secret_key = hashlib.sha256(BOT_TOKEN.encode()).digest()
    calc_hash = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()

    if calc_hash != hash_:
        raise HTTPException(401, "bad signature")
    return data_dict

@router.post("/telegram")
async def auth_telegram(data_in: TelegramAuthIn):   # ← вместо Request
    from main import get_pool
    data = verify_telegram(data_in.initData)

    tg_id = int(data["user_id"])
    first = data.get("first_name", "")

    # сохраняем пользователя
    pool = await db.get_pool(router.app)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, first_name)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING
        """, tg_id, first)

    payload = {"sub": tg_id, "first": first, "iat": int(time.time())}
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGO)
    return {"access_token": token}
