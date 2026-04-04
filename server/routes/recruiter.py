from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from typing import Optional

from database import get_session

router = APIRouter(prefix="/recruiter", tags=["recruiter"])


# --- Role management ---

class RoleCreate(BaseModel):
    company_id: int
    title: str
    description: str
    location: Optional[str] = None
    is_remote: bool = False
    min_score: float = 0.0
    max_score: float = 1.0
    keywords: list[str] = []
    questions: list[str] = []


@router.post("/roles")
def create_role(
    body: RoleCreate,
    session: Session = Depends(get_session),
):
    """Create a new role. keywords and questions are recruiter-defined."""
    pass


@router.get("/roles")
def list_roles(
    company_id: int,
    session: Session = Depends(get_session),
):
    """List all active roles for a company."""
    pass


# --- Candidate review ---

@router.get("/roles/{role_id}/candidates")
def get_role_candidates(
    role_id: int,
    session: Session = Depends(get_session),
):
    """Return all candidates who swiped like on this role, with scores.

    Used for the recruiter's candidate review queue before they swipe back.
    """
    pass


@router.post("/roles/{role_id}/candidates/{candidate_id}/swipe")
def recruiter_swipe(
    role_id: int,
    candidate_id: int,
    direction: str,  # "like" or "pass"
    session: Session = Depends(get_session),
):
    """Record a recruiter's like/pass on a candidate for a role.

    If candidate already liked → creates a Match.
    """
    pass


# --- Dashboard & comparison ---

@router.get("/dashboard/{role_id}")
def get_dashboard(
    role_id: int,
    session: Session = Depends(get_session),
):
    """Return completed interview summaries and scores for a role.

    Used for the recruiter dashboard after interviews are done.
    """
    pass


@router.get("/roles/{role_id}/compare")
def compare_candidates(
    role_id: int,
    keep_top_pct: float = 0.5,
    session: Session = Depends(get_session),
):
    """Rank all completed candidates for a role and return advance/reject split.

    Flow (comparison_service):
      1. Load completed matches for role
      2. Sum scores (resume + interview)
      3. Sort and apply cutoff
      4. Return ranked advance/reject lists
    """
    pass
