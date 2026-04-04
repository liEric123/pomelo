from fastapi import APIRouter, Depends, UploadFile, File
from sqlmodel import Session

from database import get_session

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/register")
async def register_candidate(
    name: str,
    email: str,
    resume: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Register a new candidate and process their resume.

    Flow (coordinator):
      1. Parse resume file → raw text
      2. Grade resume → BRS score, summary, top_skills
      3. Compute embedding for feed matching
      4. Persist Candidate row
      5. Return candidate id + score
    """
    pass


@router.get("/{candidate_id}/feed")
def get_candidate_feed(
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Return a ranked list of roles for the candidate's swipe feed.

    Flow (coordinator):
      1. Load candidate + embedding
      2. Fetch active roles not yet swiped
      3. Score each role via keyword_match
      4. Filter by role min/max score range
      5. Return ranked feed items
    """
    pass


@router.get("/{candidate_id}/matches")
def get_candidate_matches(
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Return all matches for a candidate with status and role info."""
    pass
