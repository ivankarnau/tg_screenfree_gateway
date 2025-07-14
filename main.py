# main.py

import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import jwt, JWTError

from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError,
    UnexpectedFormatError,
)

# === Настройка из ENV ===
BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("❌ В ENV должны быть BOT_TOKEN и JWT_SECRET")

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/telegram")

app = FastAPI(title="ScreenFree Gateway")

# === CORS Middleware ===
# замените origin на ваш фронтенд, или оставьте ["*"] для теста
origins = [
    "https://tg-screenfree.vercel.app",
    "https://www.tg-screenfree.vercel.app",
    # "http://localhost:5173",  # если локально тестируете фронт
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# === Схемы ===
class AuthRequest(BaseModel):
    initData: str

class BalanceResponse(BaseModel):
    user_id: int
    balance: int

# === Хелперы ===
def verify_init_data(raw_qs: str) -> dict:
    try:
        InitData.parse(raw_qs).validate(BOT_TOKEN, lifetime=24 * 3600)
    except (SignInvalidError, SignMissingError,
            AuthDateMissingError, ExpiredError,
            UnexpectedFormatError) as e:
        raise HTTPException(status_code=401, detail=f"bad signature: {e}")
    # Извлекаем JSON-пользователя из initData
    import urllib.parse as up, json
    user_part = up.parse_qs(raw_qs)["user"][0]
    user_json = up.unquote_plus(user_part)
    return json.loads(user_json)

# === Эндпоинты ===
@app.post("/auth/telegram")
async def auth_telegram(body: AuthRequest):
    user = verify_init_data(body.initData)
    payload = {
        "sub": str(user["id"]),       # sub как строка
        "first": user.get("first_name", ""),
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return {"access_token": token}

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise credentials_exception
    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception
    return {"user_id": int(sub)}

@app.get("/wallet/balance", response_model=BalanceResponse)
async def get_balance(current_user: dict = Depends(get_current_user)):
    # Здесь вместо 0 верните настоящий баланс из БД
    return BalanceResponse(user_id=current_user["user_id"], balance=0)

# (Можно добавить /ping для проверки живости)
@app.get("/ping")
async def ping():
    return {"pong": True}
