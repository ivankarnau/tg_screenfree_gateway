# gateway/sonic.py
from fastapi import APIRouter, Depends, HTTPException, Query
from deps import current_user
import asyncio, time
from typing import Dict

router = APIRouter(prefix="/sonic", tags=["sonic"])

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
        await asyncio.sleep(3)  # TODO: ваша логика работы с датчиком
        self._jobs[job_id]["result"] = {"distance_cm": 42, "ts": time.time()}
        self._jobs[job_id]["status"] = "done"

    def status(self, job_id: str, uid: int):
        job = self._jobs.get(job_id)
        if not job or job["user"] != uid: return None
        return job["status"]

    def result(self, job_id: str, uid: int):
        job = self._jobs.get(job_id)
        if not job or job["user"] != uid: return None
        return job["result"]

sonic = SonicService()

@router.post("/start")
async def sonic_start(user=Depends(current_user)):
    return {"job_id": await sonic.start(user["user_id"])}

@router.get("/status")
async def sonic_status(job_id: str = Query(...), user=Depends(current_user)):
    st = sonic.status(job_id, user["user_id"])
    if st is None:
        raise HTTPException(404, "Job not found")
    return {"status": st}

@router.get("/result")
async def sonic_result(job_id: str = Query(...), user=Depends(current_user)):
    res = sonic.result(job_id, user["user_id"])
    if res is None:
        raise HTTPException(404, "Result not ready")
    return res
