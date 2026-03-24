from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from typing import Optional

from database import get_db
from auth_utils import (
    create_jwt, generate_otp, otp_expiry, is_otp_expired,
    send_otp, new_id, JWT_EXPIRY_HOURS,
)

router = APIRouter()


class RegisterRequest(BaseModel):
    name: str
    phone: str
    invite_code: Optional[str] = None


class VerifyOtpRequest(BaseModel):
    phone: str
    otp: str
    invite_code: Optional[str] = None


class LoginRequest(BaseModel):
    phone: str


class ResendOtpRequest(BaseModel):
    phone: str


@router.post("/register")
def register(body: RegisterRequest):
    """Create a new user and send OTP. Phone must not already exist."""
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM users WHERE phone = ?", (body.phone,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Este número ya está registrado. Usa la pestaña Iniciar sesión."
            )

        user_id = new_id()
        otp = generate_otp()
        expires = otp_expiry()

        db.execute(
            "INSERT INTO users (id, name, phone, password_hash, otp_code, otp_expires_at) "
            "VALUES (?, ?, ?, '', ?, ?)",
            (user_id, body.name, body.phone, otp, expires),
        )
        db.commit()
        send_otp(body.phone, otp)
        return {"message": "Código enviado."}
    finally:
        db.close()


@router.post("/login")
def login(body: LoginRequest):
    """Send OTP to a registered phone number (passwordless login)."""
    db = get_db()
    try:
        user = db.execute(
            "SELECT id FROM users WHERE phone = ?", (body.phone,)
        ).fetchone()
        if not user:
            raise HTTPException(
                status_code=404,
                detail="Número no registrado. ¿Es la primera vez? Regístrate."
            )

        otp = generate_otp()
        expires = otp_expiry()
        db.execute(
            "UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE id = ?",
            (otp, expires, user["id"]),
        )
        db.commit()
        send_otp(body.phone, otp)
        return {"message": "Código enviado."}
    finally:
        db.close()


@router.post("/verify-otp")
def verify_otp(body: VerifyOtpRequest, response: Response):
    """Verify OTP — works for both new registration and returning login."""
    db = get_db()
    try:
        user = db.execute(
            "SELECT id, otp_code, otp_expires_at FROM users WHERE phone = ?",
            (body.phone,),
        ).fetchone()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        if not user["otp_code"] or not user["otp_expires_at"]:
            raise HTTPException(status_code=400, detail="No hay código pendiente. Solicita uno nuevo.")
        if is_otp_expired(user["otp_expires_at"]):
            raise HTTPException(status_code=400, detail="Código expirado. Solicita uno nuevo.")
        if body.otp != user["otp_code"]:
            raise HTTPException(status_code=400, detail="Código incorrecto")

        db.execute(
            "UPDATE users SET phone_verified = 1, otp_code = NULL, otp_expires_at = NULL WHERE id = ?",
            (user["id"],),
        )

        # Auto-join team if invite_code was provided
        if body.invite_code:
            invite = db.execute(
                "SELECT * FROM invite_codes WHERE code = ?", (body.invite_code,)
            ).fetchone()
            if invite and (not invite["max_uses"] or invite["use_count"] < invite["max_uses"]):
                existing_membership = db.execute(
                    "SELECT id FROM team_memberships WHERE team_id = ? AND user_id = ?",
                    (invite["team_id"], user["id"]),
                ).fetchone()
                if not existing_membership:
                    db.execute(
                        "INSERT INTO team_memberships (id, team_id, user_id, role) VALUES (?, ?, ?, ?)",
                        (new_id(), invite["team_id"], user["id"], invite["role"]),
                    )
                    db.execute(
                        "UPDATE invite_codes SET use_count = use_count + 1 WHERE id = ?",
                        (invite["id"],),
                    )

        db.commit()

        token = create_jwt(user["id"])
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="lax",
            max_age=JWT_EXPIRY_HOURS * 3600,
        )
        return {"message": "Verificado"}
    finally:
        db.close()


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out"}


@router.post("/resend-otp")
def resend_otp(body: ResendOtpRequest):
    db = get_db()
    try:
        user = db.execute(
            "SELECT id FROM users WHERE phone = ?", (body.phone,)
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        otp = generate_otp()
        expires = otp_expiry()
        db.execute(
            "UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE id = ?",
            (otp, expires, user["id"]),
        )
        db.commit()
        send_otp(body.phone, otp)
        return {"message": "Código reenviado"}
    finally:
        db.close()
