from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlmodel import Session

from database import get_session
from services.hiring_coordinator import (
    register_candidate as _register_candidate,
    DuplicateEmailError,
    UnsupportedFileError,
    ResumeExtractionError,
    AIServiceError,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/register", status_code=201)
async def register_candidate(
    name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Register a new candidate by uploading their resume.

    Returns: {id, name, score, summary, top_skills}
    """
    file_bytes = await resume.read()
    try:
        return _register_candidate(name, email, file_bytes, resume.filename or "", session)
    except DuplicateEmailError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except UnsupportedFileError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ResumeExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.get("/{candidate_id}/feed")
def get_candidate_feed(
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Return a ranked list of roles for the candidate's swipe feed."""
    pass


@router.get("/{candidate_id}/matches")
def get_candidate_matches(
    candidate_id: int,
    session: Session = Depends(get_session),
):
    """Return all matches for a candidate with status and role info."""
    pass
