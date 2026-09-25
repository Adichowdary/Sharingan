"""
PhishGuard Notifications Router — Notification log & management
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Campaign, NotificationLog, User

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the latest 100 notification logs across all user campaigns."""
    user_campaign_ids = [
        c.id
        for c in db.query(Campaign.id).filter(Campaign.user_id == user.id).all()
    ]
    if not user_campaign_ids:
        return []

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.campaign_id.in_(user_campaign_ids))
        .order_by(NotificationLog.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": n.id,
            "campaign_id": n.campaign_id,
            "notification_type": n.notification_type,
            "recipient_email": n.recipient_email,
            "subject": n.subject,
            "status": n.status,
            "error_message": n.error_message,
            "sent_at": str(n.sent_at) if n.sent_at else None,
            "created_at": str(n.created_at),
        }
        for n in logs
    ]


@router.get("/stats")
def notification_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return notification send statistics."""
    user_campaign_ids = [
        c.id
        for c in db.query(Campaign.id).filter(Campaign.user_id == user.id).all()
    ]
    if not user_campaign_ids:
        return {"total": 0, "sent": 0, "failed": 0, "pending": 0}

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.campaign_id.in_(user_campaign_ids))
        .all()
    )
    total = len(logs)
    sent = sum(1 for l in logs if l.status == "sent")
    failed = sum(1 for l in logs if l.status == "failed")
    pending = sum(1 for l in logs if l.status == "pending")

    return {"total": total, "sent": sent, "failed": failed, "pending": pending}
