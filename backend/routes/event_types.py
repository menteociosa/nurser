import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from auth_utils import get_current_user_id, new_id
from routes.teams import require_team_member, require_team_admin

router = APIRouter()


class CreateEventTypeRequest(BaseModel):
    name: str
    field_type: str
    options: Optional[str] = None  # JSON string for dropdown/multi_select options
    icon: Optional[str] = None
    color: Optional[str] = None
    is_header: Optional[int] = 0
    sort_order: Optional[int] = 0


class UpdateEventTypeRequest(BaseModel):
    name: Optional[str] = None
    field_type: Optional[str] = None
    options: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_header: Optional[int] = None
    sort_order: Optional[int] = None
    is_active: Optional[int] = None


VALID_FIELD_TYPES = {"boolean", "dropdown", "numeric", "multi_select", "text", "timestamp_event"}


@router.get("/teams/{team_id}/event-types")
def list_event_types(team_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_member(db, team_id, user_id)
        rows = db.execute(
            "SELECT * FROM event_types WHERE team_id = ? ORDER BY sort_order, created_at",
            (team_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("/teams/{team_id}/event-types")
def create_event_type(team_id: str, body: CreateEventTypeRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        if body.field_type not in VALID_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid field_type. Must be one of: {VALID_FIELD_TYPES}")

        et_id = new_id()
        db.execute(
            """INSERT INTO event_types (id, team_id, name, field_type, options, icon, color, is_header, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (et_id, team_id, body.name, body.field_type, body.options, body.icon, body.color, body.is_header or 0, body.sort_order or 0),
        )
        db.commit()

        row = db.execute("SELECT * FROM event_types WHERE id = ?", (et_id,)).fetchone()
        return dict(row)
    finally:
        db.close()


@router.patch("/teams/{team_id}/event-types/{type_id}")
def update_event_type(team_id: str, type_id: str, body: UpdateEventTypeRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)

        existing = db.execute(
            "SELECT * FROM event_types WHERE id = ? AND team_id = ?", (type_id, team_id)
        ).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Event type not found")

        if body.field_type and body.field_type not in VALID_FIELD_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid field_type. Must be one of: {VALID_FIELD_TYPES}")

        fields, values = [], []
        for col in ["name", "field_type", "options", "icon", "color", "is_header", "sort_order", "is_active"]:
            val = getattr(body, col)
            if val is not None:
                fields.append(f"{col} = ?")
                values.append(val)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(type_id)
        db.execute(f"UPDATE event_types SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()

        row = db.execute("SELECT * FROM event_types WHERE id = ?", (type_id,)).fetchone()
        return dict(row)
    finally:
        db.close()


@router.delete("/teams/{team_id}/event-types/{type_id}")
def delete_event_type(team_id: str, type_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        result = db.execute(
            "DELETE FROM event_types WHERE id = ? AND team_id = ?", (type_id, team_id)
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Event type not found")
        db.commit()
        return {"message": "Event type deleted"}
    finally:
        db.close()
