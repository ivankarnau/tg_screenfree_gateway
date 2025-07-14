# wallet.py
from fastapi import APIRouter, Depends, HTTPException
from deps import current_user

router = APIRouter(prefix="/wallet", tags=["wallet"])

# Временное in-memory хранилище балансов — позже замените на БД
_balances: dict[int, float] = {}

@router.get("/balance")
async def get_balance(user=Depends(current_user)):
    uid = user["user_id"]
    bal = _balances.get(uid, 0)
    return {"balance": bal}

@router.post("/topup")
async def topup(user=Depends(current_user), payload: dict = {}):
    uid = user["user_id"]
    amount = payload.get("amount")
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise HTTPException(400, "Введите положительную сумму")
    new_bal = _balances.get(uid, 0) + amount
    _balances[uid] = new_bal
    return {"balance": new_bal}
