from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from database import get_session

router = APIRouter(prefix="/swipes", tags=["swipes"])


class SwipeRequest(BaseModel):
    candidate_id: int
    role_id: int
    direction: str  # "like" or "pass"


@router.post("")
def record_swipe(
    body: SwipeRequest,
    session: Session = Depends(get_session),
):
    """Record a candidate's swipe on a role.

    Flow (coordinator):
      1. Validate direction and check for duplicate swipe
      2. Persist swipe
      3. Check for mutual interest (recruiter has already liked)
      4. If mutual → create Match, return match_id
      5. Otherwise return swipe recorded, no match
    """
    pass
