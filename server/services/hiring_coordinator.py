"""
Central workflow coordinator for the Pomelo hiring platform.

All multi-step business flows live here. Routes stay thin — they call
a coordinator function and map domain exceptions to HTTP responses.

Domain exceptions defined here are the only exceptions routes need to catch.
Low-level errors (ValueError, anthropic.APIError, json.JSONDecodeError, etc.)
are caught internally and re-raised as one of these domain types.
"""

import json
import random
from datetime import datetime, time, timezone

import anthropic
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import Candidate, Company, InterviewMessage, Match, MatchStatus, MessageRole, Role, Swipe, SwipeDirection
from utils.resume_parser import extract_text
from services.scoring_service import grade_resume
from services.resume_service import generate_skill_vector, zero_skill_vector
from services.matching_service import build_role_vector, cosine_similarity
from services.question_service import generate_simul_questions
import services.interview_session as session_mgr
import services.summary_service as summary_service


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


class NotFoundError(Exception):
    """Requested entity does not exist."""


class InvalidSwipeError(Exception):
    """Swipe direction or side value is invalid."""


class DuplicateSwipeError(Exception):
    """This side has already swiped on this role/candidate pair."""


class SwipeLimitError(Exception):
    """Daily swipe limit reached."""


class InvalidInterviewState(Exception):
    """Interview cannot proceed from its current state."""


CANDIDATE_DAILY_LIMIT = 5


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


# ---------------------------------------------------------------------------
# Swipe recording
# ---------------------------------------------------------------------------

def record_swipe(
    candidate_id: int,
    role_id: int,
    direction: str,
    side: str,
    session: Session,
) -> dict:
    """Record a candidate or recruiter swipe on a role.

    side: "candidate" or "recruiter"
    direction: "like" or "pass"

    Returns:
      {"matched": True, "match_id": <id>}  if mutual like creates a match
      {"matched": False}                    otherwise

    Raises:
      NotFoundError      — candidate or role not found
      InvalidSwipeError  — bad direction or side value
      DuplicateSwipeError — this side already swiped this pair
      SwipeLimitError    — daily limit reached
    """
    if side not in ("candidate", "recruiter"):
        raise InvalidSwipeError(f"Invalid side: '{side}'. Must be 'candidate' or 'recruiter'.")

    try:
        dir_enum = SwipeDirection(direction)
    except ValueError:
        raise InvalidSwipeError(f"Invalid direction: '{direction}'. Must be 'like' or 'pass'.")

    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found.")
    role = session.get(Role, role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found.")

    # find existing swipe row for this pair
    swipe = session.exec(
        select(Swipe).where(Swipe.candidate_id == candidate_id, Swipe.role_id == role_id)
    ).first()

    now = _utcnow()

    if side == "candidate":
        if _count_candidate_swipes_today(candidate_id, session) >= CANDIDATE_DAILY_LIMIT:
            raise SwipeLimitError(f"Candidate daily limit of {CANDIDATE_DAILY_LIMIT} swipes reached.")
        swipe = _save_swipe_side(
            swipe=swipe,
            candidate_id=candidate_id,
            role_id=role_id,
            side=side,
            direction=dir_enum,
            swiped_at=now,
            session=session,
        )
        if dir_enum == SwipeDirection.like and swipe.recruiter_direction == SwipeDirection.like:
            match = _create_or_get_match(swipe, session)
            return {"matched": True, "match_id": match.id}

    else:  # recruiter
        if _count_recruiter_swipes_today(role_id, session) >= role.max_swipes_per_day:
            raise SwipeLimitError(
                f"Recruiter daily limit of {role.max_swipes_per_day} swipes reached for this role."
            )
        swipe = _save_swipe_side(
            swipe=swipe,
            candidate_id=candidate_id,
            role_id=role_id,
            side=side,
            direction=dir_enum,
            swiped_at=now,
            session=session,
        )
        if dir_enum == SwipeDirection.like and swipe.candidate_direction == SwipeDirection.like:
            match = _create_or_get_match(swipe, session)
            return {"matched": True, "match_id": match.id}

    return {"matched": False}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today_start() -> datetime:
    """Midnight UTC today as a timezone-aware datetime."""
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


def _count_candidate_swipes_today(candidate_id: int, session: Session) -> int:
    return session.exec(
        select(func.count(Swipe.id)).where(
            Swipe.candidate_id == candidate_id,
            Swipe.candidate_swiped_at >= _today_start(),
        )
    ).one()


def _count_recruiter_swipes_today(role_id: int, session: Session) -> int:
    return session.exec(
        select(func.count(Swipe.id)).where(
            Swipe.role_id == role_id,
            Swipe.recruiter_swiped_at >= _today_start(),
        )
    ).one()


def _save_swipe_side(
    swipe: Swipe | None,
    candidate_id: int,
    role_id: int,
    side: str,
    direction: SwipeDirection,
    swiped_at: datetime,
    session: Session,
) -> Swipe:
    """Persist one side of a swipe, recovering from concurrent first-insert races."""
    direction_field = f"{side}_direction"
    timestamp_field = f"{side}_swiped_at"
    duplicate_message = (
        "Candidate already swiped on this role."
        if side == "candidate"
        else "Recruiter already swiped this candidate for this role."
    )

    if swipe and getattr(swipe, direction_field) is not None:
        raise DuplicateSwipeError(duplicate_message)

    if swipe is None:
        swipe = Swipe(candidate_id=candidate_id, role_id=role_id)
        session.add(swipe)

    setattr(swipe, direction_field, direction)
    setattr(swipe, timestamp_field, swiped_at)

    try:
        session.commit()
    except IntegrityError as e:
        session.rollback()
        swipe = session.exec(
            select(Swipe).where(Swipe.candidate_id == candidate_id, Swipe.role_id == role_id)
        ).first()
        if swipe is None:
            raise
        if getattr(swipe, direction_field) is not None:
            raise DuplicateSwipeError(duplicate_message) from e
        setattr(swipe, direction_field, direction)
        setattr(swipe, timestamp_field, swiped_at)
        try:
            session.commit()
        except IntegrityError as retry_error:
            session.rollback()
            swipe = session.exec(
                select(Swipe).where(Swipe.candidate_id == candidate_id, Swipe.role_id == role_id)
            ).first()
            if swipe is None:
                raise
            if getattr(swipe, direction_field) is not None:
                raise DuplicateSwipeError(duplicate_message) from retry_error
            raise

    session.refresh(swipe)
    return swipe


def _create_or_get_match(swipe: Swipe, session: Session) -> Match:
    """Create a Match row from a mutual-like swipe, or return the existing one."""
    existing = session.exec(
        select(Match).where(
            Match.candidate_id == swipe.candidate_id,
            Match.role_id == swipe.role_id,
        )
    ).first()
    if existing:
        return existing

    match = Match(
        candidate_id=swipe.candidate_id,
        role_id=swipe.role_id,
        swipe_id=swipe.id,
        status=MatchStatus.pending,
    )
    session.add(match)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.exec(
            select(Match).where(
                Match.candidate_id == swipe.candidate_id,
                Match.role_id == swipe.role_id,
            )
        ).first()
        if existing:
            return existing
        raise
    session.refresh(match)
    return match


# ---------------------------------------------------------------------------
# Candidate feed
# ---------------------------------------------------------------------------

def get_candidate_feed(candidate_id: int, session: Session) -> list[dict]:
    """Return up to 20 roles ranked by cosine similarity for a candidate.

    Filtering:
      - role must be active
      - candidate resume_score must fall within role.min_score / role.max_score
      - roles the candidate already swiped are excluded

    Ranking:
      - cosine similarity between candidate.embedding and role keyword vector
      - both vectors use the shared SKILL_VOCABULARY (see resume_service / matching_service)

    Raises:
      NotFoundError — candidate not found
    """
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found.")

    # roles already swiped by this candidate
    swiped_ids: set[int] = set(
        session.exec(
            select(Swipe.role_id).where(
                Swipe.candidate_id == candidate_id,
                Swipe.candidate_direction.is_not(None),
            )
        ).all()
    )

    roles = session.exec(select(Role).where(Role.is_active == True)).all()  # noqa: E712

    resume_score = candidate.resume_score or 0.0
    candidate_vec = candidate.embedding or zero_skill_vector()

    scored: list[dict] = []
    for role in roles:
        if role.id in swiped_ids:
            continue
        if not (role.min_score <= resume_score <= role.max_score):
            continue
        role_vec = build_role_vector(role.keywords)
        sim = cosine_similarity(candidate_vec, role_vec)
        scored.append({
            "role_id": role.id,
            "title": role.title,
            "company_id": role.company_id,
            "description": role.description,
            "location": role.location,
            "is_remote": role.is_remote,
            "keywords": role.keywords,
            "match_percent": round(sim * 100, 1),
        })

    scored.sort(key=lambda x: x["match_percent"], reverse=True)
    return scored[:20]


# ---------------------------------------------------------------------------
# Interview flow
# ---------------------------------------------------------------------------

def start_interview(match_id: int, db: Session) -> dict:
    """Load match context, generate questions, init in-memory session, return first question.

    Updates match.status to interviewing.
    Persists the first question as an InterviewMessage.

    Raises:
      NotFoundError         — match not found
      InvalidInterviewState — match already completed
    """
    match = db.get(Match, match_id)
    if not match:
        raise NotFoundError(f"Match {match_id} not found.")
    if match.status == MatchStatus.completed:
        raise InvalidInterviewState("Interview already completed.")

    # Reconnect: resume the existing in-memory session without regenerating questions
    # or inserting another first-question message.
    existing_sess = session_mgr.get_session(match_id)
    if existing_sess is not None:
        current_q = existing_sess.questions[existing_sess.current_index]
        return _question_payload(current_q, index=existing_sess.current_index)

    role = db.get(Role, match.role_id)
    candidate = db.get(Candidate, match.candidate_id)
    company = db.get(Company, role.company_id) if role else None
    company_name = company.name if company else "Company"

    questions = _generate_questions(role, candidate, company_name)

    # Mark match as active
    match.status = MatchStatus.interviewing
    db.add(match)

    # Persist first question message
    first_q = questions[0]
    msg = InterviewMessage(
        match_id=match_id,
        role=MessageRole.question,
        content=first_q["text"],
        question_index=0,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    # Init in-memory session
    session_mgr.create_session(
        match_id=match_id,
        role=role,
        candidate=candidate,
        company_name=company_name,
        questions=questions,
    )

    return _question_payload(first_q, index=0)


def complete_interview(match_id: int, db: Session) -> dict:
    """Generate final summary, update Match, clean up in-memory session.

    Returns the summary dict (from final_summary.md prompt).
    """
    sess = session_mgr.get_session(match_id)
    match = db.get(Match, match_id)
    if not match:
        raise NotFoundError(f"Match {match_id} not found.")

    role = db.get(Role, match.role_id)
    candidate = db.get(Candidate, match.candidate_id)
    company_name = sess.company_name if sess else "Company"

    # Load all persisted messages in order
    messages = db.exec(
        select(InterviewMessage)
        .where(InterviewMessage.match_id == match_id)
        .order_by(InterviewMessage.created_at)
    ).all()

    qa_list = _build_qa_list(messages, sess)
    interview_data = summary_service.build_interview_data(qa_list)
    time_stats = _build_time_stats(sess, qa_list)

    try:
        summary = summary_service.generate_summary(
            role_title=role.title if role else "Unknown Role",
            company_name=company_name,
            role_description=role.description if role else "",
            candidate_name=candidate.name if candidate else "Unknown",
            resume_score=int((candidate.resume_score or 0) * 100) if candidate else 0,
            interview_data=interview_data,
            time_stats=time_stats,
        )
    except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise AIServiceError(f"Summary generation failed: {e}") from e
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        raise AIServiceError(f"Summary response invalid: {e}") from e

    # Persist to Match
    now = _utcnow()
    match.status = MatchStatus.completed
    match.interview_summary = json.dumps(summary)
    match.final_score = summary.get("scores_weighted")
    match.recommendation = summary.get("verdict")
    match.completed_at = now
    db.add(match)
    db.commit()

    session_mgr.remove_session(match_id)
    return summary


def _generate_questions(role: Role, candidate: Candidate, company_name: str) -> list[dict]:
    """Select interview questions for the simulation session.

    Uses role.questions as the interviewer-selected set.
    Falls back to a sample from the behavioral question bank if role has none.
    """
    if role.questions:
        selected_set = "\n".join(f"- {q}" for q in role.questions)
    else:
        bank_path = _question_bank_path()
        with open(bank_path, encoding="utf-8") as f:
            bank = json.load(f)
        sample = random.sample(bank["questions"], min(8, len(bank["questions"])))
        selected_set = "\n".join(f"- {q['question']}" for q in sample)

    candidate_background = (
        f"{candidate.summary or 'No summary available.'}\n"
        f"Skills: {', '.join(candidate.top_skills or [])}"
    )

    return generate_simul_questions(
        role_title=role.title,
        company_name=company_name,
        role_description=role.description,
        keywords=", ".join(role.keywords or []),
        selected_question_set=selected_set,
        candidate_background=candidate_background,
    )


def _question_bank_path() -> str:
    import os
    return os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "data", "question_bank.json")
    )


def _question_payload(q: dict, index: int) -> dict:
    return {
        "id": q["id"],
        "index": index,
        "text": q["text"],
        "category": q["category"],
        "expected_signals": q.get("expected_signals", []),
        "max_seconds": session_mgr.MAX_SECONDS_PER_ANSWER,
    }


def _build_qa_list(messages: list, sess) -> list[dict]:
    """Pair question and answer messages into the structure expected by build_interview_data.

    Recruiter-injected follow-up Q&A is attached as nested fields on the preceding main
    QA item (follow_up_text / follow_up_answer / follow_up_score) so that
    summary_service.build_interview_data() can render it without KeyError.
    """
    qa_items: list[dict] = []
    pending_q: dict | None = None
    awaiting_followup_answer: bool = False

    questions_by_index: dict[int, dict] = {}
    if sess:
        for i, q in enumerate(sess.questions):
            questions_by_index[i] = q

    for msg in messages:
        if msg.role == MessageRole.question:
            q_info = questions_by_index.get(msg.question_index or 0, {})
            pending_q = {
                "category": q_info.get("category", "behavioral"),
                "question_text": msg.content,
                "candidate_answer": "",
                "score": 0.0,
                "flag": None,
                "follow_up": False,
            }
            awaiting_followup_answer = False

        elif msg.role == MessageRole.follow_up:
            if qa_items:
                # Attach to the last completed QA as a nested follow-up.
                qa_items[-1]["follow_up"] = True
                qa_items[-1]["follow_up_text"] = msg.content
                qa_items[-1]["follow_up_answer"] = ""
                qa_items[-1]["follow_up_score"] = 0.0
                awaiting_followup_answer = True
            # follow_up before any QA is dropped (shouldn't happen in practice)

        elif msg.role == MessageRole.answer:
            if awaiting_followup_answer and qa_items:
                qa_items[-1]["follow_up_answer"] = msg.content
                qa_items[-1]["follow_up_score"] = msg.score or 0.0
                awaiting_followup_answer = False
            elif pending_q is not None:
                pending_q["candidate_answer"] = msg.content
                pending_q["score"] = msg.score or 0.0
                pending_q["flag"] = msg.flags[0] if msg.flags else None
                qa_items.append(pending_q)
                pending_q = None

    return qa_items


def _build_time_stats(sess, qa_list: list[dict]) -> str:
    """Format timing data for the summary prompt."""
    times = (sess.elapsed_times if sess else []) or [0] * max(len(qa_list), 1)
    if not times:
        return "- No timing data available."
    avg = sum(times) / len(times)
    fastest_idx = times.index(min(times))
    slowest_idx = times.index(max(times))
    timed_out = sum(1 for t in times if t >= session_mgr.MAX_SECONDS_PER_ANSWER)
    return summary_service.build_time_stats(
        avg_seconds=avg,
        fastest=(fastest_idx + 1, times[fastest_idx]),
        slowest=(slowest_idx + 1, times[slowest_idx]),
        timed_out_count=timed_out,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

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
