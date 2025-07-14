# gateway/bank_mock.py
import uuid
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/bank", tags=["bank"])

class IssuanceRequest(BaseModel):
    amount: float

class IssuanceResponse(BaseModel):
    token: str
    amount: float
    created_at: datetime

@router.post("/issuance", response_model=IssuanceResponse)
async def issuance(req: IssuanceRequest):
    """
    Эндпоинт mock-банка: выдаёт токен на конкретную сумму.
    Токен — это «ваучер», замораживающий эту сумму в кошельке.
    """
    fake_token = str(uuid.uuid4())
    return IssuanceResponse(
        token=fake_token,
        amount=req.amount,
        created_at=datetime.utcnow(),
    )
