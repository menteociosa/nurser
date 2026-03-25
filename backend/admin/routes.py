import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from database import get_db
from auth_utils import get_current_user_id, new_id

router = APIRouter()

ADMIN_USERNAME = os.getenv("admin_username", "").strip()
_PANEL = Path(__file__).parent / "panel.html"


def _require_admin(request: Request) -> str:
    """Returns user_id if the requester is the configured admin, else raises 403."""
    user_id = get_current_user_id(request)
    if not ADMIN_USERNAME:
        raise HTTPException(status_code=403, detail="Admin not configured")
    db = get_db()
    try:
        user = db.execute(
            "SELECT email, phone FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if not user or (
            (user["email"] or "").strip() != ADMIN_USERNAME
            and (user["phone"] or "").strip() != ADMIN_USERNAME
        ):
            raise HTTPException(status_code=403, detail="Admin access required")
        return user_id
    finally:
        db.close()


def _sole_admin_teams_with_others(db, uid: str) -> list:
    """Find teams where uid is sole admin AND other members exist."""
    rows = db.execute(
        """SELECT t.id, t.name,
                  (SELECT COUNT(*) FROM team_memberships WHERE team_id = t.id) AS member_count,
                  (SELECT COUNT(*) FROM team_memberships WHERE team_id = t.id AND role = 'admin') AS admin_count
           FROM teams t
           JOIN team_memberships tm ON t.id = tm.team_id
           WHERE tm.user_id = ? AND tm.role = 'admin'""",
        (uid,),
    ).fetchall()
    return [
        {"team_id": r["id"], "team_name": r["name"], "member_count": r["member_count"]}
        for r in rows
        if r["admin_count"] == 1 and r["member_count"] > 1
    ]


# ── HTML Panel ───────────────────────────────────────────────

@router.get("/", include_in_schema=False)
@router.get("", include_in_schema=False)
def admin_panel():
    return FileResponse(str(_PANEL))


# ── Users ────────────────────────────────────────────────────

@router.get("/api/users")
def list_users(request: Request):
    _require_admin(request)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, name, phone, email, phone_verified, google_id, created_at "
            "FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


class PatchUserBody(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None


@router.patch("/api/users/{uid}")
def patch_user(uid: str, body: PatchUserBody, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        fields, vals = [], []
        if body.name is not None:
            if not body.name.strip():
                raise HTTPException(status_code=422, detail="Name cannot be empty")
            fields.append("name = ?")
            vals.append(body.name.strip())
        if body.phone is not None:
            fields.append("phone = ?")
            vals.append(body.phone.strip())
        if not fields:
            raise HTTPException(status_code=400, detail="Nothing to update")
        vals.append(uid)
        db.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", vals)
        db.commit()
        row = db.execute(
            "SELECT id, name, phone, email, phone_verified, google_id, created_at FROM users WHERE id = ?",
            (uid,),
        ).fetchone()
        return dict(row)
    finally:
        db.close()


@router.get("/api/users/{uid}/delete-check")
def delete_user_check(uid: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        return {"warnings": _sole_admin_teams_with_others(db, uid)}
    finally:
        db.close()


@router.delete("/api/users/{uid}")
def delete_user(uid: str, request: Request, force: bool = False):
    _require_admin(request)
    db = get_db()
    try:
        warn = _sole_admin_teams_with_others(db, uid)
        if warn and not force:
            raise HTTPException(
                status_code=409,
                detail={"message": "Sole admin of teams with other members", "teams": warn},
            )

        # All teams where this user is the sole admin (sole-member teams included)
        sole_admin_ids = [
            r["id"]
            for r in db.execute(
                """SELECT t.id FROM teams t
                   JOIN team_memberships tm ON t.id = tm.team_id
                   WHERE tm.user_id = ? AND tm.role = 'admin'
                   AND (SELECT COUNT(*) FROM team_memberships WHERE team_id = t.id AND role = 'admin') = 1""",
                (uid,),
            ).fetchall()
        ]

        # Delete user's events (caregiver_id has no ON DELETE CASCADE)
        db.execute("DELETE FROM events WHERE caregiver_id = ?", (uid,))
        # Delete user's invite_codes (created_by has no ON DELETE CASCADE)
        db.execute("DELETE FROM invite_codes WHERE created_by = ?", (uid,))
        # Delete sole-admin teams (ON DELETE CASCADE handles memberships/event_types/events)
        for tid in sole_admin_ids:
            db.execute("DELETE FROM teams WHERE id = ?", (tid,))
        # Transfer created_by for remaining teams to another admin in that team
        db.execute(
            """UPDATE teams SET created_by = (
                   SELECT user_id FROM team_memberships
                   WHERE team_id = teams.id AND user_id != ? AND role = 'admin'
                   LIMIT 1
               ) WHERE created_by = ?""",
            (uid, uid),
        )
        # Fallback: any other member if no other admin exists
        db.execute(
            """UPDATE teams SET created_by = (
                   SELECT user_id FROM team_memberships
                   WHERE team_id = teams.id AND user_id != ?
                   LIMIT 1
               ) WHERE created_by = ?""",
            (uid, uid),
        )
        db.execute("DELETE FROM users WHERE id = ?", (uid,))
        db.commit()
        return {"message": "User deleted"}
    finally:
        db.close()


# ── Teams ────────────────────────────────────────────────────

@router.get("/api/teams")
def list_teams(request: Request):
    _require_admin(request)
    db = get_db()
    try:
        rows = db.execute(
            """SELECT t.*,
                      (SELECT COUNT(*) FROM team_memberships WHERE team_id = t.id) AS member_count
               FROM teams t ORDER BY t.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


class PatchTeamBody(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_notices: Optional[str] = None


@router.patch("/api/teams/{tid}")
def patch_team(tid: str, body: PatchTeamBody, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        fields, vals = [], []
        for col, val in [
            ("name", body.name),
            ("description", body.description),
            ("team_notices", body.team_notices),
        ]:
            if val is not None:
                fields.append(f"{col} = ?")
                vals.append(val)
        if not fields:
            raise HTTPException(status_code=400, detail="Nothing to update")
        vals.append(tid)
        db.execute(f"UPDATE teams SET {', '.join(fields)} WHERE id = ?", vals)
        db.commit()
        return dict(db.execute("SELECT * FROM teams WHERE id = ?", (tid,)).fetchone())
    finally:
        db.close()


@router.delete("/api/teams/{tid}")
def delete_team(tid: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        db.execute("DELETE FROM teams WHERE id = ?", (tid,))
        db.commit()
        return {"message": "Team deleted"}
    finally:
        db.close()


# ── Team Members ─────────────────────────────────────────────

@router.get("/api/teams/{tid}/members")
def list_members(tid: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        rows = db.execute(
            """SELECT u.id, u.name, u.phone, u.email, tm.role, tm.joined_at
               FROM team_memberships tm JOIN users u ON tm.user_id = u.id
               WHERE tm.team_id = ? ORDER BY tm.joined_at""",
            (tid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


class AddMemberBody(BaseModel):
    user_id: str
    role: Optional[str] = "contributor"


@router.post("/api/teams/{tid}/members")
def add_member(tid: str, body: AddMemberBody, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        existing = db.execute(
            "SELECT id FROM team_memberships WHERE team_id = ? AND user_id = ?",
            (tid, body.user_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Already a member")
        db.execute(
            "INSERT INTO team_memberships (id, team_id, user_id, role) VALUES (?, ?, ?, ?)",
            (new_id(), tid, body.user_id, body.role or "contributor"),
        )
        db.commit()
        return {"message": "Member added"}
    finally:
        db.close()


class PatchRoleBody(BaseModel):
    role: str


@router.patch("/api/teams/{tid}/members/{uid}")
def patch_member_role(tid: str, uid: str, body: PatchRoleBody, request: Request):
    _require_admin(request)
    if body.role not in ("admin", "contributor", "viewer"):
        raise HTTPException(status_code=422, detail="Invalid role")
    db = get_db()
    try:
        db.execute(
            "UPDATE team_memberships SET role = ? WHERE team_id = ? AND user_id = ?",
            (body.role, tid, uid),
        )
        db.commit()
        return {"message": "Role updated"}
    finally:
        db.close()


@router.delete("/api/teams/{tid}/members/{uid}")
def remove_member(tid: str, uid: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        db.execute(
            "DELETE FROM team_memberships WHERE team_id = ? AND user_id = ?", (tid, uid)
        )
        db.commit()
        return {"message": "Member removed"}
    finally:
        db.close()


# ── Activity Types ───────────────────────────────────────────

@router.get("/api/teams/{tid}/event-types")
def list_event_types(tid: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        rows = db.execute(
            "SELECT * FROM event_types WHERE team_id = ? ORDER BY sort_order, created_at",
            (tid,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


class PatchEventTypeBody(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[int] = None


@router.patch("/api/teams/{tid}/event-types/{et_id}")
def patch_event_type(tid: str, et_id: str, body: PatchEventTypeBody, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        fields, vals = [], []
        for col, val in [("name", body.name), ("icon", body.icon), ("is_active", body.is_active)]:
            if val is not None:
                fields.append(f"{col} = ?")
                vals.append(val)
        if not fields:
            raise HTTPException(status_code=400, detail="Nothing to update")
        vals.append(et_id)
        db.execute(f"UPDATE event_types SET {', '.join(fields)} WHERE id = ?", vals)
        db.commit()
        return dict(db.execute("SELECT * FROM event_types WHERE id = ?", (et_id,)).fetchone())
    finally:
        db.close()


@router.delete("/api/teams/{tid}/event-types/{et_id}")
def delete_event_type(tid: str, et_id: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        db.execute("DELETE FROM event_types WHERE id = ? AND team_id = ?", (et_id, tid))
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()


# ── Registered Activities (Events) ──────────────────────────

@router.get("/api/teams/{tid}/events")
def list_events(tid: str, request: Request, limit: int = 50, offset: int = 0):
    _require_admin(request)
    db = get_db()
    try:
        rows = db.execute(
            """SELECT e.id, e.timestamp, e.event_value, e.note,
                      u.name AS caregiver_name,
                      et.name AS event_type_name, et.icon AS event_type_icon
               FROM events e
               JOIN users u ON e.caregiver_id = u.id
               JOIN event_types et ON e.event_type_id = et.id
               WHERE e.team_id = ?
               ORDER BY e.timestamp DESC LIMIT ? OFFSET ?""",
            (tid, limit, offset),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.delete("/api/events/{event_id}")
def delete_event(event_id: str, request: Request):
    _require_admin(request)
    db = get_db()
    try:
        db.execute("DELETE FROM events WHERE id = ?", (event_id,))
        db.commit()
        return {"message": "Event deleted"}
    finally:
        db.close()
