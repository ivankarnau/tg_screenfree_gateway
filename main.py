# main.py
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth import router as auth_router
from wallet import router as wallet_router
from sonic import router as sonic_router

app = FastAPI(title="ScreenFree Gateway")

# CORS: разрешаем любые origin, методы и заголовки (для WebApp/Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем все роутеры
app.include_router(auth_router)    # /auth/telegram
app.include_router(wallet_router)  # /wallet/balance, /wallet/topup
app.include_router(sonic_router)   # /sonic/start, /sonic/status, /sonic/result

# Простая проверка живости
@app.get("/ping")
async def ping():
    return {"pong": True}
