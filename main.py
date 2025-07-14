# gateway/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from auth       import router as auth_router
from wallet     import router as wallet_router
from sonic      import router as sonic_router
from db         import init_db, close_db
from bank_mock  import router as bank_router

app = FastAPI(title="ScreenFree Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db(app)

@app.on_event("shutdown")
async def on_shutdown():
    await close_db()

# Подключаем все роутеры
app.include_router(auth_router)    # /auth/telegram
app.include_router(wallet_router)  # /wallet/*
app.include_router(sonic_router)   # /sonic/*
app.include_router(bank_router)    # /bank/issuance

@app.get("/ping")
async def ping():
    return {"pong": True}
