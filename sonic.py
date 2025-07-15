# gateway/sonic.py

import asyncio
import time
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from deps import current_user
from db import get_pool

router = APIRouter(prefix="/sonic", tags=["sonic"])


# ----------------------------------
# 1) Сервис фоновых измерений
# ----------------------------------
class SonicService:
    def __init__(self):
        # job_id → { user: uid, status: str, result: dict | None }
        self._jobs: Dict[str, Dict] = {}

    async def start(self, uid: int) -> str:
        job_id = str(time.time_ns())
        self._jobs[job_id] = {"user": uid, "status": "pending", "result": None}
        # запускаем фоновую задачу
        asyncio.create_task(self._run(job_id))
        return job_id

    async def _run(self, job_id: str):
        # меняем статус, ждём 3 секунды (имитация замера)
        self._jobs[job_id]["status"] = "running"
        await asyncio.sleep(3)
        # записываем результат
        self._jobs[job_id]["result"] = {"distance_cm": 42, "timestamp": time.time()}
        self._jobs[job_id]["status"] = "done"

    def status(self, job_id: str, uid: int) -> str | None:
        job = self._jobs.get(job_id)
        if not job or job["user"] != uid:
            return None
        return job["status"]

    def result(self, job_id: str, uid: int) -> dict | None:
        job = self._jobs.get(job_id)
        if not job or job["user"] != uid:
            return None
        return job["result"]


sonic = SonicService()


@router.post("/start")
async def sonic_start(user=Depends(current_user)):
    """
    Запускает фоновый ультразвуковой замер.
    Возвращает job_id для последующего опроса.
    """
    job_id = await sonic.start(user["user_id"])
    return {"job_id": job_id}


@router.get("/status")
async def sonic_status(
    job_id: str = Query(..., description="ID задачи замера"),
    user=Depends(current_user),
):
    """
    Возвращает статус замера: pending → running → done
    """
    st = sonic.status(job_id, user["user_id"])
    if st is None:
        raise HTTPException(404, "Job not found")
    return {"status": st}


@router.get("/result")
async def sonic_result(
    job_id: str = Query(..., description="ID задачи замера"),
    user=Depends(current_user),
):
    """
    После статуса = done возвращает результат { distance_cm, timestamp }.
    """
    res = sonic.result(job_id, user["user_id"])
    if res is None:
        raise HTTPException(404, "Result not ready or not found")
    return res


# ----------------------------------
# 2) P2P-перевод “по ультразвуку”
# ----------------------------------
class TransferRequest(BaseModel):
    to_user_id: int


@router.post("/transfer")
async def sonic_transfer(
    req: TransferRequest,
    user=Depends(current_user),
):
    """
    Имитирует замер (3 сек) и списывает из available=distance_cm ₽,
    переводит их пользователю to_user_id и сохраняет в таблицу transfers.
    """
    from_id = user["user_id"]
    to_id = req.to_user_id

    # 1) имитируем сам ультразвуковой замер
    await asyncio.sleep(3)
    distance_cm = 42.0  # 1 см = 1 ₽

    pool = get_pool()
    async with pool.acquire() as conn:
        # 2) списываем у отправителя
        row = await conn.fetchrow(
            """
            UPDATE wallets
               SET available = available - $1
             WHERE user_id = $2
             RETURNING available
            """,
            distance_cm,
            from_id,
        )
        if row is None:
            raise HTTPException(400, "Sender wallet not found")
        new_available = float(row["available"])

        # 3) зачисляем получателю
        await conn.execute(
            """
            UPDATE wallets
               SET available = available + $1
             WHERE user_id = $2
            """,
            distance_cm,
            to_id,
        )

        # 4) записываем историю переводов
        await conn.execute(
            """
            INSERT INTO transfers (from_user, to_user, amount, created_at)
            VALUES ($1, $2, $3, now())
            """,
            from_id,
            to_id,
            distance_cm,
        )

    return {
        "distance_cm": distance_cm,
        "transferred": distance_cm,
        "new_available": new_available,
    }
