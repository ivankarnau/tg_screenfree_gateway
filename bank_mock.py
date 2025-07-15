from fastapi import APIRouter
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/bank", tags=["bank"])

class IssuanceResponse(BaseModel):
    token: str

@router.post("/issuance", response_model=IssuanceResponse)
async def issuance():
    async with httpx.AsyncClient() as client:
        r = await client.post("http://bank_mock:8080/issuance")
        r.raise_for_status()
        return r.json()
