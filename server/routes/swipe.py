from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from database import get_session
from models import AuthUser
from services.auth_service import require_candidate
from services.hiring_coordinator import (
    record_swipe as _record_swipe,
    NotFoundError,
    InvalidSwipeError,
    DuplicateSwipeError,
    SwipeLimitError,
)

router = APIRouter(prefix="/swipes", tags=["swipes"])


class SwipeRequest(BaseModel):
    candidate_id: int
    role_id: int
    direction: str                              # "like" or "pass"
    side: Literal["candidate", "recruiter"] = "candidate"


@router.post("")
def record_swipe(
    body: SwipeRequest,
    session: Session = Depends(get_session),
    user: AuthUser = Depends(require_candidate),
):
    """Record a candidate swipe on a role.

    Returns {"matched": true, "match_id": <id>} on mutual like,
    or {"matched": false} otherwise.
    """
    if user.candidate_id != body.candidate_id:
        raise HTTPException(status_code=403, detail="Access denied.")
    if body.side != "candidate":
        raise HTTPException(status_code=400, detail="Candidate endpoint only supports candidate swipes.")
    try:
        return _record_swipe(body.candidate_id, body.role_id, body.direction, "candidate", session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidSwipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateSwipeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SwipeLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
