# gateway/wallet.py
from fastapi import APIRouter, Depends, HTTPException
from deps import current_user

router = APIRouter(prefix="/wallet", tags=["wallet"])

# Временное хранилище (замените на БД!)
_balances: dict[int, float] = {}

@router.get("/balance")
async def get_balance(user=Depends(current_user)):
    bal = _balances.get(user["user_id"], 0)
    return {"user_id": user["user_id"], "balance": bal}

@router.post("/topup")
async def topup(user=Depends(current_user), payload: dict = {}):
    amount = payload.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise HTTPException(400, "Введите положительную сумму")
    new_bal = _balances.get(user["user_id"], 0) + amount
    _balances[user["user_id"]] = new_bal
    return {"balance": new_bal}
