from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime

from deps import current_user
from db import get_pool

router = APIRouter(prefix="/wallet", tags=["wallet"])

class BalanceOut(BaseModel):
    available: float
    reserved: float

class TopUpIn(BaseModel):
    amount: float

class TokenOut(BaseModel):
    token_id: str
    amount: float
    created_at: datetime
    redeemed_at: datetime | None = None

class ReserveIn(BaseModel):
    amount: float

class ClaimIn(BaseModel):
    token_id: str

@router.get("/balance", response_model=BalanceOut)
async def get_balance(user=Depends(current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id = $1",
            user["user_id"]
        )
    if rec is None:
        raise HTTPException(404, "Кошелёк не найден")
    return BalanceOut(
        available=float(rec["available"]),
        reserved=float(rec["reserved"])
    )

@router.post("/topup", response_model=BalanceOut)
async def topup(payload: TopUpIn, user=Depends(current_user)):
    amt = payload.amount
    if amt <= 0:
        raise HTTPException(400, "Сумма должна быть > 0")
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE wallets SET available = available + $1 WHERE user_id = $2",
            amt, user["user_id"]
        )
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id = $1",
            user["user_id"]
        )
    return BalanceOut(
        available=float(rec["available"]),
        reserved=float(rec["reserved"])
    )

@router.get("/tokens", response_model=list[TokenOut])
async def get_tokens(user=Depends(current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT token_id, amount, created_at, redeemed_at FROM tokens WHERE user_id = $1 ORDER BY created_at DESC",
            user["user_id"]
        )
    return [
        TokenOut(
            token_id=str(r["token_id"]),
            amount=float(r["amount"]),
            created_at=r["created_at"],
            redeemed_at=r["redeemed_at"],
        )
        for r in rows
    ]

@router.post("/reserve", response_model=TokenOut)
async def reserve_token(payload: ReserveIn, user=Depends(current_user)):
    amt = payload.amount
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT available FROM wallets WHERE user_id = $1",
            user["user_id"]
        )
        if not rec or amt <= 0 or amt > float(rec["available"]):
            raise HTTPException(400, "Недостаточно свободных средств")
        token_id = str(uuid4())
        await conn.execute(
            "UPDATE wallets SET available = available - $1, reserved = reserved + $1 WHERE user_id = $2",
            amt, user["user_id"]
        )
        await conn.execute(
            "INSERT INTO tokens (token_id, user_id, amount) VALUES ($1, $2, $3)",
            token_id, user["user_id"], amt
        )
        row = await conn.fetchrow(
            "SELECT token_id, amount, created_at, redeemed_at FROM tokens WHERE token_id = $1",
            token_id
        )
    return TokenOut(
        token_id=str(row["token_id"]),
        amount=float(row["amount"]),
        created_at=row["created_at"],
        redeemed_at=row["redeemed_at"]
    )

@router.post("/claim")
async def claim_token(payload: ClaimIn, user=Depends(current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM tokens WHERE token_id = $1 AND redeemed_at IS NULL",
            payload.token_id
        )
        if not row:
            raise HTTPException(404, "Токен не найден или уже использован")
        await conn.execute(
            "UPDATE wallets SET reserved = reserved - $1 WHERE user_id = $2",
            row["amount"], row["user_id"]
        )
        await conn.execute(
            "UPDATE wallets SET available = available + $1 WHERE user_id = $2",
            row["amount"], user["user_id"]
        )
        await conn.execute(
            "UPDATE tokens SET redeemed_at = now() WHERE token_id = $1",
            payload.token_id
        )
    return {"ok": True}
