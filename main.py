# main.py
import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from jose import jwt, JWTError

from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError,
    UnexpectedFormatError,
)

BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("❌ BOT_TOKEN и JWT_SECRET должны быть заданы в переменных окружения")

ALGO = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/telegram")

app = FastAPI(title="ScreenFree Gateway API")


class AuthRequest(BaseModel):
    initData: str


class BalanceResponse(BaseModel):
    user_id: int
    balance: int


def verify_init_data(raw_qs: str) -> dict:
    try:
        InitData.parse(raw_qs).validate(BOT_TOKEN, lifetime=24 * 3600)
    except (SignInvalidError, SignMissingError,
            AuthDateMissingError, ExpiredError,
            UnexpectedFormatError) as e:
        raise HTTPException(status_code=401, detail=f"bad signature: {e}")
    # достаём JSON-пользователя
    import urllib.parse as up, json
    user_json = up.unquote_plus(up.parse_qs(raw_qs)["user"][0])
    return json.loads(user_json)


@app.post("/auth/telegram")
async def auth_telegram(body: AuthRequest):
    user = verify_init_data(body.initData)
    # кодируем JWT: sub должен быть строкой, чтобы OAuth2PasswordBearer не ругался
    payload = {
        "sub": str(user["id"]),
        "first": user.get("first_name", ""),
        "iat": int(time.time()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGO)
    return {"access_token": token}


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGO])
    except JWTError:
        raise credentials_exception
    # проверяем обязательное поле sub
    sub = payload.get("sub")
    if sub is None:
        raise credentials_exception
    return {"user_id": int(sub)}


@app.get("/wallet/balance", response_model=BalanceResponse)
async def get_balance(current_user: dict = Depends(get_current_user)):
    # Здесь ваш реальный код: запрос к БД, вычисление баланса и т.д.
    # Для примера — возвращаем 0
    return BalanceResponse(user_id=current_user["user_id"], balance=0)
