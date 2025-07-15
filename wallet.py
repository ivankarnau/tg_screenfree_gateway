# gateway/wallet.py

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


class TokenInfo(BaseModel):
    token_id: str
    amount: float
    created_at: datetime
    redeemed_at: datetime | None = None


@router.get("/balance", response_model=BalanceOut)
async def get_balance(user=Depends(current_user)):
    """
    Возвращает два баланса:
      - available — доступные средства
      - reserved  — замороженные в токенах
    """
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
    """
    Увеличивает available на указанную положительную сумму.
    """
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


@router.post("/issue-token", response_model=TokenInfo)
async def issue_token(payload: IssueTokenIn, user=Depends(current_user)):
    """
    Резервирует сумму из available → reserved и выдаёт token_id.
    """
    amt = payload.amount
    pool = get_pool()
    async with pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT available, reserved FROM wallets WHERE user_id = $1",
            user["user_id"]
        )
        if rec is None:
            raise HTTPException(404, "Кошелёк не найден")
        if amt <= 0 or amt > float(rec["available"]):
            raise HTTPException(400, "Недостаточно доступных средств")
        token_id = str(uuid4())
        # Обновляем балансы
        await conn.execute(
            "UPDATE wallets SET available = available - $1, reserved = reserved + $1 WHERE user_id = $2",
            amt, user["user_id"]
        )
        # Сохраняем токен
        await conn.execute(
            "INSERT INTO tokens (token_id, user_id, amount) VALUES ($1, $2, $3)",
            token_id, user["user_id"], amt
        )
    return TokenInfo(
        token_id=token_id,
        amount=amt,
        created_at=datetime.utcnow(),
        redeemed_at=None
    )


@router.get("/list-tokens", response_model=list[TokenInfo])
async def list_tokens(user=Depends(current_user)):
    """
    Список всех активных (не выкупленных) токенов пользователя.
    """
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT token_id, amount, created_at, redeemed_at
              FROM tokens
             WHERE user_id = $1
               AND redeemed_at IS NULL
             ORDER BY created_at DESC
            """,
            user["user_id"]
        )
    return [
        TokenInfo(
            token_id=str(r["token_id"]),
            amount=float(r["amount"]),
            created_at=r["created_at"],
            redeemed_at=r["redeemed_at"],
        )
        for r in rows
    ]
