import os, asyncpg
from fastapi import FastAPI

DB_URL = os.getenv("DATABASE_URL")

def attach_pool(app: FastAPI):
    """
    Создать пул и положить в app.state.pool
    (вызывается из main.py в startup).
    """
    async def _create():
        app.state.db = await asyncpg.create_pool(dsn=DB_URL)
    return _create

async def get_pool(app: FastAPI):
    """Вернуть готовый пул из app.state."""
    return app.state.db
