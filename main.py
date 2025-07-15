from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import init_db, close_db
from auth import router as auth_router
from wallet import router as wallet_router
from bank_mock import router as bank_router
from sonic import router as sonic_router

app = FastAPI(title="ScreenFree Gateway")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], allow_credentials=False
)

@app.on_event("startup")
async def startup():
    await init_db(app)

@app.on_event("shutdown")
async def shutdown():
    await close_db()

app.include_router(auth_router)    # /auth/telegram
app.include_router(wallet_router)  # /wallet/*
app.include_router(bank_router)    # /bank/issuance
app.include_router(sonic_router)   # /sonic/*

@app.get("/ping")
async def ping():
    return {"pong": True}
