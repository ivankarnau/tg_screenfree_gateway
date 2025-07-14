# main.py
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel

import db
from auth import router as auth_router

# ————— Настройки JWT —————
JWT_SECRET = os.getenv("JWT_SECRET", "")
ALGO       = "HS256"

# ————— Инициализация FastAPI —————
app = FastAPI()

# ─── Подключаем пул к PostgreSQL при старте ───
app.add_event_handler("startup", db.attach_pool(app))

# ─── Регистрируем ваш /auth/telegram роутер ───
app.include_router(auth_router)

# ─── CORS (разрешаем любые методы и заголовки, в т.ч. Authorization) ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "https://tg-screenfree.vercel.app",
        "https://tgscreenfreegateway-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Простенький healthcheck ─────────────────────────
@app.get("/ping")
async def ping():
    return {"pong": "🏓"}

# ─── Security: схема Bearer JWT ───────────────────────
security = HTTPBearer()

async def current_user(
    creds: HTTPAuthorizationCredentials = Depends(security)
):
    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid JWT")
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Invalid JWT payload")
    return {"sub": sub, **payload}

# ─── Модель ответа для баланса ───────────────────────
class BalanceOut(BaseModel):
    user_id: int
    balance: int

# ─── Защищённый эндпоинт GET /wallet/balance ─────────
@app.get("/wallet/balance", response_model=BalanceOut)
async def balance(user = Depends(current_user)):
    # здесь вместо "0" вы можете делать запрос в БД по user["sub"]
    return {"user_id": user["sub"], "balance": 0}
