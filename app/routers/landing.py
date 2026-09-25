"""
PhishGuard Landing Page Router (v2)

- Enhanced telemetry tracking (non-sensitive only)
- User-agent parsing for browser/OS/device
- Notification triggering on events
- SSE broadcast for real-time dashboard
"""
import re
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Campaign, CampaignTarget, Event
from app.services.notification_queue import (
    broadcast_event, check_cooldown, enqueue_notification, add_to_batch,
)

router = APIRouter(tags=["Landing Pages"])


class EventSubmission(BaseModel):
    event_type: str = "submit"
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    location_consent: bool = False
    browser_info: Optional[dict] = None


# ── User-Agent Parser ─────────────────────────────────────────────────
def _parse_user_agent(ua: str) -> dict:
    """Lightweight UA parser — extracts browser family, OS, and device category."""
    ua_lower = ua.lower()

    # Browser
    if "firefox" in ua_lower:
        browser = "Firefox"
    elif "edg" in ua_lower:
        browser = "Edge"
    elif "opr" in ua_lower or "opera" in ua_lower:
        browser = "Opera"
    elif "chrome" in ua_lower:
        browser = "Chrome"
    elif "safari" in ua_lower:
        browser = "Safari"
    else:
        browser = "Other"

    # OS
    if "windows" in ua_lower:
        os_fam = "Windows"
    elif "mac os" in ua_lower or "macintosh" in ua_lower:
        os_fam = "macOS"
    elif "android" in ua_lower:
        os_fam = "Android"
    elif "iphone" in ua_lower or "ipad" in ua_lower:
        os_fam = "iOS"
    elif "linux" in ua_lower:
        os_fam = "Linux"
    else:
        os_fam = "Other"

    # Device
    if any(kw in ua_lower for kw in ("mobile", "android", "iphone")):
        device = "Mobile"
    elif any(kw in ua_lower for kw in ("tablet", "ipad")):
        device = "Tablet"
    else:
        device = "Desktop"

    return {"browser": browser, "os": os_fam, "device": device}


# ── Training Landing Page ─────────────────────────────────────────────
@router.get("/t/{token}", response_class=HTMLResponse)
async def landing_page(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Render the security-awareness training page and record a click event."""
    target = db.query(CampaignTarget).filter(CampaignTarget.token == token).first()
    if not target:
        raise HTTPException(status_code=404, detail="Link not found or expired")

    campaign = db.query(Campaign).filter(Campaign.id == target.campaign_id).first()
    if not campaign or campaign.status not in ("active",):
        raise HTTPException(status_code=410, detail="This campaign has ended")

    # Check expiration
    if campaign.expires_at:
        exp = campaign.expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            campaign.status = "expired"
            db.commit()
            raise HTTPException(status_code=410, detail="This campaign link has expired")

    # Parse user agent
    ua_str = request.headers.get("user-agent", "")
    ua_parsed = _parse_user_agent(ua_str)

    # Record click
    if not target.clicked:
        target.clicked = True
        target.click_time = datetime.now(timezone.utc)

    event = Event(
        campaign_id=campaign.id,
        target_id=target.id,
        event_type="click",
        ip_address=request.client.host if request.client else "",
        user_agent=ua_str,
        browser_family=ua_parsed["browser"],
        os_family=ua_parsed["os"],
        device_category=ua_parsed["device"],
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Broadcast SSE event
    sse_data = {
        "type": "campaign_event",
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "event_type": "click",
        "session_id": event.session_id,
        "browser": ua_parsed["browser"],
        "os": ua_parsed["os"],
        "device": ua_parsed["device"],
        "timestamp": str(event.timestamp),
    }
    background_tasks.add_task(asyncio.ensure_future, broadcast_event(sse_data))

    # Trigger notification
    if campaign.notifications_enabled and campaign.notification_email:
        _trigger_notification(campaign, event, ua_parsed, background_tasks)

    html = _render_landing_html(token, campaign.name, target.name)
    return HTMLResponse(content=html)


# ── Record Event from Landing Page ────────────────────────────────────
@router.post("/t/{token}/event")
async def record_event(
    token: str,
    body: EventSubmission,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Record a consent-based event from the training landing page."""
    target = db.query(CampaignTarget).filter(CampaignTarget.token == token).first()
    if not target:
        raise HTTPException(status_code=404, detail="Invalid token")

    campaign = db.query(Campaign).filter(Campaign.id == target.campaign_id).first()

    target.submitted = True

    ua_str = request.headers.get("user-agent", "")
    ua_parsed = _parse_user_agent(ua_str)

    event = Event(
        campaign_id=target.campaign_id,
        target_id=target.id,
        event_type=body.event_type,
        ip_address=request.client.host if request.client else "",
        user_agent=ua_str,
        location_lat=body.location_lat if body.location_consent else None,
        location_lng=body.location_lng if body.location_consent else None,
        location_consent=body.location_consent,
        browser_info=body.browser_info,
        browser_family=ua_parsed["browser"],
        os_family=ua_parsed["os"],
        device_category=ua_parsed["device"],
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    # Broadcast SSE
    sse_data = {
        "type": "campaign_event",
        "campaign_id": target.campaign_id,
        "campaign_name": campaign.name if campaign else "",
        "event_type": body.event_type,
        "session_id": event.session_id,
        "browser": ua_parsed["browser"],
        "os": ua_parsed["os"],
        "device": ua_parsed["device"],
        "location_consent": body.location_consent,
        "timestamp": str(event.timestamp),
    }
    background_tasks.add_task(asyncio.ensure_future, broadcast_event(sse_data))

    # Trigger notification
    if campaign and campaign.notifications_enabled and campaign.notification_email:
        _trigger_notification(campaign, event, ua_parsed, background_tasks)

    return {"status": "recorded", "event_type": body.event_type, "session_id": event.session_id}


# ── Notification Trigger ──────────────────────────────────────────────
def _trigger_notification(campaign, event, ua_parsed, background_tasks):
    """Decide how to route the notification based on campaign frequency."""
    job = {
        "campaign_id": campaign.id,
        "event_id": event.id,
        "event_type": event.event_type,
        "session_id": event.session_id,
        "timestamp": str(event.timestamp),
        "browser_info": ua_parsed.get("browser", ""),
        "device_info": f"{ua_parsed.get('os', '')} / {ua_parsed.get('device', '')}",
        "dashboard_url": f"{settings.BASE_URL}/#campaigns",
    }

    freq = campaign.notification_frequency or "immediate"

    if freq == "immediate":
        if check_cooldown(campaign.id):
            background_tasks.add_task(asyncio.ensure_future, enqueue_notification(job))
    elif freq == "every_5_min":
        add_to_batch(campaign.id, job)
    # "daily" is handled by the daily summary cron (separate worker)


# ── Render Landing HTML ───────────────────────────────────────────────
def _render_landing_html(token: str, campaign_name: str, target_name: str) -> str:
    """Generate the security awareness training HTML page."""
    greeting = f'Hello <strong>{target_name}</strong>! ' if target_name else ''
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Security Awareness Training</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:'Inter',sans-serif;background:linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#e2e8f0}}
        .container{{max-width:680px;width:100%}}
        .card{{background:rgba(255,255,255,.06);backdrop-filter:blur(20px);border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:40px;margin-bottom:20px;animation:fadeUp .6s ease-out}}
        @keyframes fadeUp{{from{{opacity:0;transform:translateY(30px)}}to{{opacity:1;transform:translateY(0)}}}}
        .icon-warning{{width:80px;height:80px;margin:0 auto 24px;background:linear-gradient(135deg,#f59e0b,#ef4444);border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:40px;animation:pulse 2s infinite}}
        @keyframes pulse{{0%,100%{{transform:scale(1)}}50%{{transform:scale(1.08)}}}}
        h1{{font-size:28px;font-weight:700;text-align:center;margin-bottom:12px;background:linear-gradient(135deg,#f59e0b,#ef4444);-webkit-background-clip:text;-webkit-text-fill-color:transparent}}
        .subtitle{{text-align:center;color:#94a3b8;font-size:16px;margin-bottom:28px;line-height:1.6}}
        .info-box{{background:rgba(124,58,237,.15);border:1px solid rgba(124,58,237,.3);border-radius:12px;padding:20px;margin-bottom:20px}}
        .info-box h3{{color:#a78bfa;font-size:14px;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px}}
        .info-box ul{{list-style:none;padding:0}}
        .info-box li{{padding:8px 0;padding-left:24px;position:relative;color:#cbd5e1;font-size:14px;line-height:1.5}}
        .info-box li::before{{content:"✓";position:absolute;left:0;color:#34d399;font-weight:bold}}
        .consent-section{{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:12px;padding:20px;margin-top:20px}}
        .consent-section h3{{color:#34d399;font-size:14px;margin-bottom:12px}}
        .consent-section p{{color:#94a3b8;font-size:13px;margin-bottom:16px;line-height:1.5}}
        .notice-box{{background:rgba(6,182,212,.1);border:1px solid rgba(6,182,212,.3);border-radius:12px;padding:16px;margin-bottom:20px;font-size:13px;color:#67e8f9;line-height:1.5}}
        .btn{{display:inline-flex;align-items:center;gap:8px;padding:12px 24px;border:none;border-radius:10px;font-family:'Inter',sans-serif;font-size:14px;font-weight:600;cursor:pointer;transition:all .3s ease;margin-right:8px;margin-bottom:8px}}
        .btn-primary{{background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff}}
        .btn-primary:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(124,58,237,.4)}}
        .btn-secondary{{background:rgba(255,255,255,.1);color:#e2e8f0;border:1px solid rgba(255,255,255,.15)}}
        .btn-secondary:hover{{background:rgba(255,255,255,.15)}}
        .result-box{{display:none;background:rgba(34,197,94,.15);border:1px solid rgba(34,197,94,.3);border-radius:12px;padding:20px;margin-top:16px;animation:fadeUp .4s ease-out}}
        .result-box.visible{{display:block}}
        .result-box p{{color:#a7f3d0;font-size:14px;line-height:1.6}}
        .footer{{text-align:center;color:#475569;font-size:12px;margin-top:20px}}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="icon-warning">\u26a0\ufe0f</div>
            <h1>This Was a Simulated Phishing Test</h1>
            <p class="subtitle">
                {greeting}You clicked a link from a <strong>security awareness training campaign</strong>.
                This is NOT a real attack \u2014 it's an authorized exercise to help improve security awareness.
            </p>

            <div class="notice-box">
                \U0001f6c8 <strong>Authorized Security Exercise</strong><br>
                This is an authorized security-awareness simulation conducted by your organization.
                No passwords, credentials, cookies, or sensitive data are collected.
                Only non-sensitive training telemetry (event type, browser family, timestamp)
                is recorded for educational purposes.
            </div>

            <div class="info-box">
                <h3>\U0001f6e1\ufe0f What You Should Learn</h3>
                <ul>
                    <li>Always verify the sender before clicking links in emails or messages</li>
                    <li>Check the URL carefully \u2014 look for misspellings and suspicious domains</li>
                    <li>Never enter credentials on pages reached through unexpected links</li>
                    <li>Hover over links to preview the actual destination URL</li>
                    <li>Report suspicious emails to your IT/security team immediately</li>
                    <li>Use multi-factor authentication (MFA) on all accounts</li>
                </ul>
            </div>

            <div class="consent-section">
                <h3>\U0001f4cb Training Data Collection (Optional)</h3>
                <p>
                    This security-awareness exercise can <strong>optionally</strong> use your
                    browser's location permission. Your location will only be processed if you
                    <strong>explicitly grant browser permission</strong>. You can decline without
                    any consequences. No passwords, cookies, or keystrokes are collected.
                </p>
                <button class="btn btn-primary" onclick="submitConsent(true)">
                    \u2705 I Consent \u2014 Share Training Data
                </button>
                <button class="btn btn-secondary" onclick="submitConsent(false)">
                    \u274c No Thanks \u2014 Skip
                </button>
                <div id="result" class="result-box">
                    <p id="result-text"></p>
                </div>
            </div>
        </div>
        <p class="footer">
            PhishGuard Security Awareness Platform \u00b7 Campaign: {campaign_name}
        </p>
    </div>

    <script>
        const TOKEN = "{token}";

        function getBrowserInfo() {{
            return {{
                browser: navigator.userAgent,
                platform: navigator.platform,
                language: navigator.language,
                screen: navigator.screen ? (navigator.screen.width + "x" + navigator.screen.height) : "unknown",
                timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
                cookiesEnabled: navigator.cookieEnabled,
                online: navigator.onLine,
            }};
        }}

        async function submitConsent(withLocation) {{
            const payload = {{
                event_type: withLocation ? "location_consent" : "submit",
                location_consent: false,
                browser_info: getBrowserInfo(),
            }};

            if (withLocation && "geolocation" in navigator) {{
                try {{
                    const pos = await new Promise((resolve, reject) =>
                        navigator.geolocation.getCurrentPosition(resolve, reject, {{ timeout: 10000 }})
                    );
                    payload.location_lat = pos.coords.latitude;
                    payload.location_lng = pos.coords.longitude;
                    payload.location_consent = true;
                }} catch (err) {{
                    payload.event_type = "location_denied";
                    console.log("Location denied or unavailable:", err.message);
                }}
            }}

            try {{
                const resp = await fetch("/t/" + TOKEN + "/event", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(payload),
                }});
                const data = await resp.json();
                const box = document.getElementById("result");
                const text = document.getElementById("result-text");
                box.classList.add("visible");
                if (payload.location_consent) {{
                    text.innerHTML = "\u2705 Thank you! Your training data (including authorized location) has been recorded.<br><small>Session: " + (data.session_id || "") + "</small>";
                }} else {{
                    text.innerHTML = "\u2705 Thank you for participating in this security awareness exercise! Stay vigilant against real phishing attempts.<br><small>Session: " + (data.session_id || "") + "</small>";
                }}
            }} catch (err) {{
                console.error("Submit error:", err);
            }}
        }}
    </script>
</body>
</html>"""
