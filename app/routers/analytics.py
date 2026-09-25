"""
PhishGuard Analytics Router — Dashboard stats & campaign analytics
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, Campaign, CampaignTarget, Event, URLScan, User

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


# ── Dashboard Overview ────────────────────────────────────────────────
@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return high-level dashboard statistics."""
    total_campaigns = (
        db.query(Campaign).filter(Campaign.user_id == user.id).count()
    )
    active_campaigns = (
        db.query(Campaign)
        .filter(Campaign.user_id == user.id, Campaign.status == "active")
        .count()
    )

    # Targets across all user campaigns
    user_campaign_ids = [
        c.id
        for c in db.query(Campaign.id).filter(Campaign.user_id == user.id).all()
    ]

    total_targets = 0
    total_clicked = 0
    total_submitted = 0
    if user_campaign_ids:
        total_targets = (
            db.query(CampaignTarget)
            .filter(CampaignTarget.campaign_id.in_(user_campaign_ids))
            .count()
        )
        total_clicked = (
            db.query(CampaignTarget)
            .filter(
                CampaignTarget.campaign_id.in_(user_campaign_ids),
                CampaignTarget.clicked == True,
            )
            .count()
        )
        total_submitted = (
            db.query(CampaignTarget)
            .filter(
                CampaignTarget.campaign_id.in_(user_campaign_ids),
                CampaignTarget.submitted == True,
            )
            .count()
        )

    total_url_scans = (
        db.query(URLScan).filter(URLScan.user_id == user.id).count()
    )

    total_events = 0
    if user_campaign_ids:
        total_events = (
            db.query(Event)
            .filter(Event.campaign_id.in_(user_campaign_ids))
            .count()
        )

    click_rate = round(total_clicked / total_targets * 100, 1) if total_targets else 0

    return {
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "total_targets": total_targets,
        "total_clicked": total_clicked,
        "total_submitted": total_submitted,
        "click_rate": click_rate,
        "total_url_scans": total_url_scans,
        "total_events": total_events,
    }


# ── Campaign Analytics ────────────────────────────────────────────────
@router.get("/campaign/{campaign_id}")
def campaign_analytics(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return detailed analytics for a specific campaign."""
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.user_id == user.id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    events = (
        db.query(Event)
        .filter(Event.campaign_id == campaign_id)
        .order_by(Event.timestamp.desc())
        .all()
    )

    # Event type breakdown
    event_types = {}
    for e in events:
        event_types[e.event_type] = event_types.get(e.event_type, 0) + 1

    # Location data (consent-based only)
    locations = []
    for e in events:
        if e.location_consent and e.location_lat is not None:
            locations.append({
                "lat": e.location_lat,
                "lng": e.location_lng,
                "timestamp": str(e.timestamp),
                "event_type": e.event_type,
            })

    # Timeline (events per hour over last 72 hours)
    now = datetime.now(timezone.utc)
    timeline = []
    for hours_ago in range(72, -1, -1):
        t_start = now - timedelta(hours=hours_ago + 1)
        t_end = now - timedelta(hours=hours_ago)
        count = sum(
            1 for e in events
            if e.timestamp and t_start <= e.timestamp.replace(tzinfo=timezone.utc) < t_end
        )
        timeline.append({
            "hour": str(t_end),
            "count": count,
        })

    # Browser breakdown
    browsers = {}
    for e in events:
        if e.browser_info and isinstance(e.browser_info, dict):
            browser_name = e.browser_info.get("browser", "Unknown")
            browsers[browser_name] = browsers.get(browser_name, 0) + 1

    total = len(campaign.targets)
    clicked = sum(1 for t in campaign.targets if t.clicked)
    submitted = sum(1 for t in campaign.targets if t.submitted)

    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "status": campaign.status,
        "total_targets": total,
        "clicked": clicked,
        "submitted": submitted,
        "click_rate": round(clicked / total * 100, 1) if total else 0,
        "submit_rate": round(submitted / total * 100, 1) if total else 0,
        "total_events": len(events),
        "event_types": event_types,
        "locations": locations,
        "timeline": timeline,
        "browsers": browsers,
        "recent_events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "session_id": e.session_id,
                "ip_address": e.ip_address,
                "user_agent": e.user_agent[:100] if e.user_agent else "",
                "browser_family": e.browser_family or "",
                "os_family": e.os_family or "",
                "device_category": e.device_category or "",
                "location_consent": e.location_consent,
                "timestamp": str(e.timestamp),
            }
            for e in events[:50]
        ],
    }


# ── Audit Logs ────────────────────────────────────────────────────────
@router.get("/audit-logs")
def audit_logs(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the last 100 audit log entries."""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user.id)
        .order_by(AuditLog.timestamp.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": l.id,
            "action": l.action,
            "details": l.details,
            "ip_address": l.ip_address,
            "timestamp": str(l.timestamp),
        }
        for l in logs
    ]
