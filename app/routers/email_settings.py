"""
PhishGuard Email Settings Router — SMTP configuration CRUD & test
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, EmailConfig, User
from app.services.email_service import SMTP_PRESETS, send_email, render_test_email

router = APIRouter(prefix="/api/email", tags=["Email Settings"])


class EmailConfigCreate(BaseModel):
    smtp_provider: str = "custom"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    sender_email: str = ""
    sender_name: str = "PhishGuard"
    enabled: bool = True
    notify_on_click: bool = True
    notify_on_submit: bool = True
    notify_on_location: bool = False
    notify_daily_summary: bool = False


class EmailConfigResponse(BaseModel):
    id: int
    smtp_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    sender_email: str
    sender_name: str
    enabled: bool
    is_verified: bool
    notify_on_click: bool
    notify_on_submit: bool
    notify_on_location: bool
    notify_daily_summary: bool


# ── Get current config ────────────────────────────────────────────────
@router.get("/config")
def get_email_config(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Retrieve the admin's current email configuration (password is never returned)."""
    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user.id).first()
    if not cfg:
        return {"configured": False}

    return {
        "configured": True,
        "id": cfg.id,
        "smtp_provider": cfg.smtp_provider,
        "smtp_host": cfg.smtp_host,
        "smtp_port": cfg.smtp_port,
        "smtp_username": cfg.smtp_username,
        "sender_email": cfg.sender_email,
        "sender_name": cfg.sender_name,
        "enabled": cfg.enabled,
        "is_verified": cfg.is_verified,
        "notify_on_click": cfg.notify_on_click,
        "notify_on_submit": cfg.notify_on_submit,
        "notify_on_location": cfg.notify_on_location,
        "notify_daily_summary": cfg.notify_daily_summary,
    }


# ── Save / update config ─────────────────────────────────────────────
@router.post("/config")
def save_email_config(
    body: EmailConfigCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create or update SMTP email configuration."""
    # Apply provider presets
    if body.smtp_provider in SMTP_PRESETS and body.smtp_provider != "custom":
        preset = SMTP_PRESETS[body.smtp_provider]
        body.smtp_host = preset["host"]
        body.smtp_port = preset["port"]

    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user.id).first()
    if cfg:
        cfg.smtp_provider = body.smtp_provider
        cfg.smtp_host = body.smtp_host
        cfg.smtp_port = body.smtp_port
        cfg.smtp_username = body.smtp_username
        if body.smtp_password:  # Only update password if provided
            cfg.smtp_password_encrypted = body.smtp_password
        cfg.sender_email = body.sender_email
        cfg.sender_name = body.sender_name
        cfg.enabled = body.enabled
        cfg.notify_on_click = body.notify_on_click
        cfg.notify_on_submit = body.notify_on_submit
        cfg.notify_on_location = body.notify_on_location
        cfg.notify_daily_summary = body.notify_daily_summary
        cfg.is_verified = False  # Require re-verification
    else:
        cfg = EmailConfig(
            user_id=user.id,
            smtp_provider=body.smtp_provider,
            smtp_host=body.smtp_host,
            smtp_port=body.smtp_port,
            smtp_username=body.smtp_username,
            smtp_password_encrypted=body.smtp_password,
            sender_email=body.sender_email,
            sender_name=body.sender_name,
            enabled=body.enabled,
            is_verified=False,
            notify_on_click=body.notify_on_click,
            notify_on_submit=body.notify_on_submit,
            notify_on_location=body.notify_on_location,
            notify_daily_summary=body.notify_daily_summary,
        )
        db.add(cfg)

    db.add(AuditLog(
        user_id=user.id,
        action="email_config_saved",
        details=f"SMTP config updated: {body.smtp_provider} / {body.smtp_host}",
    ))
    db.commit()
    db.refresh(cfg)

    return {"status": "saved", "id": cfg.id}


# ── Send test email ──────────────────────────────────────────────────
@router.post("/test")
def send_test_email(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Send a test email to verify SMTP configuration."""
    cfg = db.query(EmailConfig).filter(EmailConfig.user_id == user.id).first()
    if not cfg:
        raise HTTPException(status_code=400, detail="Email not configured yet")

    subject, html = render_test_email()
    result = send_email(
        to_email=cfg.sender_email,
        subject=subject,
        html_body=html,
        smtp_host=cfg.smtp_host,
        smtp_port=cfg.smtp_port,
        smtp_username=cfg.smtp_username,
        smtp_password=cfg.smtp_password_encrypted,
        sender_email=cfg.sender_email,
        sender_name=cfg.sender_name,
    )

    if result["status"] == "sent":
        cfg.is_verified = True
        db.commit()

    db.add(AuditLog(
        user_id=user.id,
        action="email_test",
        details=f"Test email {result['status']}: {result.get('error', 'OK')}",
    ))
    db.commit()

    return result


# ── Get available SMTP providers ──────────────────────────────────────
@router.get("/providers")
def get_providers(user: User = Depends(get_current_user)):
    """List available SMTP provider presets."""
    return {
        name: {"host": p["host"], "port": p["port"]}
        for name, p in SMTP_PRESETS.items()
    }
