from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from auth import router as auth_router
import db                         # ← наш модуль с пулом

app = FastAPI()
app.add_event_handler("startup", db.attach_pool(app))
app.include_router(auth_router)

# ---------- CORS --------------------------------------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------------------------------------------

# ---------- DB: создаём таблицу users на старте -------------------
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
# ------------------------------------------------------------------

# ---------- PING --------------------------------------------------
@app.get("/ping")
async def ping():
    return {"pong": "🏓"}
# ------------------------------------------------------------------

# ---------- SIMPLE BALANCE STUB ----------------------------------
class BalanceOut(BaseModel):
    user_id: int
    balance: int


@app.get("/wallet/balance", response_model=BalanceOut)
async def balance(user_id: int = 1):
    return {"user_id": user_id, "balance": 0}
# ------------------------------------------------------------------
