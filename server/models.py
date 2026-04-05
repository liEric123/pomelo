"""
SQLModel table definitions for Pomelo.

Storage conventions:
  - Lists of strings (top_skills, keywords, questions): JSON column via sa.JSON
  - Resume embeddings: JSON column storing list[float] (pgvector not required for hackathon)
  - Timestamps: datetime with timezone=True, default to utcnow
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import sqlalchemy as sa
from sqlmodel import Field, Column, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UserRole(str, Enum):
    candidate = "candidate"
    recruiter = "recruiter"


class SwipeDirection(str, Enum):
    like = "like"
    pass_ = "pass"


class MatchStatus(str, Enum):
    pending = "pending"       # mutual interest, interview not started
    interviewing = "interviewing"
    completed = "completed"
    rejected = "rejected"


class MessageRole(str, Enum):
    system = "system"
    question = "question"     # AI-generated question sent to candidate
    answer = "answer"         # candidate's response
    follow_up = "follow_up"   # recruiter-injected or AI-suggested follow-up


# ---------------------------------------------------------------------------
# AuthUser
# ---------------------------------------------------------------------------

class AuthUser(SQLModel, table=True):
    """Login credentials and role for a demo user.

    Linked to either a Candidate or Company (recruiter) domain record.
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True)
    hashed_password: str
    role: UserRole                                    # "candidate" or "recruiter"

    # Exactly one of these should be set, matching the role
    candidate_id: Optional[int] = Field(default=None, foreign_key="candidate.id")
    company_id: Optional[int] = Field(default=None, foreign_key="company.id")

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# ---------------------------------------------------------------------------
# Company
# ---------------------------------------------------------------------------

class Company(SQLModel, table=True):
    """A company that posts roles and has recruiters."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class Role(SQLModel, table=True):
    """A job or internship role posted by a company."""

    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id")

    title: str
    description: str
    location: Optional[str] = None
    is_remote: bool = False

    # Scoring guidance: min/max resume score range to surface in feed
    min_score: float = 0.0
    max_score: float = 1.0

    # keywords used for matching and display tags, stored as JSON array
    keywords: list[str] = Field(default_factory=list, sa_column=Column(sa.JSON))

    # Ordered list of interview question strings for this role
    questions: list[str] = Field(default_factory=list, sa_column=Column(sa.JSON))

    # Max recruiter swipes per day for this role (enforced in coordinator)
    max_swipes_per_day: int = 20

    is_active: bool = True
    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------

class Candidate(SQLModel, table=True):
    """A job seeker with an uploaded resume."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    resume_text: Optional[str] = None   # raw extracted text

    # AI-generated structured fields populated after resume parsing
    summary: Optional[str] = None
    top_skills: list[str] = Field(default_factory=list, sa_column=Column(sa.JSON))

    # Embedding of resume text for similarity scoring (list of floats)
    embedding: Optional[list[float]] = Field(default=None, sa_column=Column(sa.JSON))

    # Overall resume quality score (0–1), computed by resume_service
    resume_score: Optional[float] = None

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# ---------------------------------------------------------------------------
# Swipe
# ---------------------------------------------------------------------------

class Swipe(SQLModel, table=True):
    """Records a candidate's like/pass on a role, and a company's like/pass on a candidate."""

    __table_args__ = (
        sa.UniqueConstraint("candidate_id", "role_id", name="uq_swipe_candidate_role"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidate.id")
    role_id: int = Field(foreign_key="role.id")

    # candidate swipe: like or pass
    candidate_direction: Optional[SwipeDirection] = None
    candidate_swiped_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )

    # recruiter swipe: like or pass on the candidate for this role
    recruiter_direction: Optional[SwipeDirection] = None
    recruiter_swiped_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )

    # recruiter keyword screening result (optional pre-swipe step)
    keyword_score: Optional[float] = None          # 0–1 score from keyword_match prompt
    keyword_reasoning: Optional[str] = None        # recruiter-facing explanation
    keyword_approved: Optional[bool] = None        # approve_for_interview flag from Claude

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------

class Match(SQLModel, table=True):
    """Created when both candidate and recruiter swipe 'like' on each other."""

    __table_args__ = (
        sa.UniqueConstraint("candidate_id", "role_id", name="uq_match_candidate_role"),
        sa.UniqueConstraint("swipe_id", name="uq_match_swipe_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="candidate.id")
    role_id: int = Field(foreign_key="role.id")
    swipe_id: int = Field(foreign_key="swipe.id")

    status: MatchStatus = MatchStatus.pending

    # Populated after interview completes
    interview_summary: Optional[str] = None
    final_score: Optional[float] = None          # 0–1 overall interview score
    recommendation: Optional[str] = None         # e.g. "strong yes", "maybe", "no"

    matched_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(sa.DateTime(timezone=True), nullable=True),
    )


# ---------------------------------------------------------------------------
# InterviewMessage
# ---------------------------------------------------------------------------

class InterviewMessage(SQLModel, table=True):
    """A single turn in an interview session."""

    id: Optional[int] = Field(default=None, primary_key=True)
    match_id: int = Field(foreign_key="match.id")

    role: MessageRole
    content: str

    # Question index within the role's question set (null for follow-ups)
    question_index: Optional[int] = None

    # AI grading fields — populated after answer is received
    score: Optional[float] = None          # 0–1 answer quality score
    score_label: Optional[str] = None     # e.g. "strong", "adequate", "weak"
    flags: list[str] = Field(default_factory=list, sa_column=Column(sa.JSON))
    grade_reasoning: Optional[str] = None  # brief explanation for recruiter

    # Whether this was injected by a recruiter (vs. AI-generated or preset)
    recruiter_injected: bool = False

    created_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(sa.DateTime(timezone=True), nullable=False),
    )
