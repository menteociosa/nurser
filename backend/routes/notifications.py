import os
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pywebpush import webpush, WebPushException

from database import get_db
from auth_utils import get_current_user_id, new_id

logger = logging.getLogger(__name__)

router = APIRouter()

VAPID_PRIVATE_KEY = os.getenv("vapid_private_key", "")
VAPID_PUBLIC_KEY = os.getenv("vapid_public_key", "")
_vapid_email_raw = os.getenv("vapid_email", "support@example.com")
VAPID_CLAIMS_SUB = _vapid_email_raw if _vapid_email_raw.startswith("mailto:") else f"mailto:{_vapid_email_raw}"


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionBody(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys


class UnsubscribeBody(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
def get_vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    return {"public_key": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
def subscribe_push(body: PushSubscriptionBody, request: Request):
    """Save a push subscription for the current user."""
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        # Upsert: update if same endpoint already exists for this user
        existing = db.execute(
            "SELECT id FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
            (user_id, body.endpoint),
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE push_subscriptions SET p256dh = ?, auth = ? WHERE id = ?",
                (body.keys.p256dh, body.keys.auth, existing["id"]),
            )
        else:
            db.execute(
                "INSERT INTO push_subscriptions (id, user_id, endpoint, p256dh, auth) VALUES (?, ?, ?, ?, ?)",
                (new_id(), user_id, body.endpoint, body.keys.p256dh, body.keys.auth),
            )
        db.commit()
        return {"message": "Subscribed"}
    finally:
        db.close()


@router.post("/unsubscribe")
def unsubscribe_push(body: UnsubscribeBody, request: Request):
    """Remove a push subscription for the current user."""
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        db.execute(
            "DELETE FROM push_subscriptions WHERE user_id = ? AND endpoint = ?",
            (user_id, body.endpoint),
        )
        db.commit()
        return {"message": "Unsubscribed"}
    finally:
        db.close()


def send_push_to_team(db, team_id: str, title: str, body: str, exclude_user_id: Optional[str] = None):
    """
    Send a push notification to all team members who have:
    - receive_push_notifications = TRUE for this team
    - at least one push subscription saved
    """
    logger.info("[PUSH] send_push_to_team called: team=%s title=%r exclude=%s", team_id, title, exclude_user_id)

    members = db.execute(
        """SELECT tm.user_id
           FROM team_memberships tm
           WHERE tm.team_id = ? AND tm.receive_push_notifications = TRUE""",
        (team_id,),
    ).fetchall()

    logger.info("[PUSH] members with receive_push_notifications=TRUE: %d", len(members))

    for member in members:
        uid = member["user_id"]
        if uid == exclude_user_id:
            logger.info("[PUSH] skipping excluded user %s", uid)
            continue
        subs = db.execute(
            "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
            (uid,),
        ).fetchall()
        logger.info("[PUSH] user %s has %d subscription(s)", uid, len(subs))
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                    },
                    data=json.dumps({"title": title, "body": body}),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": VAPID_CLAIMS_SUB},
                )
                logger.info("[PUSH] sent OK to %s", sub["endpoint"][:60])
            except WebPushException as e:
                logger.warning("[PUSH] WebPushException for %s: %s", sub["endpoint"][:60], e)
                # 410 Gone = subscription expired/removed; clean it up
                if "410" in str(e) or "404" in str(e):
                    db.execute(
                        "DELETE FROM push_subscriptions WHERE endpoint = ?",
                        (sub["endpoint"],),
                    )
                    db.commit()
            except Exception as e:
                logger.error("[PUSH] unexpected error for %s: %s", sub["endpoint"][:60], e)


@router.post("/test-push")
def test_push(request: Request):
    """Send a test push to the current user's subscriptions (debug endpoint)."""
    user_id = get_current_user_id(request)
    db = get_db()
    try:
        subs = db.execute(
            "SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        if not subs:
            return {"error": "No subscriptions found for your user. Toggle notifications on first."}
        results = []
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        "endpoint": sub["endpoint"],
                        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
                    },
                    data=json.dumps({"title": "Test notification", "body": "Push is working!"}),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": VAPID_CLAIMS_SUB},
                )
                results.append({"endpoint": sub["endpoint"][:60], "status": "sent"})
            except Exception as e:
                results.append({"endpoint": sub["endpoint"][:60], "error": str(e)})
        return {"results": results}
    finally:
        db.close()
