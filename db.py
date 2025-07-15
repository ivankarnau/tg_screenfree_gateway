import os
import asyncpg
from fastapi import FastAPI

DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL не задана в окружении")

_pool: asyncpg.Pool | None = None

async def init_db(app: FastAPI):
    global _pool
    _pool = await asyncpg.create_pool(dsn=DB_URL)
    # создаём таблицы, если их ещё нет
    async with _pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          telegram_id BIGINT UNIQUE NOT NULL,
          first_name TEXT,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS wallets (
          user_id INT PRIMARY KEY REFERENCES users(id),
          available NUMERIC(12,2) NOT NULL DEFAULT 0,
          reserved  NUMERIC(12,2) NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS tokens (
          token_id   UUID PRIMARY KEY,
          user_id    INT REFERENCES users(id),
          amount     NUMERIC(12,2) NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now(),
          redeemed_at TIMESTAMPTZ
        );
        CREATE TABLE IF NOT EXISTS transfers (
          id         SERIAL PRIMARY KEY,
          from_user  INT REFERENCES users(id),
          to_user    INT REFERENCES users(id),
          amount     NUMERIC(12,2) NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

async def close_db():
    global _pool
    if _pool:
        await _pool.close()

def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB не инициализирована")
    return _pool
