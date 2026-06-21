from fastapi import FastAPI, Request
from datetime import datetime, timedelta
from db.database import set_subscribed
import hashlib
from config import CLICK_SECRET_KEY

app = FastAPI()


@app.post("/click/webhook")
async def click_webhook(request: Request):
    data = await request.json()

    sign_string = (
        f"{data.get('click_trans_id')}{data.get('service_id')}"
        f"{CLICK_SECRET_KEY}{data.get('merchant_trans_id')}"
        f"{data.get('amount')}{data.get('action')}{data.get('sign_time')}"
    )
    sign = hashlib.md5(sign_string.encode()).hexdigest()

    if sign != data.get("sign_string"):
        return {"error": -1, "error_note": "Invalid sign"}

    if data.get("error") == 0:
        telegram_id = int(data.get("merchant_trans_id"))
        until = datetime.now() + timedelta(days=30)
        await set_subscribed(telegram_id, until)

    return {"error": 0, "error_note": "Success"}


@app.get("/health")
async def health():
    return {"status": "ok"}