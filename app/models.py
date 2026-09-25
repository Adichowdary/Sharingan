"""
PhishGuard Database Models (v2 — with email, notifications, templates)
"""
import secrets
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    Float, Text, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


def _gen_token():
    return secrets.token_urlsafe(32)


def _gen_session_id():
    return f"Session-{secrets.token_hex(3).upper()}"


# ── Admin Users ───────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    campaigns = relationship("Campaign", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")
    email_configs = relationship("EmailConfig", back_populates="user")


# ── Campaigns ─────────────────────────────────────────────────────────
class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="active")
    campaign_type = Column(String(50), default="awareness")
    created_at = Column(DateTime, default=_utcnow)
    expires_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Notification settings
    notification_email = Column(String(255), default="")
    notification_frequency = Column(String(20), default="immediate")  # immediate, every_5_min, daily
    notifications_enabled = Column(Boolean, default=False)

    # Authorization confirmation
    authorized_simulation = Column(Boolean, default=False)
    redirect_url = Column(String(500), default="")

    owner = relationship("User", back_populates="campaigns")
    targets = relationship(
        "CampaignTarget", back_populates="campaign", cascade="all, delete-orphan"
    )
    events = relationship(
        "Event", back_populates="campaign", cascade="all, delete-orphan"
    )
    notification_logs = relationship(
        "NotificationLog", back_populates="campaign", cascade="all, delete-orphan"
    )


# ── Campaign Targets ─────────────────────────────────────────────────
class CampaignTarget(Base):
    __tablename__ = "campaign_targets"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    email = Column(String(255), default="")
    name = Column(String(200), default="")
    token = Column(String(64), unique=True, index=True, default=_gen_token)
    clicked = Column(Boolean, default=False)
    submitted = Column(Boolean, default=False)
    click_time = Column(DateTime, nullable=True)

    campaign = relationship("Campaign", back_populates="targets")
    events = relationship(
        "Event", back_populates="target", cascade="all, delete-orphan"
    )


# ── Events ────────────────────────────────────────────────────────────
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    target_id = Column(Integer, ForeignKey("campaign_targets.id"), nullable=True)
    event_type = Column(String(50))  # click, submit, location_consent, page_view
    session_id = Column(String(32), default=_gen_session_id)
    ip_address = Column(String(45), default="")
    user_agent = Column(Text, default="")
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    location_consent = Column(Boolean, default=False)
    browser_info = Column(JSON, nullable=True)

    # Parsed UA fields
    browser_family = Column(String(50), default="")
    os_family = Column(String(50), default="")
    device_category = Column(String(20), default="")

    timestamp = Column(DateTime, default=_utcnow)
    metadata_json = Column(JSON, nullable=True)

    campaign = relationship("Campaign", back_populates="events")
    target = relationship("CampaignTarget", back_populates="events")


# ── URL Scans ─────────────────────────────────────────────────────────
class URLScan(Base):
    __tablename__ = "url_scans"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(2048), nullable=False)
    scan_date = Column(DateTime, default=_utcnow)
    results = Column(JSON, nullable=True)
    risk_score = Column(Integer, default=0)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


# ── Email Configuration ──────────────────────────────────────────────
class EmailConfig(Base):
    __tablename__ = "email_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    smtp_provider = Column(String(50), default="custom")
    smtp_host = Column(String(255), default="")
    smtp_port = Column(Integer, default=587)
    smtp_username = Column(String(255), default="")
    smtp_password_encrypted = Column(String(512), default="")
    sender_email = Column(String(255), default="")
    sender_name = Column(String(100), default="PhishGuard")
    is_verified = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    # Per-event-type notification toggles
    notify_on_click = Column(Boolean, default=True)
    notify_on_submit = Column(Boolean, default=True)
    notify_on_location = Column(Boolean, default=False)
    notify_daily_summary = Column(Boolean, default=False)

    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="email_configs")


# ── Notification Log ─────────────────────────────────────────────────
class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True)
    event_id = Column(Integer, nullable=True)
    notification_type = Column(String(50), default="")
    recipient_email = Column(String(255), default="")
    subject = Column(String(500), default="")
    status = Column(String(20), default="pending")  # pending, sent, failed
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    campaign = relationship("Campaign", back_populates="notification_logs")


# ── Email Templates ──────────────────────────────────────────────────
class EmailTemplate(Base):
    __tablename__ = "email_templates"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String(100), default="")
    template_type = Column(String(50), default="")  # link_opened, training_completed, etc.
    subject = Column(String(500), default="")
    body_html = Column(Text, default="")
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


# ── Audit Logs ────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, default="")
    ip_address = Column(String(45), default="")
    timestamp = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="audit_logs")
