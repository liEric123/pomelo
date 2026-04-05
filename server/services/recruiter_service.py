"""Recruiter-facing role management helpers."""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import Company, Role


class RecruiterRoleValidationError(Exception):
    """Raised when recruiter-provided role inputs are invalid."""


class RecruiterCompanyNotFoundError(Exception):
    """Raised when a referenced company does not exist."""


def create_role(
    *,
    company_id: int,
    title: str,
    description: str,
    location: str | None,
    is_remote: bool,
    min_score: float,
    max_score: float,
    keywords: list[str],
    questions: list[str],
    session: Session,
) -> Role:
    """Create and persist a recruiter role."""
    normalized_title = title.strip()
    normalized_description = description.strip()
    normalized_location = location.strip() if location else None
    normalized_keywords = _normalize_text_list(keywords)
    normalized_questions = _normalize_text_list(questions)

    if company_id <= 0:
        raise RecruiterRoleValidationError("Company ID must be a positive integer.")
    if not normalized_title:
        raise RecruiterRoleValidationError("Role title is required.")
    if not normalized_description:
        raise RecruiterRoleValidationError("Role description is required.")
    if min_score < 0 or min_score > 1 or max_score < 0 or max_score > 1:
        raise RecruiterRoleValidationError("Min and max score must be between 0.0 and 1.0.")
    if min_score > max_score:
        raise RecruiterRoleValidationError("Min score cannot be greater than max score.")
    if len(normalized_questions) < 6:
        raise RecruiterRoleValidationError("At least 6 questions are required for each role.")

    company = session.get(Company, company_id)
    if not company:
        raise RecruiterCompanyNotFoundError(f"Company {company_id} not found.")

    role = Role(
        company_id=company_id,
        title=normalized_title,
        description=normalized_description,
        location=normalized_location,
        is_remote=is_remote,
        min_score=min_score,
        max_score=max_score,
        keywords=normalized_keywords,
        questions=normalized_questions,
    )

    session.add(role)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise RecruiterRoleValidationError(
            "We could not save that role. Please verify the company and try again."
        ) from exc
    session.refresh(role)
    return role


def list_roles(*, company_id: int, session: Session) -> list[Role]:
    """List active roles for a company, newest first."""
    if company_id <= 0:
        raise RecruiterRoleValidationError("Company ID must be a positive integer.")

    statement = (
        select(Role)
        .where(Role.company_id == company_id, Role.is_active == True)  # noqa: E712
        .order_by(Role.created_at.desc())
    )
    return list(session.exec(statement).all())


def _normalize_text_list(values: list[str]) -> list[str]:
    return [value.strip() for value in values if value.strip()]
