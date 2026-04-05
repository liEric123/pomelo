from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session
from typing import Optional

from database import get_session
from services.recruiter_service import (
    RecruiterCompanyNotFoundError,
    RecruiterRoleValidationError,
    create_role as _create_role,
    list_roles as _list_roles,
)

router = APIRouter(prefix="/recruiter", tags=["recruiter"])


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------

class RoleCreate(BaseModel):
    company_id: int
    title: str
    description: str
    location: Optional[str] = None
    is_remote: bool = False
    min_score: float = 0.0
    max_score: float = 1.0
    keywords: list[str] = Field(default_factory=list)
    questions: list[str] = Field(default_factory=list)


@router.post("/roles", status_code=201)
def create_role(
    body: RoleCreate,
    session: Session = Depends(get_session),
):
    """Create a new role.

    keywords: used for candidate feed matching.
    questions: recruiter-defined questions for the interview question set.

    Returns the created role with role_id.
    """

    try:
        return _create_role(
            company_id=body.company_id,
            title=body.title,
            description=body.description,
            location=body.location,
            is_remote=body.is_remote,
            min_score=body.min_score,
            max_score=body.max_score,
            keywords=body.keywords,
            questions=body.questions,
            session=session,
        )
    except RecruiterRoleValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RecruiterCompanyNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/roles")
def list_roles(
    company_id: int,
    session: Session = Depends(get_session),
):
    """List all active roles for a company.

    Returns role metadata including keywords, score range, and question count.
    """
    try:
        return _list_roles(company_id, session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ---------------------------------------------------------------------------
# Candidate review queue
# ---------------------------------------------------------------------------

@router.get("/roles/{role_id}/candidates")
def get_role_candidates(
    role_id: int,
    session: Session = Depends(get_session),
):
    """Return candidates who liked this role and are waiting for recruiter review.

    Sorted by resume_score descending. Only shows candidates the recruiter
    hasn't swiped on yet. Use POST .../swipe to act on each candidate.
    """
    try:
        return _get_role_candidates(role_id, session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/roles/{role_id}/candidates/{candidate_id}/keyword-filter")
def keyword_filter_candidate(
    role_id: int,
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Run AI keyword screening for a candidate against a role.

    The candidate must have already liked the role (must be in the review queue).
    Results are persisted on the swipe row — re-calling overwrites the previous result.

    Response: {candidate_id, role_id, keyword_score, reasoning, approve_for_interview}
    """
    try:
        return _screen_candidate_keywords(candidate_id, role_id, session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))


class RecruiterSwipeRequest(BaseModel):
    direction: str  # "like" or "pass"


@router.post("/roles/{role_id}/candidates/{candidate_id}/swipe")
def recruiter_swipe(
    role_id: int,
    candidate_id: int,
    body: RecruiterSwipeRequest,
    session: Session = Depends(get_session),
):
    """Record a recruiter's like or pass on a candidate for a role.

    A mutual like (candidate already liked) creates a Match and starts
    the interview pipeline.

    Returns {"matched": true, "match_id": <id>} on mutual like,
    or {"matched": false} otherwise.
    """
    try:
        return _record_swipe(candidate_id, role_id, body.direction, "recruiter", session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidSwipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateSwipeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SwipeLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))


# ---------------------------------------------------------------------------
# Active interviews
# ---------------------------------------------------------------------------

@router.get("/active-interviews")
def get_active_interviews(
    company_id: Optional[int] = None,
    session: Session = Depends(get_session),
):
    """Return all matches currently in the interviewing state.

    Pass company_id to scope to one company, or omit for all active interviews.

    Each item: {match_id, role_id, role_title, candidate_id, candidate_name,
                top_skills, matched_at}
    """
    return _get_active_interviews(session, company_id=company_id)


# ---------------------------------------------------------------------------
# Dashboard & comparison
# ---------------------------------------------------------------------------

@router.get("/dashboard/{role_id}")
def get_dashboard(
    role_id: int,
    session: Session = Depends(get_session),
):
    """Return the recruiter dashboard for a role.

    Response shape:
      {
        "role": { role metadata },
        "active": [ { match_id, candidate_id, name, resume_score_pct,
                      top_skills, matched_at, status } ],
        "completed": [ { match_id, candidate_id, name, resume_score_pct,
                         top_skills, matched_at, final_score,
                         recommendation, summary, completed_at } ]
      }

    active: pending + interviewing matches.
    completed: finished interviews with parsed summary payload.
    """
    try:
        return _get_role_dashboard(role_id, session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/roles/{role_id}/compare")
def compare_candidates(
    role_id: int,
    keep_top_pct: float = 0.5,
    session: Session = Depends(get_session),
):
    """Rank all completed candidates for a role and return advance/reject split.

    keep_top_pct: fraction to advance (0.0–1.0, default 0.5).

    Composite score = 0.4 * resume_score + 0.6 * interview_score.

    Response shape:
      {
        "advance": [ { candidate_id, name, total_score, rank, ... } ],
        "reject":  [ { candidate_id, name, total_score, rank, ... } ],
        "total": int,
        "cutoff": int
      }
    """
    if not (0.0 <= keep_top_pct <= 1.0):
        raise HTTPException(status_code=400, detail="keep_top_pct must be between 0.0 and 1.0.")
    try:
        return _compare_role_candidates(role_id, keep_top_pct, session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
