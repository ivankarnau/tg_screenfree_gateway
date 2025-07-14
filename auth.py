# auth.py
import os
import time
import json
import urllib.parse as up

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError,
    UnexpectedFormatError,
)

BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN и JWT_SECRET должны быть заданы")

ALGO = "HS256"
router = APIRouter(prefix="/auth", tags=["auth"])

class AuthTelegramRequest(BaseModel):
    initData: str

class AuthTelegramResponse(BaseModel):
    access_token: str

def verify_init_data(raw_qs: str) -> dict:
    try:
        InitData.parse(raw_qs).validate(BOT_TOKEN, lifetime=24*3600)
    except (
        SignInvalidError, SignMissingError,
        AuthDateMissingError, ExpiredError,
        UnexpectedFormatError
    ) as e:
        raise HTTPException(401, f"bad signature: {e}")
    user_qs = up.parse_qs(raw_qs)["user"][0]
    user_json = up.unquote_plus(user_qs)
    return json.loads(user_json)

@router.post("/telegram", response_model=AuthTelegramResponse)
async def auth_telegram(data: AuthTelegramRequest):
    user = verify_init_data(data.initData)
    token = jwt.encode(
        {"sub": str(user["id"]), "first": user.get("first_name", ""), "iat": int(time.time())},
        JWT_SECRET,
        algorithm=ALGO,
    )
    return {"access_token": token}
