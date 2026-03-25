import os

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from starlette.requests import Request
from typing import Optional
from authlib.integrations.starlette_client import OAuth

from database import get_db
from auth_utils import (
    create_jwt, generate_otp, otp_expiry, is_otp_expired,
    send_otp, new_id, JWT_EXPIRY_HOURS, get_current_user_id,
)

router = APIRouter()

_oauth = OAuth()
_oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


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


@router.get("/google")
async def google_login(request: Request, link: bool = False):
    """Redirect browser to Google consent screen."""
    redirect_uri = os.getenv("GOOGLE_OAUTH_CALLBACK_URL")
    if link:
        try:
            request.session["link_user_id"] = get_current_user_id(request)
        except HTTPException:
            pass
    return await _oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback — find or create user, link account, or redirect."""
    token = await _oauth.google.authorize_access_token(request)
    info = token["userinfo"]
    google_id = info["sub"]
    email = info.get("email", "")
    name = info.get("name") or email

    link_user_id = request.session.pop("link_user_id", None)
    db = get_db()
    try:
        if link_user_id:
            existing = db.execute(
                "SELECT id FROM users WHERE google_id = ?", (google_id,)
            ).fetchone()
            if existing and existing["id"] != link_user_id:
                return RedirectResponse(url="/profile.html?error=google_already_linked", status_code=302)
            db.execute(
                "UPDATE users SET google_id = ?, email = COALESCE(NULLIF(email, ''), ?) WHERE id = ?",
                (google_id, email, link_user_id),
            )
            db.commit()
            return RedirectResponse(url="/profile.html?linked=google", status_code=302)

        # Normal login flow
        user = db.execute(
            "SELECT id FROM users WHERE google_id = ?", (google_id,)
        ).fetchone()

        if not user and email:
            # Link Google to an existing account matched by email
            user = db.execute(
                "SELECT id FROM users WHERE email = ?", (email,)
            ).fetchone()
            if user:
                db.execute(
                    "UPDATE users SET google_id = ? WHERE id = ?",
                    (google_id, user["id"]),
                )
                db.commit()

        if not user:
            # Brand-new user — phone placeholder (column is NOT NULL UNIQUE)
            user_id = new_id()
            db.execute(
                "INSERT INTO users (id, name, phone, email, password_hash, phone_verified, google_id) "
                "VALUES (?, ?, ?, ?, '', 1, ?)",
                (user_id, name, f"google_{google_id}", email, google_id),
            )
            db.commit()
            user = {"id": user_id}

        jwt_token = create_jwt(user["id"])
        redirect = RedirectResponse(url="/contributor.html", status_code=302)
        redirect.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            samesite="lax",
            max_age=JWT_EXPIRY_HOURS * 3600,
        )
        return redirect
    finally:
        db.close()


class LinkPhoneRequest(BaseModel):
    phone: str


class LinkPhoneVerifyRequest(BaseModel):
    phone: str
    otp: str


@router.post("/link-phone/send")
def link_phone_send(body: LinkPhoneRequest, request: Request):
    """Send OTP to a phone number to link it to the currently logged-in account."""
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM users WHERE phone = ?", (body.phone,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Este número ya está en uso")
        otp = generate_otp()
        expires = otp_expiry()
        db.execute(
            "UPDATE users SET otp_code = ?, otp_expires_at = ? WHERE id = ?",
            (otp, expires, user_id),
        )
        db.commit()
        send_otp(body.phone, otp)
        return {"message": "Código enviado"}
    finally:
        db.close()


@router.post("/link-phone/verify")
def link_phone_verify(body: LinkPhoneVerifyRequest, request: Request):
    """Verify OTP and link the phone number to the currently logged-in account."""
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM users WHERE phone = ? AND id != ?", (body.phone, user_id)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Este número ya está en uso")
        user = db.execute(
            "SELECT otp_code, otp_expires_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user or not user["otp_code"]:
            raise HTTPException(status_code=400, detail="No hay código pendiente. Solicita uno nuevo.")
        if is_otp_expired(user["otp_expires_at"]):
            raise HTTPException(status_code=400, detail="Código expirado. Solicita uno nuevo.")
        if body.otp != user["otp_code"]:
            raise HTTPException(status_code=400, detail="Código incorrecto")
        db.execute(
            "UPDATE users SET phone = ?, phone_verified = 1, otp_code = NULL, otp_expires_at = NULL WHERE id = ?",
            (body.phone, user_id),
        )
        db.commit()
        return {"message": "Teléfono vinculado correctamente"}
    finally:
        db.close()
