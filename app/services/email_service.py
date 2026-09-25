"""
PhishGuard Email Service
Handles SMTP connections and sending HTML notification emails.
"""
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("phishguard.email")

# ── Provider presets ──────────────────────────────────────────────────
SMTP_PRESETS = {
    "gmail": {"host": "smtp.gmail.com", "port": 587},
    "outlook": {"host": "smtp-mail.outlook.com", "port": 587},
    "yahoo": {"host": "smtp.mail.yahoo.com", "port": 587},
    "custom": {"host": "", "port": 587},
}


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    smtp_host: str = "",
    smtp_port: int = 587,
    smtp_username: str = "",
    smtp_password: str = "",
    sender_email: str = "",
    sender_name: str = "PhishGuard",
) -> dict:
    """Send an HTML email via SMTP. Returns a status dict."""
    from app.config import settings

    host = smtp_host or settings.SMTP_HOST
    port = smtp_port or settings.SMTP_PORT
    username = smtp_username or settings.SMTP_USERNAME
    password = smtp_password or settings.SMTP_PASSWORD
    from_email = sender_email or settings.NOTIFICATION_FROM

    if not all([host, username, password, from_email]):
        return {"status": "failed", "error": "SMTP not configured"}

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{from_email}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}: {subject}")
        return {"status": "sent", "error": None}

    except smtplib.SMTPAuthenticationError:
        err = "SMTP authentication failed — check username/password"
        logger.error(err)
        return {"status": "failed", "error": err}
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        logger.error(f"Email send failed: {err}")
        return {"status": "failed", "error": err}


# ── Email Templates ───────────────────────────────────────────────────

def render_event_email(
    campaign_name: str,
    event_type: str,
    session_id: str,
    timestamp: str,
    browser_info: str = "",
    device_info: str = "",
    dashboard_url: str = "",
) -> tuple:
    """Render an event notification email. Returns (subject, html_body)."""
    event_labels = {
        "click": "Simulation Link Opened",
        "link_opened": "Simulation Link Opened",
        "page_view": "Training Page Displayed",
        "training_displayed": "Training Page Displayed",
        "location_consent": "Location Permission Response",
        "location_granted": "Location Permission Granted",
        "location_denied": "Location Permission Denied",
        "submit": "Training Interaction Completed",
        "training_completed": "Training Completed",
    }
    label = event_labels.get(event_type, event_type.replace("_", " ").title())

    badge_class = "click"
    if "submit" in event_type or "complete" in event_type:
        badge_class = "submit"
    elif "location" in event_type:
        badge_class = "location"

    subject = f"\U0001f6e1\ufe0f Security Awareness Campaign Activity: {label}"

    device_row = ""
    if browser_info:
        device_row = f"""
                <div class="field">
                    <div class="field-label">Browser / Device</div>
                    <div class="field-value">{browser_info} &middot; {device_info}</div>
                </div>"""

    dashboard_btn = ""
    if dashboard_url:
        dashboard_btn = f'<a href="{dashboard_url}" class="btn">Open Campaign Dashboard &rarr;</a>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f0f23;color:#e2e8f0;padding:0;margin:0}}
.container{{max-width:600px;margin:0 auto;padding:32px 20px}}
.header{{text-align:center;padding:24px;background:linear-gradient(135deg,#7c3aed,#6d28d9);border-radius:16px 16px 0 0}}
.header h1{{color:#fff;font-size:20px;margin:0}}
.header p{{color:rgba(255,255,255,.8);font-size:13px;margin-top:4px}}
.body{{background:#1a1a2e;border:1px solid rgba(255,255,255,.1);border-top:none;border-radius:0 0 16px 16px;padding:32px}}
.event-badge{{display:inline-block;padding:6px 16px;border-radius:20px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:20px}}
.event-badge.click{{background:rgba(6,182,212,.2);color:#06b6d4}}
.event-badge.submit{{background:rgba(16,185,129,.2);color:#10b981}}
.event-badge.location{{background:rgba(245,158,11,.2);color:#f59e0b}}
.field{{margin-bottom:16px}}
.field-label{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#64748b;margin-bottom:4px}}
.field-value{{font-size:15px;color:#f1f5f9}}
.divider{{border:none;border-top:1px solid rgba(255,255,255,.08);margin:20px 0}}
.btn{{display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;text-decoration:none;border-radius:10px;font-weight:600;font-size:14px;margin-top:16px}}
.footer{{text-align:center;padding:20px;color:#475569;font-size:11px}}
</style></head>
<body>
<div class="container">
    <div class="header">
        <h1>\U0001f6e1\ufe0f PhishGuard</h1>
        <p>Security Awareness Campaign Activity Detected</p>
    </div>
    <div class="body">
        <span class="event-badge {badge_class}">{label}</span>
        <div class="field"><div class="field-label">Campaign</div><div class="field-value">{campaign_name}</div></div>
        <div class="field"><div class="field-label">Event</div><div class="field-value">{label}</div></div>
        <div class="field"><div class="field-label">Time</div><div class="field-value">{timestamp}</div></div>
        <div class="field"><div class="field-label">Participant</div><div class="field-value">{session_id}</div></div>
        {device_row}
        <hr class="divider">
        <p style="color:#94a3b8;font-size:13px">
            This notification was automatically generated by your authorized
            security awareness simulation campaign.
        </p>
        {dashboard_btn}
    </div>
    <div class="footer">PhishGuard Security Awareness Platform<br>Automated notification from an authorized simulation.</div>
</div>
</body></html>"""

    return subject, html


def render_daily_summary_email(campaign_name: str, stats: dict, dashboard_url: str = "") -> tuple:
    """Render a daily campaign summary email. Returns (subject, html)."""
    subject = f"\U0001f4ca Daily Summary: {campaign_name}"

    dashboard_btn = ""
    if dashboard_url:
        dashboard_btn = f'<a href="{dashboard_url}" class="btn">Open Dashboard &rarr;</a>'

    def _stat(label, key):
        return f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{stats.get(key, 0)}</span></div>'

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<style>
body{{font-family:'Segoe UI',Arial,sans-serif;background:#0f0f23;color:#e2e8f0;padding:0;margin:0}}
.container{{max-width:600px;margin:0 auto;padding:32px 20px}}
.header{{text-align:center;padding:24px;background:linear-gradient(135deg,#06b6d4,#0891b2);border-radius:16px 16px 0 0}}
.header h1{{color:#fff;font-size:20px;margin:0}}
.body{{background:#1a1a2e;border:1px solid rgba(255,255,255,.1);border-top:none;border-radius:0 0 16px 16px;padding:32px}}
.stat-row{{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid rgba(255,255,255,.06)}}
.stat-label{{color:#94a3b8;font-size:14px}}
.stat-value{{color:#f1f5f9;font-weight:700;font-size:16px}}
.btn{{display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#06b6d4,#0891b2);color:#fff;text-decoration:none;border-radius:10px;font-weight:600;font-size:14px;margin-top:20px}}
.footer{{text-align:center;padding:20px;color:#475569;font-size:11px}}
</style></head>
<body>
<div class="container">
    <div class="header"><h1>\U0001f4ca Daily Campaign Summary</h1></div>
    <div class="body">
        <h2 style="font-size:18px;margin-bottom:20px">{campaign_name}</h2>
        {_stat("Links Generated", "total_targets")}
        {_stat("Links Opened", "clicked")}
        {_stat("Training Completed", "submitted")}
        {_stat("Click Rate", "click_rate")}
        {_stat("Events Today", "events_today")}
        {_stat("Notifications Sent", "notifications_sent")}
        {dashboard_btn}
    </div>
    <div class="footer">PhishGuard &middot; Automated daily summary</div>
</div>
</body></html>"""
    return subject, html


def render_test_email() -> tuple:
    """Render a test email to verify SMTP configuration."""
    subject = "\u2705 PhishGuard \u2014 SMTP Test Successful"
    html = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:#0f0f23;color:#e2e8f0;padding:40px">
<div style="max-width:500px;margin:0 auto;text-align:center;background:#1a1a2e;border:1px solid rgba(255,255,255,.1);border-radius:16px;padding:40px">
<div style="font-size:48px;margin-bottom:16px">\u2705</div>
<h1 style="font-size:22px;margin-bottom:8px">SMTP Configuration Verified</h1>
<p style="color:#94a3b8;font-size:14px">Your PhishGuard email notifications are working correctly.</p>
<hr style="border:none;border-top:1px solid rgba(255,255,255,.08);margin:24px 0">
<p style="color:#475569;font-size:11px">PhishGuard Security Awareness Platform</p>
</div></body></html>"""
    return subject, html
