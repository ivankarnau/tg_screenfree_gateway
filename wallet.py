# wallet.py
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

class IssueTokenIn(BaseModel):
    amount: float

@router.get("/balance", response_model=BalanceOut)
async def balance(user=Depends(current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id=$1",
            user["user_id"]
        )
    return BalanceOut(**rec)

@router.post("/topup", response_model=BalanceOut)
async def topup(payload: TopUpIn, user=Depends(current_user)):
    if payload.amount <= 0:
        raise HTTPException(400, "Сумма должна быть > 0")
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE wallets SET available=available+$1 WHERE user_id=$2",
            payload.amount, user["user_id"]
        )
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id=$1",
            user["user_id"]
        )
    return BalanceOut(**rec)

@router.post("/issue-token")
async def issue_token(payload: IssueTokenIn, user=Depends(current_user)):
    amt = payload.amount
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id=$1",
            user["user_id"]
        )
        if amt <= 0 or amt > float(rec["available"]):
            raise HTTPException(400, "Недостаточно средств для резерва")
        tok = str(uuid4())
        await conn.execute(
            "UPDATE wallets SET available=available-$1, reserved=reserved+$1 WHERE user_id=$2",
            amt, user["user_id"]
        )
        await conn.execute(
            "INSERT INTO tokens(token_id,user_id,amount) VALUES($1,$2,$3)",
            tok, user["user_id"], amt
        )
    return {"token_id": tok, "amount": amt}

@router.get("/list-tokens")
async def list_tokens(user=Depends(current_user)):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT token_id, amount, created_at FROM tokens "
            "WHERE user_id=$1 AND redeemed_at IS NULL "
            "ORDER BY created_at DESC",
            user["user_id"]
        )
    return [
        {"token_id": r["token_id"], "amount": float(r["amount"]), "created_at": r["created_at"]}
        for r in rows
    ]
