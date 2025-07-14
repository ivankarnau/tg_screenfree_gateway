from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jose import jwt
from init_data_py import InitData
from init_data_py.errors import (
    SignInvalidError, SignMissingError,
    AuthDateMissingError, ExpiredError,
    UnexpectedFormatError,
)
import urllib.parse as up, json, os, time

# ⚙️  берём токены из переменных окружения
BOT_TOKEN  = os.getenv("BOT_TOKEN")
JWT_SECRET = os.getenv("JWT_SECRET")

if not BOT_TOKEN or not JWT_SECRET:
    sys.exit("❌  BOT_TOKEN и/или JWT_SECRET не заданы в переменных окружения")

ALGO = "HS256"

app = FastAPI()

class TGIn(BaseModel):
    initData: str

def verify(raw_qs: str) -> dict:
    """Проверяем подпись initData и вытаскиваем user{}"""
    try:
        InitData.parse(raw_qs).validate(BOT_TOKEN, lifetime=24*3600)
    except (SignInvalidError, SignMissingError,
            AuthDateMissingError, ExpiredError,
            UnexpectedFormatError) as e:
        raise HTTPException(401, f"bad signature: {e}")

    # user в query-string закодирован как JSON
    user_json = up.unquote_plus(up.parse_qs(raw_qs)["user"][0])
    return json.loads(user_json)

@app.post("/auth/telegram")
async def auth(body: TGIn):
    u = verify(body.initData)           # ✅ подпись прошла
    token = jwt.encode(
        {"sub": u["id"],
         "first": u.get("first_name", ""),
         "iat": int(time.time())},
        JWT_SECRET,
        algorithm=ALGO,
    )
    return {"access_token": token}

