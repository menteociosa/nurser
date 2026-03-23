from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from database import get_db
from auth_utils import get_current_user_id, new_id
from routes.teams import require_team_member

router = APIRouter()


class CreateEventRequest(BaseModel):
    team_id: str
    event_type_id: str
    event_value: Optional[str] = None
    timestamp: str
    note: Optional[str] = None


class UpdateEventRequest(BaseModel):
    event_value: Optional[str] = None
    timestamp: Optional[str] = None
    note: Optional[str] = None


@router.post("")
def create_event(body: CreateEventRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_member(db, body.team_id, user_id)

        # Verify event type belongs to this team
        et = db.execute(
            "SELECT id FROM event_types WHERE id = ? AND team_id = ?",
            (body.event_type_id, body.team_id),
        ).fetchone()
        if not et:
            raise HTTPException(status_code=400, detail="Event type not found in this team")

        event_id = new_id()
        db.execute(
            """INSERT INTO events (id, team_id, caregiver_id, event_type_id, event_value, timestamp, note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event_id, body.team_id, user_id, body.event_type_id, body.event_value, body.timestamp, body.note),
        )
        db.commit()

        row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row)
    finally:
        db.close()


@router.get("")
def list_events(
    request: Request,
    team_id: str = Query(...),
    caregiver_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_member(db, team_id, user_id)

        if caregiver_id:
            rows = db.execute(
                """SELECT e.*, u.name AS caregiver_name, et.name AS event_type_name, et.icon, et.color
                   FROM events e
                   JOIN users u ON e.caregiver_id = u.id
                   JOIN event_types et ON e.event_type_id = et.id
                   WHERE e.team_id = ? AND e.caregiver_id = ?
                   ORDER BY e.timestamp DESC
                   LIMIT ? OFFSET ?""",
                (team_id, caregiver_id, limit, offset),
            ).fetchall()
        else:
            rows = db.execute(
                """SELECT e.*, u.name AS caregiver_name, et.name AS event_type_name, et.icon, et.color
                   FROM events e
                   JOIN users u ON e.caregiver_id = u.id
                   JOIN event_types et ON e.event_type_id = et.id
                   WHERE e.team_id = ?
                   ORDER BY e.timestamp DESC
                   LIMIT ? OFFSET ?""",
                (team_id, limit, offset),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.get("/{event_id}")
def get_event(event_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        row = db.execute(
            """SELECT e.*, u.name AS caregiver_name, et.name AS event_type_name
               FROM events e
               JOIN users u ON e.caregiver_id = u.id
               JOIN event_types et ON e.event_type_id = et.id
               WHERE e.id = ?""",
            (event_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        require_team_member(db, row["team_id"], user_id)
        return dict(row)
    finally:
        db.close()


@router.patch("/{event_id}")
def update_event(event_id: str, body: UpdateEventRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Event not found")

        require_team_member(db, existing["team_id"], user_id)

        fields, values = [], []
        if body.event_value is not None:
            fields.append("event_value = ?")
            values.append(body.event_value)
        if body.timestamp is not None:
            fields.append("timestamp = ?")
            values.append(body.timestamp)
        if body.note is not None:
            fields.append("note = ?")
            values.append(body.note)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")

        values.append(event_id)
        db.execute(f"UPDATE events SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()

        row = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row)
    finally:
        db.close()


@router.delete("/{event_id}")
def delete_event(event_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        existing = db.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Event not found")
        require_team_member(db, existing["team_id"], user_id)

        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        db.commit()
        return {"message": "Event deleted"}
    finally:
        db.close()
