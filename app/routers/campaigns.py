"""
PhishGuard Campaign Router (v2) — CRUD + Targets + QR + Notifications
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import AuditLog, Campaign, CampaignTarget, User
from app.services.qr_generator import generate_qr_code, generate_qr_bytes

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])


# ── Schemas ───────────────────────────────────────────────────────────
class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    campaign_type: str = "awareness"
    expires_in_hours: Optional[int] = None
    notification_email: str = ""
    notification_frequency: str = "immediate"  # immediate, every_5_min, daily
    notifications_enabled: bool = False
    authorized_simulation: bool = False


class TargetCreate(BaseModel):
    name: str = ""
    email: str = ""


class TargetBulkCreate(BaseModel):
    targets: list[TargetCreate]


# ── List Campaigns ───────────────────────────────────────────────────
@router.get("")
def list_campaigns(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all campaigns for the current user."""
    campaigns = (
        db.query(Campaign)
        .filter(Campaign.user_id == user.id)
        .order_by(Campaign.created_at.desc())
        .all()
    )
    result = []
    for c in campaigns:
        # Auto-expire
        if c.expires_at:
            exp = c.expires_at
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > exp and c.status == "active":
                c.status = "expired"
                db.commit()

        total = len(c.targets)
        clicked = sum(1 for t in c.targets if t.clicked)
        submitted = sum(1 for t in c.targets if t.submitted)
        result.append({
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "status": c.status,
            "campaign_type": c.campaign_type,
            "created_at": str(c.created_at),
            "expires_at": str(c.expires_at) if c.expires_at else None,
            "total_targets": total,
            "clicked": clicked,
            "submitted": submitted,
            "click_rate": round(clicked / total * 100, 1) if total else 0,
            "notification_email": c.notification_email,
            "notification_frequency": c.notification_frequency,
            "notifications_enabled": c.notifications_enabled,
            "authorized_simulation": c.authorized_simulation,
        })
    return result


# ── Create Campaign ──────────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def create_campaign(
    body: CampaignCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new training campaign (requires authorized_simulation confirmation)."""
    if not body.authorized_simulation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm this is an authorized security-awareness simulation.",
        )

    expires_at = None
    hours = body.expires_in_hours or settings.DEFAULT_CAMPAIGN_EXPIRY_HOURS
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours)

    campaign = Campaign(
        name=body.name.strip(),
        description=body.description.strip(),
        campaign_type=body.campaign_type,
        expires_at=expires_at,
        user_id=user.id,
        notification_email=body.notification_email.strip(),
        notification_frequency=body.notification_frequency,
        notifications_enabled=body.notifications_enabled,
        authorized_simulation=body.authorized_simulation,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    db.add(AuditLog(
        user_id=user.id,
        action="campaign_created",
        details=f"Campaign '{campaign.name}' (ID: {campaign.id}) created. Notifications: {campaign.notifications_enabled}",
    ))
    db.commit()

    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "created_at": str(campaign.created_at),
        "expires_at": str(campaign.expires_at),
        "notifications_enabled": campaign.notifications_enabled,
    }


# ── Get Campaign Detail ──────────────────────────────────────────────
@router.get("/{campaign_id}")
def get_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get detailed info about a campaign."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    targets = []
    for t in campaign.targets:
        link = f"{settings.BASE_URL}/t/{t.token}"
        targets.append({
            "id": t.id,
            "name": t.name,
            "email": t.email,
            "token": t.token,
            "link": link,
            "clicked": t.clicked,
            "submitted": t.submitted,
            "click_time": str(t.click_time) if t.click_time else None,
        })

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "campaign_type": campaign.campaign_type,
        "created_at": str(campaign.created_at),
        "expires_at": str(campaign.expires_at) if campaign.expires_at else None,
        "notification_email": campaign.notification_email,
        "notification_frequency": campaign.notification_frequency,
        "notifications_enabled": campaign.notifications_enabled,
        "authorized_simulation": campaign.authorized_simulation,
        "targets": targets,
        "event_count": len(campaign.events),
    }


# ── Delete Campaign ──────────────────────────────────────────────────
@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a campaign and all associated data."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    name = campaign.name
    db.delete(campaign)
    db.add(AuditLog(
        user_id=user.id,
        action="campaign_deleted",
        details=f"Campaign '{name}' (ID: {campaign_id}) deleted",
    ))
    db.commit()


# ── Toggle Campaign Status ───────────────────────────────────────────
@router.patch("/{campaign_id}/status")
def toggle_status(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Toggle campaign between active and paused."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "paused" if campaign.status == "active" else "active"
    db.commit()
    return {"id": campaign.id, "status": campaign.status}


# ── Add Targets ───────────────────────────────────────────────────────
@router.post("/{campaign_id}/targets")
def add_targets(
    campaign_id: int,
    body: TargetBulkCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add one or more targets to a campaign."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    current_count = len(campaign.targets)
    if current_count + len(body.targets) > settings.MAX_TARGETS_PER_CAMPAIGN:
        raise HTTPException(
            status_code=400,
            detail=f"Max {settings.MAX_TARGETS_PER_CAMPAIGN} targets per campaign",
        )

    created = []
    for t in body.targets:
        target = CampaignTarget(
            campaign_id=campaign.id,
            name=t.name.strip(),
            email=t.email.strip(),
        )
        db.add(target)
        db.flush()
        link = f"{settings.BASE_URL}/t/{target.token}"
        created.append({
            "id": target.id,
            "name": target.name,
            "email": target.email,
            "token": target.token,
            "link": link,
        })

    db.add(AuditLog(
        user_id=user.id,
        action="targets_added",
        details=f"{len(created)} target(s) added to campaign '{campaign.name}'",
    ))
    db.commit()
    return {"added": len(created), "targets": created}


# ── QR Code for Target ───────────────────────────────────────────────
@router.get("/{campaign_id}/targets/{target_id}/qr")
def get_target_qr(
    campaign_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a QR code for a target's campaign link (returns base64 data URI)."""
    target = (
        db.query(CampaignTarget)
        .filter(
            CampaignTarget.id == target_id,
            CampaignTarget.campaign_id == campaign_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    link = f"{settings.BASE_URL}/t/{target.token}"
    qr_data_uri = generate_qr_code(link)
    return {"link": link, "qr_code": qr_data_uri}


@router.get("/{campaign_id}/targets/{target_id}/qr.png")
def get_target_qr_image(
    campaign_id: int,
    target_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a QR code PNG image for download."""
    target = (
        db.query(CampaignTarget)
        .filter(
            CampaignTarget.id == target_id,
            CampaignTarget.campaign_id == campaign_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    link = f"{settings.BASE_URL}/t/{target.token}"
    png_bytes = generate_qr_bytes(link)
    return Response(content=png_bytes, media_type="image/png")
