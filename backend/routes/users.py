from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from database import get_db
from auth_utils import get_current_user_id

router = APIRouter()


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


@router.get("/me")
def get_me(request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        user = db.execute(
            "SELECT id, name, phone, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return dict(user)
    finally:
        db.close()


@router.patch("/me")
def update_me(body: UpdateProfileRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        fields = []
        values = []
        if body.name is not None:
            if not body.name.strip():
                raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")
            fields.append("name = ?")
            values.append(body.name.strip())
        if body.email is not None:
            fields.append("email = ?")
            values.append(body.email or None)

        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(user_id)
        db.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()

        user = db.execute(
            "SELECT id, name, phone, email, created_at FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return dict(user)
    finally:
        db.close()
