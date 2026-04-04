from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from database import get_session
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
):
    """Record a candidate or recruiter swipe on a role.

    Returns {"matched": true, "match_id": <id>} on mutual like,
    or {"matched": false} otherwise.
    """
    try:
        return _record_swipe(body.candidate_id, body.role_id, body.direction, body.side, session)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidSwipeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DuplicateSwipeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except SwipeLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
