"""
PhishGuard Auth Router — Login, Register, Profile
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserResponse(BaseModel):
    id: int
    username: str
    created_at: str


# ── Register (first-time setup) ──────────────────────────────────────
@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """Create the admin account. Only works if no users exist yet."""
    existing = db.query(User).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account already exists. Use /login.",
        )

    if len(body.username) < 3 or len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be ≥3 chars, password ≥6 chars.",
        )

    user = User(
        username=body.username.strip().lower(),
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(AuditLog(user_id=user.id, action="register", details="Admin account created"))
    db.commit()

    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, username=user.username)


# ── Login ─────────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and receive a JWT token."""
    user = db.query(User).filter(User.username == body.username.strip().lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    db.add(AuditLog(user_id=user.id, action="login", details="Successful login"))
    db.commit()

    token = create_access_token({"sub": user.username})
    return TokenResponse(access_token=token, username=user.username)


# ── Profile ───────────────────────────────────────────────────────────
@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return {
        "id": user.id,
        "username": user.username,
        "created_at": str(user.created_at),
    }


# ── Check if setup is needed ─────────────────────────────────────────
@router.get("/status")
def auth_status(db: Session = Depends(get_db)):
    """Check if an admin account exists (for first-time setup)."""
    user_count = db.query(User).count()
    return {"setup_required": user_count == 0}
