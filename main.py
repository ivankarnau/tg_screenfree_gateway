# main.py :contentReference[oaicite:8]{index=8}
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from auth import router as auth_router
from deps import current_user

app = FastAPI()

# подключаем пул при старте
app.add_event_handler("startup", db.attach_pool(app))

# CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://tg-screenfree.vercel.app",
    "https://tgscreenfreegateway-production.up.railway.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # для продакшена сузьте список
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],      # важно разрешить Authorization
)

app.include_router(auth_router)

@app.on_event("startup")
async def ensure_tables():
    pool = await db.get_pool(app)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id           serial       PRIMARY KEY,
                telegram_id  bigint       UNIQUE,
                first_name   text,
                created_at   timestamptz  DEFAULT now()
            );
            """
        )

@app.get("/ping")
async def ping():
    return {"pong": "🏓"}

class BalanceOut(BaseModel):
    user_id: int
    balance: int

@app.get("/wallet/balance", response_model=BalanceOut)
async def balance(user=Depends(current_user)):
    return {"user_id": user["sub"], "balance": 0}
