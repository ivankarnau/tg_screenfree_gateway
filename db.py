import os
import asyncpg
from fastapi import FastAPI

# ---- строка подключения -------------------------------------------------
DB_URL = os.getenv("DATABASE_URL")
if DB_URL is None:
    raise RuntimeError(
        "Переменная окружения DATABASE_URL не найдена. "
        "Добавь её в Railway → Variables."
    )
# ------------------------------------------------------------------------

_pool: asyncpg.Pool | None = None


async def get_pool(app: FastAPI | None = None) -> asyncpg.Pool:
    """
    Возвращает единый пул соединений.
    Создаёт его при первом вызове.
    """
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=DB_URL)
    return _pool


def attach_pool(app: FastAPI):
    """
    Хук для FastAPI — создаёт пул при старте приложения.
    """
    async def _create():
        await get_pool(app)
    return _create
