"""
Sharingan JWT Authentication
Multi-tier support: python-jose -> PyJWT -> Pure Python Standard Library fallback.
Never crashes with ModuleNotFoundError on bare environments (Kali Linux, Ubuntu, Windows).
"""
import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

# ── JWT Implementation (jose -> pyjwt -> stdlib) ──────────────────────
try:
    from jose import JWTError, jwt
except ImportError:
    try:
        import jwt
        from jwt.exceptions import PyJWTError as JWTError
    except ImportError:
        class JWTError(Exception):
            """Fallback JWT Error when neither jose nor PyJWT is installed."""
            pass

        class _StdLibJWT:
            @staticmethod
            def _b64url_encode(data: bytes) -> str:
                return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

            @staticmethod
            def _b64url_decode(s: str) -> bytes:
                rem = len(s) % 4
                if rem:
                    s += "=" * (4 - rem)
                return base64.urlsafe_b64decode(s.encode("utf-8"))

            @classmethod
            def encode(cls, claims: dict, key: str, algorithm: str = "HS256") -> str:
                payload = {}
                for k, v in claims.items():
                    if isinstance(v, datetime):
                        payload[k] = int(v.timestamp())
                    else:
                        payload[k] = v
                header = {"alg": "HS256", "typ": "JWT"}
                h_b64 = cls._b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
                p_b64 = cls._b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
                msg = f"{h_b64}.{p_b64}".encode("utf-8")
                sig = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).digest()
                s_b64 = cls._b64url_encode(sig)
                return f"{h_b64}.{p_b64}.{s_b64}"

            @classmethod
            def decode(cls, token: str, key: str, algorithms: list = None) -> dict:
                try:
                    parts = token.split(".")
                    if len(parts) != 3:
                        raise JWTError("Invalid token segments")
                    h_b64, p_b64, s_b64 = parts
                    msg = f"{h_b64}.{p_b64}".encode("utf-8")
                    expected_sig = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).digest()
                    actual_sig = cls._b64url_decode(s_b64)
                    if not hmac.compare_digest(expected_sig, actual_sig):
                        raise JWTError("Signature verification failed")
                    payload = json.loads(cls._b64url_decode(p_b64).decode("utf-8"))
                    if "exp" in payload:
                        exp = payload["exp"]
                        now = datetime.now(timezone.utc).timestamp()
                        if now > exp:
                            raise JWTError("Token expired")
                    return payload
                except Exception as e:
                    if isinstance(e, JWTError):
                        raise
                    raise JWTError(str(e))

        jwt = _StdLibJWT()


# ── Password Hashing Implementation (bcrypt -> stdlib pbkdf2) ──────────
try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    """Hash a plaintext password securely."""
    pwd_bytes = password.encode("utf-8")
    if _HAS_BCRYPT:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")
    else:
        salt = os.urandom(16).hex()
        dk = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt.encode("utf-8"), 100000).hex()
        return f"pbkdf2_sha256${salt}${dk}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a hash."""
    try:
        if hashed.startswith("pbkdf2_sha256$"):
            _, salt, dk = hashed.split("$")
            calc = hashlib.pbkdf2_hmac("sha256", plain.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
            return hmac.compare_digest(dk, calc)
        elif _HAS_BCRYPT:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        return False
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency: extract and validate the current user from the JWT."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def get_optional_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Dependency: return current user or None (no error if unauthenticated)."""
    if token is None:
        return None
    try:
        return get_current_user(token, db)
    except HTTPException:
        return None

