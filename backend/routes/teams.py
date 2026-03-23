import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from database import get_db
from auth_utils import get_current_user_id, new_id, generate_invite_code

router = APIRouter()


# --------------- Pydantic models ---------------

class CreateTeamRequest(BaseModel):
    name: str
    description: Optional[str] = None


class UpdateTeamRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    team_notices: Optional[str] = None


class UpdateMemberRoleRequest(BaseModel):
    role: str


class InviteRequest(BaseModel):
    role: Optional[str] = "contributor"


class UpdateTeamNoticesRequest(BaseModel):
    team_notices: str


# --------------- Helpers ---------------

def require_team_member(db, team_id: str, user_id: str) -> dict:
    """Return membership row or raise 403."""
    membership = db.execute(
        "SELECT * FROM team_memberships WHERE team_id = ? AND user_id = ?",
        (team_id, user_id),
    ).fetchone()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this team")
    return dict(membership)


def require_team_admin(db, team_id: str, user_id: str):
    m = require_team_member(db, team_id, user_id)
    if m["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")


# --------------- Team CRUD ---------------

@router.get("")
def list_teams(request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        rows = db.execute(
            """SELECT t.*, tm.role AS my_role
               FROM teams t
               JOIN team_memberships tm ON t.id = tm.team_id
               WHERE tm.user_id = ?
               ORDER BY t.created_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.post("")
def create_team(body: CreateTeamRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        team_id = new_id()
        db.execute(
            "INSERT INTO teams (id, name, description, created_by) VALUES (?, ?, ?, ?)",
            (team_id, body.name, body.description, user_id),
        )
        membership_id = new_id()
        db.execute(
            "INSERT INTO team_memberships (id, team_id, user_id, role) VALUES (?, ?, ?, 'admin')",
            (membership_id, team_id, user_id),
        )
        db.commit()
        return {"id": team_id, "name": body.name, "description": body.description}
    finally:
        db.close()


@router.get("/{team_id}")
def get_team(team_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_member(db, team_id, user_id)
        team = db.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        return dict(team)
    finally:
        db.close()


@router.patch("/{team_id}")
def update_team(team_id: str, body: UpdateTeamRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        fields, values = [], []
        if body.name is not None:
            fields.append("name = ?")
            values.append(body.name)
        if body.description is not None:
            fields.append("description = ?")
            values.append(body.description)
        if body.team_notices is not None:
            fields.append("team_notices = ?")
            values.append(body.team_notices)
        if not fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        values.append(team_id)
        db.execute(f"UPDATE teams SET {', '.join(fields)} WHERE id = ?", values)
        db.commit()
        team = db.execute("SELECT * FROM teams WHERE id = ?", (team_id,)).fetchone()
        return dict(team)
    finally:
        db.close()


@router.delete("/{team_id}")
def delete_team(team_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        db.execute("DELETE FROM teams WHERE id = ?", (team_id,))
        db.commit()
        return {"message": "Team deleted"}
    finally:
        db.close()


# --------------- Team Notices (editable by contributors) ---------------

@router.get("/{team_id}/notices")
def get_notices(team_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_member(db, team_id, user_id)
        team = db.execute("SELECT team_notices FROM teams WHERE id = ?", (team_id,)).fetchone()
        return {"team_notices": team["team_notices"]}
    finally:
        db.close()


@router.patch("/{team_id}/notices")
def update_notices(team_id: str, body: UpdateTeamNoticesRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        m = require_team_member(db, team_id, user_id)
        if m["role"] == "viewer":
            raise HTTPException(status_code=403, detail="Viewers cannot edit notices")
        db.execute("UPDATE teams SET team_notices = ? WHERE id = ?", (body.team_notices, team_id))
        db.commit()
        return {"team_notices": body.team_notices}
    finally:
        db.close()


# --------------- Members ---------------

@router.get("/{team_id}/members")
def list_members(team_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_member(db, team_id, user_id)
        rows = db.execute(
            """SELECT u.id, u.name, u.phone, u.email, tm.role, tm.joined_at
               FROM team_memberships tm
               JOIN users u ON tm.user_id = u.id
               WHERE tm.team_id = ?
               ORDER BY tm.joined_at""",
            (team_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        db.close()


@router.patch("/{team_id}/members/{member_user_id}")
def update_member_role(team_id: str, member_user_id: str, body: UpdateMemberRoleRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        if body.role not in ("admin", "contributor", "viewer"):
            raise HTTPException(status_code=400, detail="Invalid role")
        result = db.execute(
            "UPDATE team_memberships SET role = ? WHERE team_id = ? AND user_id = ?",
            (body.role, team_id, member_user_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Member not found")
        db.commit()
        return {"message": "Role updated"}
    finally:
        db.close()


@router.delete("/{team_id}/members/{member_user_id}")
def remove_member(team_id: str, member_user_id: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        if member_user_id == user_id:
            raise HTTPException(status_code=400, detail="Cannot remove yourself")
        result = db.execute(
            "DELETE FROM team_memberships WHERE team_id = ? AND user_id = ?",
            (team_id, member_user_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Member not found")
        db.commit()
        return {"message": "Member removed"}
    finally:
        db.close()


# --------------- Invites ---------------

@router.post("/{team_id}/invite")
def create_invite(team_id: str, body: InviteRequest, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        require_team_admin(db, team_id, user_id)
        code = generate_invite_code()
        invite_id = new_id()
        db.execute(
            """INSERT INTO invite_codes (id, team_id, code, created_by, role)
               VALUES (?, ?, ?, ?, ?)""",
            (invite_id, team_id, code, user_id, body.role or "contributor"),
        )
        db.commit()
        return {"code": code, "invite_id": invite_id}
    finally:
        db.close()


@router.post("/join/{invite_code}")
def join_team(invite_code: str, request: Request):
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        invite = db.execute(
            "SELECT * FROM invite_codes WHERE code = ?", (invite_code,)
        ).fetchone()
        if not invite:
            raise HTTPException(status_code=404, detail="Invalid invite code")

        if invite["max_uses"] and invite["use_count"] >= invite["max_uses"]:
            raise HTTPException(status_code=400, detail="Invite code has been fully used")

        if invite["expires_at"] and datetime.now(timezone.utc).isoformat() > invite["expires_at"]:
            raise HTTPException(status_code=400, detail="Invite code has expired")

        existing = db.execute(
            "SELECT id FROM team_memberships WHERE team_id = ? AND user_id = ?",
            (invite["team_id"], user_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Already a member of this team")

        membership_id = new_id()
        db.execute(
            "INSERT INTO team_memberships (id, team_id, user_id, role) VALUES (?, ?, ?, ?)",
            (membership_id, invite["team_id"], user_id, invite["role"]),
        )
        db.execute(
            "UPDATE invite_codes SET use_count = use_count + 1 WHERE id = ?",
            (invite["id"],),
        )
        db.commit()

        team = db.execute("SELECT id, name FROM teams WHERE id = ?", (invite["team_id"],)).fetchone()
        return {"message": "Joined team", "team_id": team["id"], "team_name": team["name"]}
    finally:
        db.close()
