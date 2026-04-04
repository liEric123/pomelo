import json

import anthropic
from fastapi import APIRouter, Depends, Form, UploadFile, File, HTTPException
from sqlmodel import Session, select

from database import get_session
from models import Candidate
from utils.resume_parser import extract_text
from services.scoring_service import grade_resume
from services.resume_service import generate_skill_vector, zero_skill_vector

router = APIRouter(prefix="/candidates", tags=["candidates"])

# Generic role context used when grading a resume at registration
# (no specific role yet — produces a role-agnostic BRS)
_GENERIC_ROLE = dict(
    role_title="Software Engineer",
    company_name="General Assessment",
    role_description="A general software engineering role.",
    keywords="",
)


@router.post("/register", status_code=201)
async def register_candidate(
    name: str = Form(...),
    email: str = Form(...),
    resume: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Register a new candidate by uploading their resume.

    Accepts multipart/form-data with name, email, and a resume file (PDF/DOCX/TXT).

    Returns: {id, name, score, summary, top_skills}

    Error codes:
      400 — unsupported file type
      409 — email already registered
      422 — resume text extraction failed or produced unusable content
      502 — Claude API call failed or returned invalid output
    """
    # --- duplicate check ---
    existing = session.exec(select(Candidate).where(Candidate.email == email)).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered.")

    # --- parse resume ---
    file_bytes = await resume.read()
    filename = resume.filename or ""

    try:
        resume_text = extract_text(file_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # --- grade resume via Claude ---
    try:
        grade = grade_resume(resume_text=resume_text, **_GENERIC_ROLE)
        _validate_grade(grade)
    except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise HTTPException(status_code=502, detail=f"Resume grading API error: {e}")
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise HTTPException(status_code=502, detail=f"Resume grading returned invalid output: {e}")

    top_skills: list[str] = grade.get("top_skills", [])
    summary: str = grade.get("summary", "")
    brs: int = int(grade.get("score", 0))

    # --- generate skill vector ---
    try:
        skill_vector = generate_skill_vector(resume_text, top_skills)
    except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise HTTPException(status_code=502, detail=f"Skill vector API error: {e}")
    except Exception:
        # non-critical: fall back to zero vector rather than failing registration
        skill_vector = zero_skill_vector()

    # --- persist candidate ---
    candidate = Candidate(
        name=name,
        email=email,
        resume_text=resume_text,
        summary=summary,
        top_skills=top_skills,
        resume_score=brs / 100.0,   # normalize BRS 1-100 → 0-1 for internal use
        embedding=skill_vector,
    )
    session.add(candidate)
    session.commit()
    session.refresh(candidate)

    return {
        "id": candidate.id,
        "name": candidate.name,
        "score": brs,               # return raw BRS (1-100) to frontend
        "summary": summary,
        "top_skills": top_skills,
    }


def _validate_grade(grade: dict) -> None:
    """Raise TypeError if the grading response is missing required fields."""
    if not isinstance(grade, dict):
        raise TypeError("Grade response is not a JSON object.")
    if "score" not in grade or "summary" not in grade or "top_skills" not in grade:
        raise KeyError(f"Grade response missing required fields: {list(grade.keys())}")


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
