import os
import time
import json
import urllib.parse as up

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError, UnexpectedFormatError
)

# === Подхватываем переменные из ENV Railway ===
BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("❌ Задайте BOT_TOKEN и JWT_SECRET в ENV Railway")

ALGORITHM = "HS256"

app = FastAPI(title="ScreenFree Gateway")
bearer_scheme = HTTPBearer()

# === CORS: теперь пропускаем любые origin и любые методы (включая OPTIONS) ===
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # временно разрешаем все origin
    allow_credentials=True,
    allow_methods=["*"],        # GET, POST, OPTIONS и т.п.
    allow_headers=["*"],        # Authorization и любые другие заголовки
)

# === Схемы входных/выходных данных ===
class AuthRequest(BaseModel):
    initData: str

class BalanceResponse(BaseModel):
    user_id: int
    balance: int

# === Проверка initData от Telegram ===
def verify_init_data(raw_qs: str) -> dict:
    try:
        InitData.parse(raw_qs).validate(BOT_TOKEN, lifetime=24*3600)
    except (SignInvalidError, SignMissingError,
            AuthDateMissingError, ExpiredError,
            UnexpectedFormatError) as e:
        raise HTTPException(status_code=401, detail=f"bad signature: {e}")
    qs = up.parse_qs(raw_qs)
    user_part = qs["user"][0]
    user_json = up.unquote_plus(user_part)
    return json.loads(user_json)

# === Эндпоинт авторизации через Telegram ===
@app.post("/auth/telegram")
async def auth_telegram(data: AuthRequest):
    user = verify_init_data(data.initData)
    payload = {
        "sub": str(user["id"]),
        "first": user.get("first_name", ""),
        "iat": int(time.time()),
    }
    access_token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    return {"access_token": access_token}

# === Депенд на получение текущего юзера из Bearer-токена ===
def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Missing sub")
    return {"user_id": int(sub)}

# === Эндпоинт для получения баланса ===
@app.get("/wallet/balance", response_model=BalanceResponse)
async def get_balance(user=Depends(get_current_user)):
    # TODO: здесь вместо заглушки нужно достать реальные данные из БД
    return BalanceResponse(user_id=user["user_id"], balance=0)

# === Просто healthcheck ===
@app.get("/ping")
async def ping():
    return {"pong": True}
