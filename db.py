import os
import asyncpg
from fastapi import FastAPI

DB_URL = os.getenv("DATABASE_URL")
if DB_URL is None:
    raise RuntimeError(
        "Переменная окружения DATABASE_URL не найдена. "
        "Добавь её в Railway → Variables."
    )

_pool: asyncpg.Pool | None = None


async def get_pool(app: FastAPI | None = None) -> asyncpg.Pool:
    """Создаёт (один раз) и возвращает пул соединений."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=DB_URL)
    return _pool


def attach_pool(app: FastAPI):
    """Хук, который создаёт пул на старте FastAPI-приложения."""
    async def _create():
        await get_pool(app)
    return _create
