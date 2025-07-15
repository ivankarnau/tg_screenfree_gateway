from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from init_data_py import validate_init_data
from deps import JWT_SECRET, ALGORITHM
from jose import jwt
from db import get_pool

router = APIRouter(prefix="/auth", tags=["auth"])

class AuthRequest(BaseModel):
    init_data: str   # <— обязательно snake_case

@router.post("/telegram")
async def auth_telegram(data: AuthRequest):
    # 1) проверяем подпись от Telegram
    ok, payload = validate_init_data(data.init_data, JWT_SECRET)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid init_data")

    # 2) создаём/апдейтим пользователя
    telegram_id = int(payload["id"])
    first = payload.get("first_name", "")
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            """INSERT INTO users (telegram_id, first_name)
               VALUES ($1, $2)
               ON CONFLICT (telegram_id) DO UPDATE
                 SET first_name=EXCLUDED.first_name
               RETURNING id""",
            telegram_id, first
        )
        uid = rec["id"]
        # гарантируем, что есть запись в wallets
        await conn.execute(
            """INSERT INTO wallets (user_id)
               VALUES ($1)
               ON CONFLICT (user_id) DO NOTHING""",
            uid
        )

    # 3) отдаем JWT
    token = jwt.encode({"sub": str(telegram_id)}, JWT_SECRET, algorithm=ALGORITHM)
    return {"access_token": token}
