# wallet.py
from fastapi import APIRouter, Depends, HTTPException, Request
from deps import current_user

router = APIRouter(prefix="/wallet", tags=["wallet"])

@router.get("/balance")
async def get_balance(request: Request, user=Depends(current_user)):
    pool = request.app.state.db
    uid  = user["user_id"]
    raw  = await pool.fetchval(
        "SELECT balance FROM wallets WHERE user_id = $1",
        uid
    )
    bal = float(raw) if raw is not None else 0.0
    return {"balance": bal}

@router.post("/topup")
async def topup(request: Request, user=Depends(current_user), payload: dict = {}):
    pool   = request.app.state.db
    uid    = user["user_id"]
    amount = payload.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise HTTPException(400, "Введите положительную сумму")

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO wallets(user_id, balance) VALUES($1, 0) ON CONFLICT DO NOTHING",
                uid
            )
            await conn.execute(
                "UPDATE wallets SET balance = balance + $1 WHERE user_id = $2",
                amount, uid
            )
            raw = await conn.fetchval(
                "SELECT balance FROM wallets WHERE user_id = $1",
                uid
            )
    return {"balance": float(raw)}
