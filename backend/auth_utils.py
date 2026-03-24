import os
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
import platform
import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import Cookie, HTTPException, Request

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "87600"))  # 10 years default
BULKSMS_USERNAME = os.getenv("BULKSMS_USERNAME", "placeholder")
BULKSMS_PASSWORD = os.getenv("BULKSMS_PASSWORD", "placeholder")

OTP_EXPIRY_MINUTES = 10


# --------------- Password hashing ---------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --------------- JWT ---------------

def create_jwt(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")




def get_current_user_id(request: Request) -> str:
    ### start block for autologin in development on Windows (ignores JWT and cookies)
    dev_phone = os.getenv("DEV_AUTOLOGIN_PHONE", "").strip()
    if dev_phone and platform.system() == "Windows":
        from database import get_db
        db = get_db()
        try:
            row = db.execute("SELECT id FROM users WHERE phone = ?", (dev_phone,)).fetchone()
        finally:
            db.close()
        if not row:
            raise HTTPException(status_code=401, detail=f"DEV_AUTOLOGIN_PHONE '{dev_phone}' not found in DB")
        return row["id"]
    ### end block for autologin in development on Windows
    
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_jwt(token)
    return payload["sub"]


# --------------- OTP ---------------

def generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def otp_expiry() -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()


def is_otp_expired(expires_at: str) -> bool:
    exp = datetime.fromisoformat(expires_at)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) > exp


def send_otp(phone: str, otp: str):
    """Send OTP via BulkSMS. Falls back to printing to console if using placeholder keys."""
    if BULKSMS_USERNAME == "placeholder":
        print(f"\n{'='*50}")
        print(f"  SMS OTP for {phone}: {otp}")
        print(f"{'='*50}\n")
        return

    import base64
    import requests

    credentials = f"{BULKSMS_USERNAME}:{BULKSMS_PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")

    response = requests.post(
        "https://api.bulksms.com/v1/messages",
        json={
            "to": [phone],
            "body": f"Tu clave de acceso a Nurser es: {otp}",
            "encoding": "UNICODE",
        },
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {encoded_credentials}",
        },
    )
    response.raise_for_status()
    print(f"SMS sent to {phone} — BulkSMS response: {response.status_code}")


# --------------- Helpers ---------------

def new_id() -> str:
    return str(uuid.uuid4())


def generate_invite_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
