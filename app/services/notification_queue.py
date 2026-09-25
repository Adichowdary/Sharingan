"""
PhishGuard Notification Queue & SSE Event Bus

- In-memory async queue for background email processing
- Server-Sent Events broadcast for real-time dashboard
- Cooldown tracking to prevent notification flooding
"""
import asyncio
import logging
from datetime import datetime, timezone
from collections import defaultdict
from typing import Any

logger = logging.getLogger("phishguard.queue")

# ── SSE Event Bus ─────────────────────────────────────────────────────
_sse_subscribers: list[asyncio.Queue] = []


async def subscribe_sse() -> asyncio.Queue:
    """Create a new SSE subscription queue."""
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _sse_subscribers.append(queue)
    logger.info(f"SSE subscriber added ({len(_sse_subscribers)} active)")
    return queue


def unsubscribe_sse(queue: asyncio.Queue):
    """Remove an SSE subscription."""
    if queue in _sse_subscribers:
        _sse_subscribers.remove(queue)
        logger.info(f"SSE subscriber removed ({len(_sse_subscribers)} active)")


async def broadcast_event(event_data: dict):
    """Push an event to all SSE subscribers."""
    dead: list[asyncio.Queue] = []
    for q in _sse_subscribers:
        try:
            q.put_nowait(event_data)
        except asyncio.QueueFull:
            dead.append(q)
    for q in dead:
        unsubscribe_sse(q)


# ── Notification Cooldown ─────────────────────────────────────────────
_cooldowns: dict[str, datetime] = {}
COOLDOWN_SECONDS = 30


def check_cooldown(campaign_id: int) -> bool:
    """Return True if notification is allowed (cooldown elapsed)."""
    key = f"c_{campaign_id}"
    now = datetime.now(timezone.utc)
    last = _cooldowns.get(key)
    if last and (now - last).total_seconds() < COOLDOWN_SECONDS:
        return False
    _cooldowns[key] = now
    return True


# ── Batch Buffer (for "every 5 min" frequency) ───────────────────────
_batch_buffer: dict[int, list[dict]] = defaultdict(list)


def add_to_batch(campaign_id: int, event_data: dict):
    """Buffer an event for batched sending."""
    _batch_buffer[campaign_id].append(event_data)


def pop_batch(campaign_id: int) -> list[dict]:
    """Retrieve and clear all buffered events for a campaign."""
    return _batch_buffer.pop(campaign_id, [])


def all_batch_campaign_ids() -> list[int]:
    """Return campaign IDs that have pending batched events."""
    return list(_batch_buffer.keys())


# ── Notification Job Queue ────────────────────────────────────────────
_job_queue: asyncio.Queue | None = None


def _get_queue() -> asyncio.Queue:
    global _job_queue
    if _job_queue is None:
        _job_queue = asyncio.Queue(maxsize=500)
    return _job_queue


async def enqueue_notification(job: dict):
    """Add a notification job to the async queue."""
    try:
        _get_queue().put_nowait(job)
    except asyncio.QueueFull:
        logger.warning("Notification queue full — dropping job")


async def notification_worker(db_factory):
    """
    Background coroutine that processes the notification queue.
    Runs forever; call as an asyncio.Task from app startup.
    """
    from app.services.email_service import send_email, render_event_email
    from app.models import NotificationLog, Campaign, EmailConfig

    logger.info("Notification worker started")

    while True:
        job = await _get_queue().get()
        try:
            db = db_factory()
            try:
                campaign = db.query(Campaign).filter(Campaign.id == job["campaign_id"]).first()
                if not campaign or not campaign.notifications_enabled:
                    continue

                email_cfg = (
                    db.query(EmailConfig)
                    .filter(EmailConfig.user_id == campaign.user_id, EmailConfig.enabled == True)
                    .first()
                )

                to_email = campaign.notification_email
                if not to_email:
                    continue

                subject, html = render_event_email(
                    campaign_name=campaign.name,
                    event_type=job.get("event_type", "click"),
                    session_id=job.get("session_id", "Unknown"),
                    timestamp=job.get("timestamp", ""),
                    browser_info=job.get("browser_info", ""),
                    device_info=job.get("device_info", ""),
                    dashboard_url=job.get("dashboard_url", ""),
                )

                smtp_kwargs = {}
                if email_cfg:
                    smtp_kwargs = {
                        "smtp_host": email_cfg.smtp_host,
                        "smtp_port": email_cfg.smtp_port,
                        "smtp_username": email_cfg.smtp_username,
                        "smtp_password": email_cfg.smtp_password_encrypted,
                        "sender_email": email_cfg.sender_email,
                        "sender_name": email_cfg.sender_name,
                    }

                result = send_email(to_email, subject, html, **smtp_kwargs)

                log = NotificationLog(
                    campaign_id=campaign.id,
                    event_id=job.get("event_id"),
                    notification_type=job.get("event_type", "click"),
                    recipient_email=to_email,
                    subject=subject,
                    status=result["status"],
                    error_message=result.get("error"),
                    sent_at=datetime.now(timezone.utc) if result["status"] == "sent" else None,
                )
                db.add(log)
                db.commit()

                logger.info(f"Notification {result['status']}: {subject} -> {to_email}")
            finally:
                db.close()

        except Exception as exc:
            logger.error(f"Notification worker error: {exc}", exc_info=True)


async def batch_worker(db_factory):
    """
    Background coroutine that flushes batched notifications every 5 minutes.
    """
    from app.services.email_service import send_email, render_event_email
    from app.models import NotificationLog, Campaign, EmailConfig

    logger.info("Batch notification worker started")

    while True:
        await asyncio.sleep(300)  # 5 minutes
        campaign_ids = all_batch_campaign_ids()
        for cid in campaign_ids:
            events = pop_batch(cid)
            if not events:
                continue
            try:
                db = db_factory()
                try:
                    campaign = db.query(Campaign).filter(Campaign.id == cid).first()
                    if not campaign or not campaign.notification_email:
                        continue

                    summary_lines = "\n".join(
                        f"• {e.get('event_type', '?')} — Session {e.get('session_id', '?')} at {e.get('timestamp', '?')}"
                        for e in events
                    )

                    subject = f"\U0001f6e1\ufe0f Batch: {len(events)} events for {campaign.name}"
                    html = f"""<html><body style="font-family:sans-serif;background:#0f0f23;color:#e2e8f0;padding:32px">
<div style="max-width:600px;margin:auto;background:#1a1a2e;border-radius:16px;padding:32px;border:1px solid rgba(255,255,255,.1)">
<h2 style="color:#a78bfa">\U0001f6e1\ufe0f Batch Notification — {campaign.name}</h2>
<p style="color:#94a3b8">{len(events)} events recorded in the last 5 minutes:</p>
<pre style="color:#e2e8f0;font-size:13px;line-height:1.8">{summary_lines}</pre>
<hr style="border:none;border-top:1px solid rgba(255,255,255,.08);margin:20px 0">
<p style="color:#475569;font-size:11px">PhishGuard automated batch notification</p>
</div></body></html>"""

                    email_cfg = (
                        db.query(EmailConfig)
                        .filter(EmailConfig.user_id == campaign.user_id, EmailConfig.enabled == True)
                        .first()
                    )
                    smtp_kwargs = {}
                    if email_cfg:
                        smtp_kwargs = {
                            "smtp_host": email_cfg.smtp_host,
                            "smtp_port": email_cfg.smtp_port,
                            "smtp_username": email_cfg.smtp_username,
                            "smtp_password": email_cfg.smtp_password_encrypted,
                            "sender_email": email_cfg.sender_email,
                            "sender_name": email_cfg.sender_name,
                        }

                    result = send_email(campaign.notification_email, subject, html, **smtp_kwargs)
                    db.add(NotificationLog(
                        campaign_id=cid,
                        notification_type="batch",
                        recipient_email=campaign.notification_email,
                        subject=subject,
                        status=result["status"],
                        error_message=result.get("error"),
                        sent_at=datetime.now(timezone.utc) if result["status"] == "sent" else None,
                    ))
                    db.commit()
                finally:
                    db.close()
            except Exception as exc:
                logger.error(f"Batch worker error for campaign {cid}: {exc}")
