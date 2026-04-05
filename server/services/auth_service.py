"""
JWT authentication and FastAPI dependency helpers.

Supports token delivery via:
  - Authorization: Bearer <token>  (HTTP endpoints)
  - ?token=<token> query param     (WebSocket / SSE endpoints)
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select

from database import get_session
from models import AuthUser, Match, Role, UserRole

SECRET_KEY = os.getenv("AUTH_SECRET", "dev-secret-change-in-prod")
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
DEFAULT_CANDIDATE_PASSWORD = os.getenv("AUTH_DEFAULT_CANDIDATE_PASSWORD", "pomelo2026")

_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
_bearer = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return _pwd.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def create_token(user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": str(user_id), "role": role, "exp": expire},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


def default_candidate_password() -> str:
    return DEFAULT_CANDIDATE_PASSWORD


def get_user_from_token(raw_token: str, db: Session) -> AuthUser:
    payload = _decode_token(raw_token)
    user_id = int(payload["sub"])
    user = db.get(AuthUser, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    token_query: Optional[str] = Query(None, alias="token"),
    db: Session = Depends(get_session),
) -> AuthUser:
    """Accept token from Bearer header or ?token= query param."""
    raw_token: Optional[str] = None
    if credentials:
        raw_token = credentials.credentials
    elif token_query:
        raw_token = token_query

    if not raw_token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return get_user_from_token(raw_token, db)


def require_candidate(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != UserRole.candidate:
        raise HTTPException(status_code=403, detail="Candidate access required.")
    return user


def require_recruiter(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != UserRole.recruiter:
        raise HTTPException(status_code=403, detail="Recruiter access required.")
    return user


def ensure_recruiter_role_access(role_id: int, user: AuthUser, db: Session) -> Role:
    role = db.get(Role, role_id)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role {role_id} not found.")
    if user.company_id != role.company_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return role


def ensure_candidate_match_access(match_id: int, user: AuthUser, db: Session) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found.")
    if user.role != UserRole.candidate or user.candidate_id != match.candidate_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return match


def ensure_recruiter_match_access(match_id: int, user: AuthUser, db: Session) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise HTTPException(status_code=404, detail=f"Match {match_id} not found.")
    role = db.get(Role, match.role_id)
    if role is None:
        raise HTTPException(status_code=404, detail=f"Role {match.role_id} not found.")
    if user.role != UserRole.recruiter or user.company_id != role.company_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return match
