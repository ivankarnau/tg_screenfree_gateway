import os, time, json, urllib.parse as up
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt
from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError, UnexpectedFormatError
)

BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")
if not BOT_TOKEN or not JWT_SECRET:
    raise RuntimeError("BOT_TOKEN и JWT_SECRET должны быть заданы")

router = APIRouter(prefix="/auth", tags=["auth"])
ALGO = "HS256"

class TGIn(BaseModel):
    initData: str

def verify(raw_qs: str) -> dict:
    try:
        InitData.parse(raw_qs).validate(BOT_TOKEN, lifetime=24*3600)
    except (SignInvalidError, SignMissingError,
            AuthDateMissingError, ExpiredError,
            UnexpectedFormatError) as e:
        raise HTTPException(401, f"bad signature: {e}")
    user_qs = up.parse_qs(raw_qs)["user"][0]
    user_json = up.unquote_plus(user_qs)
    return json.loads(user_json)

@router.post("/telegram")
async def auth(body: TGIn):
    u = verify(body.initData)
    token = jwt.encode(
        {"sub": u["id"], "first": u.get("first_name",""), "iat": int(time.time())},
        JWT_SECRET, algorithm=ALGO
    )
    return {"access_token": token}
