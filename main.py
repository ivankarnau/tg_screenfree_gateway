# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from deps import current_user
from fastapi import Depends


import db
from auth import router as auth_router     # ← теперь импорт проходит

app = FastAPI()

# ─── подключаем пул PG -------------------------------------------------
app.add_event_handler("startup", db.attach_pool(app))
# ─── роуты -------------------------------------------------------------
app.include_router(auth_router)
# ─── CORS --------------------------------------------------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "https://tg-screenfree.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tg-screenfree.vercel.app", 
                   "https://tgscreenfreegateway-production.up.railway.app",
                   "*"],  # на проде лучше сузить список!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],    # важно: разрешаем Authorization
)
# ─── ensure tables -----------------------------------------------------
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
# ─── healthcheck -------------------------------------------------------
@app.get("/ping")
async def ping():
    return {"pong": "🏓"}
# ─── simple balance stub ----------------------------------------------
from pydantic import BaseModel
class BalanceOut(BaseModel):
    user_id: int
    balance: int

@app.get("/wallet/balance", response_model=BalanceOut)
async def balance(user=Depends(current_user)):
    return {"user_id": user["sub"], "balance": 0}