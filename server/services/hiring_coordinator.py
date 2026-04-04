"""
Central workflow coordinator for the Pomelo hiring platform.

All multi-step business flows live here. Routes stay thin — they call
a coordinator function and map domain exceptions to HTTP responses.

Domain exceptions defined here are the only exceptions routes need to catch.
Low-level errors (ValueError, anthropic.APIError, json.JSONDecodeError, etc.)
are caught internally and re-raised as one of these domain types.
"""

import json

import anthropic
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import Candidate
from utils.resume_parser import extract_text
from services.scoring_service import grade_resume
from services.resume_service import generate_skill_vector, zero_skill_vector


# ---------------------------------------------------------------------------
# Domain exceptions — routes import and catch only these
# ---------------------------------------------------------------------------

class DuplicateEmailError(Exception):
    """Candidate with this email already exists."""


class UnsupportedFileError(Exception):
    """Resume file type is not supported."""


class ResumeExtractionError(Exception):
    """Resume text extraction failed or produced unusable content."""


class AIServiceError(Exception):
    """Claude API call failed or returned unparseable output."""


# ---------------------------------------------------------------------------
# Generic role context for registration-time grading (no role selected yet)
# ---------------------------------------------------------------------------

_GENERIC_ROLE = dict(
    role_title="Software Engineer",
    company_name="General Assessment",
    role_description="A general software engineering role.",
    keywords="",
)


# ---------------------------------------------------------------------------
# Candidate registration
# ---------------------------------------------------------------------------

def register_candidate(
    name: str,
    email: str,
    file_bytes: bytes,
    filename: str,
    session: Session,
) -> dict:
    """Orchestrate full candidate registration flow.

    Steps:
      1. Duplicate email check
      2. Resume text extraction
      3. Resume grading (BRS score, summary, top_skills)
      4. Skill vector generation
      5. Persist Candidate row
      6. Return {id, name, score, summary, top_skills}

    Raises:
      DuplicateEmailError  — email already in use
      UnsupportedFileError — file extension not supported
      ResumeExtractionError — extraction produced unusable text
      AIServiceError       — Claude call failed or returned invalid output
    """
    # 1. Duplicate check
    existing = session.exec(select(Candidate).where(Candidate.email == email)).first()
    if existing:
        raise DuplicateEmailError(f"Email already registered: {email}")

    # 2. Parse resume
    try:
        resume_text = extract_text(file_bytes, filename)
    except ValueError as e:
        raise UnsupportedFileError(str(e)) from e
    except RuntimeError as e:
        raise ResumeExtractionError(str(e)) from e

    # 3. Grade resume
    try:
        grade = grade_resume(resume_text=resume_text, **_GENERIC_ROLE)
        brs, summary, top_skills = _normalize_grade(grade)
    except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise AIServiceError(f"Resume grading API error: {e}") from e
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        raise AIServiceError(f"Resume grading returned invalid output: {e}") from e

    # 4. Skill vector (non-fatal: fall back to zero vector on any non-API failure)
    try:
        skill_vector = generate_skill_vector(resume_text, top_skills)
    except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise AIServiceError(f"Skill vector API error: {e}") from e
    except Exception:
        skill_vector = zero_skill_vector()

    # 5. Persist
    candidate = Candidate(
        name=name,
        email=email,
        resume_text=resume_text,
        summary=summary,
        top_skills=top_skills,
        resume_score=brs / 100.0,  # normalize BRS 1-100 → 0-1 for internal use
        embedding=skill_vector,
    )
    session.add(candidate)
    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise DuplicateEmailError(f"Email already registered: {email}") from e
    session.refresh(candidate)

    # 6. Return
    return {
        "id": candidate.id,
        "name": candidate.name,
        "score": brs,           # raw BRS (1-100) for frontend display
        "summary": summary,
        "top_skills": top_skills,
    }


def _normalize_grade(grade: dict) -> tuple[int, str, list[str]]:
    """Validate and normalize grading output into strongly-typed fields."""
    if not isinstance(grade, dict):
        raise TypeError("Grade response is not a JSON object.")

    missing = {"score", "summary", "top_skills"} - grade.keys()
    if missing:
        raise KeyError(f"Grade response missing fields: {missing}")

    summary = grade["summary"]
    if not isinstance(summary, str):
        raise TypeError("Grade response field 'summary' must be a string.")

    top_skills = grade["top_skills"]
    if not isinstance(top_skills, list) or not all(isinstance(skill, str) for skill in top_skills):
        raise TypeError("Grade response field 'top_skills' must be a list of strings.")

    brs = int(grade["score"])
    if not 0 <= brs <= 100:
        raise ValueError("Grade response field 'score' must be between 0 and 100.")

    return brs, summary, top_skills
