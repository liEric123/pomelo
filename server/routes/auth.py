"""
Auth routes: login and current-user introspection.

POST /api/auth/login  — email + password, returns JWT
GET  /api/auth/me     — current user info
"""

from fastapi import APIRouter, Depends, Form, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import AuthUser
from services.auth_service import (
    create_token,
    get_current_user,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_session),
):
    """Exchange email + password for a JWT bearer token.

    Returns: {access_token, token_type, role, candidate_id, company_id}
    """
    user = db.exec(select(AuthUser).where(AuthUser.email == email)).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_token(user.id, user.role)
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "candidate_id": user.candidate_id,
        "company_id": user.company_id,
    }


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)):
    """Return the identity of the currently authenticated user."""
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "candidate_id": user.candidate_id,
        "company_id": user.company_id,
    }
