# db.py
import os
import asyncpg
from fastapi import FastAPI

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL не задана в окружении")

pool: asyncpg.Pool | None = None

async def init_db(app: FastAPI):
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)
    async with pool.acquire() as conn:
        # создаём таблицы, если их ещё нет
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
          user_id BIGINT PRIMARY KEY,
          balance NUMERIC(18,2) NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS transfers (
          id BIGSERIAL PRIMARY KEY,
          from_user BIGINT NOT NULL REFERENCES wallets(user_id),
          to_user   BIGINT NOT NULL REFERENCES wallets(user_id),
          amount    NUMERIC(18,2) NOT NULL,
          ts        TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """)
    app.state.db = pool

async def close_db():
    global pool
    if pool:
        await pool.close()
