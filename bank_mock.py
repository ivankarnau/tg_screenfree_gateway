# gateway/bank_mock.py
import uuid
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/bank", tags=["bank"])

class IssuanceResponse(BaseModel):
    token: str

@router.post("/issuance", response_model=IssuanceResponse)
async def issuance():
    # Генерируем фейковый токен
    fake_token = str(uuid.uuid4())
    return IssuanceResponse(token=fake_token)
