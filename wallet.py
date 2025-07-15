from fastapi import APIRouter, Depends, HTTPException
from deps import current_user
from db import get_pool
import uuid

router = APIRouter(prefix="/wallet", tags=["wallet"])

@router.get("/balance")
async def get_balance(user=Depends(current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id=$1",
            user["user_id"]
        )
    return {"available": float(rec["available"]), "reserved": float(rec["reserved"])}

@router.post("/topup")
async def topup(user=Depends(current_user), payload: dict = {}):
    amount = payload.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise HTTPException(400, "Введите положительную сумму")
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE wallets SET available = available + $1 WHERE user_id=$2",
            amount, user["user_id"]
        )
    return await get_balance(user)
