import os
import asyncpg
from fastapi import FastAPI

# Берём строку подключения из переменной окружения Railway
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise RuntimeError("DATABASE_URL не задана в окружении")

_pool: asyncpg.Pool | None = None

async def init_db(app: FastAPI):
    """
    Функция-инициализатор, которую нужно зарегить в FastAPI как:
    
      app = FastAPI()
      @app.on_event("startup")
      async def startup():
          await init_db(app)
      @app.on_event("shutdown")
      async def shutdown():
          await close_db()
    """
    global _pool
    _pool = await asyncpg.create_pool(dsn=DB_URL)

    # создаём таблицы, если они ещё не созданы
    async with _pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
          id SERIAL PRIMARY KEY,
          telegram_id BIGINT UNIQUE NOT NULL,
          first_name TEXT,
          created_at TIMESTAMPTZ DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS wallets (
          user_id INT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          available NUMERIC(12,2) NOT NULL DEFAULT 0,
          reserved  NUMERIC(12,2) NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tokens (
          token_id   UUID PRIMARY KEY,
          user_id    INT REFERENCES users(id) ON DELETE CASCADE,
          amount     NUMERIC(12,2) NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now(),
          redeemed_at TIMESTAMPTZ
        );

        CREATE TABLE IF NOT EXISTS transfers (
          id         SERIAL PRIMARY KEY,
          from_user  INT REFERENCES users(id) ON DELETE CASCADE,
          to_user    INT REFERENCES users(id) ON DELETE CASCADE,
          amount     NUMERIC(12,2) NOT NULL,
          created_at TIMESTAMPTZ DEFAULT now()
        );
        """)

async def close_db():
    """
    Закрывает пул при завершении приложения
    """
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

def get_pool() -> asyncpg.Pool:
    """
    Возвращает готовый пул соединений.
    Вызывать можно из любых роутеров через Depends или напрямую.
    """
    if _pool is None:
        raise RuntimeError("DB не инициализирована. Проверьте, что init_db был вызван на старте.")
    return _pool
