"""
PhishGuard URL Analyzer Router
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import AuditLog, URLScan, User
from app.services.url_scanner import analyze_url

router = APIRouter(prefix="/api/url", tags=["URL Analyzer"])


class URLAnalyzeRequest(BaseModel):
    url: str


# ── Analyze a URL ─────────────────────────────────────────────────────
@router.post("/analyze")
def scan_url(
    body: URLAnalyzeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Perform a comprehensive security analysis of a URL."""
    results = analyze_url(body.url)

    # Save scan to history
    scan = URLScan(
        url=body.url,
        results=results,
        risk_score=results.get("risk_score", 0),
        user_id=user.id,
    )
    db.add(scan)
    db.add(AuditLog(
        user_id=user.id,
        action="url_scanned",
        details=f"Scanned URL: {body.url} — Risk: {results.get('risk_score', 0)}/100",
    ))
    db.commit()
    db.refresh(scan)

    results["scan_id"] = scan.id
    return results


# ── Scan History ──────────────────────────────────────────────────────
@router.get("/history")
def scan_history(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the last 50 URL scans."""
    scans = (
        db.query(URLScan)
        .filter(URLScan.user_id == user.id)
        .order_by(URLScan.scan_date.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": s.id,
            "url": s.url,
            "risk_score": s.risk_score,
            "scan_date": str(s.scan_date),
            "risk_level": s.results.get("risk_level", "unknown") if s.results else "unknown",
        }
        for s in scans
    ]
