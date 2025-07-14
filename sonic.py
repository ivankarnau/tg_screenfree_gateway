# sonic.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from deps import current_user
from pydantic import BaseModel
import asyncio, time
from typing import Dict

router = APIRouter(prefix="/sonic", tags=["sonic"])

# Существующий сервис для фоновых замеров
class SonicService:
    def __init__(self):
        self._jobs: Dict[str, Dict] = {}

    async def start(self, uid: int) -> str:
        job_id = str(time.time_ns())
        self._jobs[job_id] = {"user": uid, "status": "pending", "result": None}
        asyncio.create_task(self._run(job_id))
        return job_id

    async def _run(self, job_id: str):
        self._jobs[job_id]["status"] = "running"
        await asyncio.sleep(3)  # здесь будет реальный замер
        # имитируем результат 42 см
        self._jobs[job_id]["result"] = {"distance_cm": 42, "ts": time.time()}
        self._jobs[job_id]["status"] = "done"

    def status(self, job_id: str, uid: int):
        job = self._jobs.get(job_id)
        if not job or job["user"] != uid:
            return None
        return job["status"]

    def result(self, job_id: str, uid: int):
        job = self._jobs.get(job_id)
        if not job or job["user"] != uid:
            return None
        return job["result"]

sonic = SonicService()

# 1) Фоновые роуты, как было
@router.post("/start")
async def sonic_start(user=Depends(current_user)):
    return {"job_id": await sonic.start(user["user_id"])}

@router.get("/status")
async def sonic_status(
    job_id: str = Query(...), user=Depends(current_user)
):
    st = sonic.status(job_id, user["user_id"])
    if st is None:
        raise HTTPException(404, "Job not found")
    return {"status": st}

@router.get("/result")
async def sonic_result(
    job_id: str = Query(...), user=Depends(current_user)
):
    res = sonic.result(job_id, user["user_id"])
    if res is None:
        raise HTTPException(404, "Result not ready")
    return res

# 2) Новый роут для P2P-перевода «по ультразвуку»
class TransferRequest(BaseModel):
    to_user_id: int

@router.post("/transfer")
async def sonic_transfer(
    req: TransferRequest,
    request: Request,
    user=Depends(current_user)
):
    pool    = request.app.state.db
    from_id = user["user_id"]
    to_id   = req.to_user_id

    # 2.1) Имитация замера
    # (в реале здесь будет вызов вашего драйвера)
    await asyncio.sleep(2)
    distance_cm = 42.0  # пусть 1 см = 1 ₽

    async with pool.acquire() as conn:
        async with conn.transaction():
            # убедимся, что у обоих есть кошелёк
            await conn.execute(
                "INSERT INTO wallets(user_id,balance) VALUES($1,0) ON CONFLICT DO NOTHING",
                from_id
            )
            await conn.execute(
                "INSERT INTO wallets(user_id,balance) VALUES($1,0) ON CONFLICT DO NOTHING",
                to_id
            )
            # списываем у отправителя
            row = await conn.fetchrow(
                "UPDATE wallets SET balance = balance - $1 WHERE user_id = $2 RETURNING balance",
                distance_cm, from_id
            )
            if row is None:
                raise HTTPException(400, "Отправитель не найден")
            new_balance = float(row["balance"])

            # зачисляем получателю
            await conn.execute(
                "UPDATE wallets SET balance = balance + $1 WHERE user_id = $2",
                distance_cm, to_id
            )
            # сохраняем в историю переводов
            await conn.execute(
                "INSERT INTO transfers(from_user,to_user,amount) VALUES($1,$2,$3)",
                from_id, to_id, distance_cm
            )

    return {
        "distance_cm": distance_cm,
        "transferred": distance_cm,
        "new_balance": new_balance
    }
