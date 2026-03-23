import os

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from database import get_db
from auth_utils import get_current_user_id

router = APIRouter()

AGENTMAIL_API_KEY = os.getenv("agent_mail_nurser", "")
AGENTMAIL_INBOX_ID = os.getenv("agentmail_inbox_id", "")
SUPPORT_EMAIL = os.getenv("support_email", "")


class FeedbackRequest(BaseModel):
    message: str


@router.post("/feedback")
def send_feedback(body: FeedbackRequest, request: Request):
    user_id = get_current_user_id(request)

    db = get_db()
    try:
        user = db.execute("SELECT phone FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        phone = user["phone"]
    finally:
        db.close()

    if not AGENTMAIL_API_KEY:
        print(f"[FEEDBACK] from {phone}: {body.message}")
        return {"message": "Feedback received (logged locally)"}

    from agentmail import AgentMail
    client = AgentMail(api_key=AGENTMAIL_API_KEY)
    client.inboxes.messages.send(
        inbox_id=AGENTMAIL_INBOX_ID,
        to=SUPPORT_EMAIL,
        subject=f"Feedback de Nurser - {phone}",
        text=f"user: {phone}\n\n{body.message}",
    )

    return {"message": "Feedback sent"}
