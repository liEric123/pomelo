"""
Central workflow coordinator for the Pomelo hiring platform.

All multi-step business flows live here. Routes stay thin — they call
a coordinator function and map domain exceptions to HTTP responses.

Domain exceptions defined here are the only exceptions routes need to catch.
Low-level errors (ValueError, anthropic.APIError, json.JSONDecodeError, etc.)
are caught internally and re-raised as one of these domain types.
"""

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime, time, timezone

import anthropic
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from models import AuthUser, Candidate, Company, InterviewMessage, Match, MatchStatus, MessageRole, Role, Swipe, SwipeDirection, UserRole
import services.comparison_service as comparison_service
from services.auth_service import default_candidate_password, hash_password
from utils.resume_parser import extract_text
from services.scoring_service import grade_resume, keyword_match as _keyword_match
from services.resume_service import generate_skill_vector, zero_skill_vector
from services.matching_service import build_role_vector, cosine_similarity
from services.grading_service import grade_answer
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
    password: str | None,
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
    try:
        session.add(candidate)
        session.flush()

        auth_password = password.strip() if password and password.strip() else default_candidate_password()
        auth_user = AuthUser(
            email=email,
            hashed_password=hash_password(auth_password),
            role=UserRole.candidate,
            candidate_id=candidate.id,
        )
        session.add(auth_user)
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
        if existing_sess.awaiting_injected:
            return {
                "type": "follow_up",
                "text": existing_sess.current_injected_question,
                "emit_transcript": False,
            }
        current_q = existing_sess.questions[existing_sess.current_index]
        return {
            "type": "question",
            **_question_payload(current_q, index=existing_sess.current_index),
            "emit_transcript": False,
        }

    role = db.get(Role, match.role_id)
    if not role:
        raise NotFoundError(f"Role {match.role_id} not found.")
    candidate = db.get(Candidate, match.candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {match.candidate_id} not found.")
    company = db.get(Company, role.company_id)
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

    return {
        "type": "question",
        **_question_payload(first_q, index=0),
        "emit_transcript": True,
    }


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

    _persist_completed_match(match, summary, db)
    session_mgr.remove_session(match_id)
    return summary


# ---------------------------------------------------------------------------
# Per-answer processing (called from WebSocket route)
# ---------------------------------------------------------------------------

@dataclass
class AnswerResult:
    """What the WebSocket route should send after one answer is processed.

    next_action: "follow_up" | "question" | "complete"
    graded_question and grade are passed back so the route can fire the
    background follow-up suggestion task without re-reading session state.
    """
    next_action: str
    follow_up_text: str | None = None
    next_question: dict | None = None
    summary: dict | None = None
    graded_question: dict = field(default_factory=dict)
    grade: dict = field(default_factory=dict)


async def process_interview_answer(
    match_id: int,
    answer_text: str,
    elapsed: int,
    db: Session,
) -> AnswerResult:
    """Process one candidate answer end-to-end.

    Steps:
      1. Determine which question is being answered (scheduled or injected)
      2. Persist the answer message
      3. Grade the answer (async-wrapped sync AI call)
      4. Update the answer message with grade fields
      5. Record elapsed time in session state
      6. Emit transcript and score events to the recruiter SSE stream
      7. Decide and return what to send back to the candidate:
           - An injected follow-up question from the queue
           - The next scheduled question
           - Interview completion (triggers summary generation)

    Raises:
      InvalidInterviewState — no active session for this match
    """
    sess = session_mgr.get_session(match_id)
    if sess is None:
        raise InvalidInterviewState(f"No active session for match {match_id}.")

    # Determine which question is being answered
    if sess.awaiting_injected:
        current_q: dict = {
            "id": "injected",
            "text": sess.current_injected_question,
            "category": "follow_up",
            "expected_signals": [],
        }
        q_index = None
    else:
        q_index = sess.current_index
        current_q = sess.questions[q_index]

    # Persist answer
    answer_msg = InterviewMessage(
        match_id=match_id,
        role=MessageRole.answer,
        content=answer_text,
        question_index=q_index,
        recruiter_injected=sess.awaiting_injected,
    )
    db.add(answer_msg)
    db.commit()
    db.refresh(answer_msg)

    # Grade (synchronous AI call, run in thread to avoid blocking the event loop)
    role = sess.role
    try:
        grade = await asyncio.to_thread(
            grade_answer,
            role_title=role.title,
            company_name=sess.company_name,
            category=current_q["category"],
            question_text=current_q["text"] or answer_text,
            expected_signals=", ".join(current_q.get("expected_signals") or []),
            candidate_answer=answer_text,
            seconds=elapsed,
            max_seconds=session_mgr.MAX_SECONDS_PER_ANSWER,
        )
    except Exception as e:
        grade = {"score": 0.0, "rationale": str(e), "flag": None, "recruiter_hint": "Grading failed."}

    # Persist grade fields onto the answer message
    answer_msg.score = grade.get("score", 0.0)
    answer_msg.score_label = _score_label(grade.get("score", 0.0))
    answer_msg.flags = [grade["flag"]] if grade.get("flag") else []
    answer_msg.grade_reasoning = grade.get("rationale")
    db.add(answer_msg)
    db.commit()

    # Record timing
    sess.elapsed_times.append(elapsed)

    # Emit to recruiter SSE
    await session_mgr.emit_event(match_id, "transcript", {
        "question_id": current_q["id"], "text": answer_text, "role": "answer",
    })
    await session_mgr.emit_event(match_id, "score", {
        "question_id": current_q["id"],
        "score": grade.get("score"),
        "flag": grade.get("flag"),
        "recruiter_hint": grade.get("recruiter_hint"),
    })

    # Clear injected-answer flag before deciding next step
    if sess.awaiting_injected:
        sess.awaiting_injected = False

    # Injected question takes priority over scheduled advancement
    if sess.inject_queue:
        injected_text = sess.inject_queue.popleft()
        inject_msg = InterviewMessage(
            match_id=match_id,
            role=MessageRole.follow_up,
            content=injected_text,
            recruiter_injected=True,
        )
        db.add(inject_msg)
        db.commit()
        sess.awaiting_injected = True
        sess.current_injected_question = injected_text
        await session_mgr.emit_event(match_id, "transcript", {
            "question_id": None, "text": injected_text, "role": "follow_up",
        })
        return AnswerResult(
            next_action="follow_up",
            follow_up_text=injected_text,
            graded_question=current_q,
            grade=grade,
        )

    # Advance to next scheduled question
    sess.current_index += 1

    if sess.current_index < len(sess.questions):
        next_q = sess.questions[sess.current_index]
        q_msg = InterviewMessage(
            match_id=match_id,
            role=MessageRole.question,
            content=next_q["text"],
            question_index=sess.current_index,
        )
        db.add(q_msg)
        db.commit()
        await session_mgr.emit_event(match_id, "transcript", {
            "question_id": next_q["id"], "text": next_q["text"], "role": "question",
        })
        return AnswerResult(
            next_action="question",
            next_question=_question_payload(next_q, sess.current_index),
            graded_question=current_q,
            grade=grade,
        )

    # All questions answered — generate summary and complete
    sess.is_complete = True
    try:
        summary = await asyncio.to_thread(complete_interview, match_id, db)
    except AIServiceError:
        summary = {
            "verdict": "MAYBE",
            "one_liner": "Summary generation failed.",
            "scores_weighted": None,
        }
        match = db.get(Match, match_id)
        if match is not None:
            _persist_completed_match(match, summary, db)
        session_mgr.remove_session(match_id)
    await session_mgr.emit_event(match_id, "interview_complete", {"summary": summary})
    return AnswerResult(
        next_action="complete",
        summary=summary,
        graded_question=current_q,
        grade=grade,
    )


def inject_recruiter_question(match_id: int, question_text: str) -> None:
    """Queue a recruiter-injected follow-up question for the active interview.

    Raises:
      NotFoundError — no active (non-completed) session for this match
    """
    ok = session_mgr.push_inject(match_id, question_text)
    if not ok:
        raise NotFoundError(f"No active interview session for match {match_id}.")


def _score_label(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.5:
        return "adequate"
    return "weak"


def _persist_completed_match(match: Match, summary: dict, db: Session) -> None:
    """Persist final interview results onto a match and mark it completed."""
    now = _utcnow()
    match.status = MatchStatus.completed
    match.interview_summary = json.dumps(summary)
    match.final_score = summary.get("scores_weighted")
    match.recommendation = summary.get("verdict")
    match.completed_at = now
    db.add(match)
    db.commit()


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
        sample = random.sample(bank["questions"], min(4, len(bank["questions"])))
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

# ---------------------------------------------------------------------------
# Candidate matches
# ---------------------------------------------------------------------------

def get_candidate_matches(candidate_id: int, session: Session) -> list[dict]:
    """Return all matches for a candidate, newest first.

    Each item includes role + company context and interview outcome when available.

    Raises:
      NotFoundError — candidate not found
    """
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found.")

    matches = session.exec(
        select(Match)
        .where(Match.candidate_id == candidate_id)
        .order_by(Match.matched_at.desc())
    ).all()

    result = []
    for match in matches:
        role = session.get(Role, match.role_id)
        company = session.get(Company, role.company_id) if role else None
        result.append({
            "match_id": match.id,
            "role_id": match.role_id,
            "role_title": role.title if role else None,
            "company_name": company.name if company else None,
            "status": match.status,
            "matched_at": match.matched_at.isoformat(),
            "completed_at": match.completed_at.isoformat() if match.completed_at else None,
            "final_score": match.final_score,
            "recommendation": match.recommendation,
        })
    return result


# ---------------------------------------------------------------------------
# Role management
# ---------------------------------------------------------------------------

def create_role(
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
) -> dict:
    """Create a new role for a company.

    Raises:
      NotFoundError — company not found
    """
    company = session.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    role = Role(
        company_id=company_id,
        title=title,
        description=description,
        location=location,
        is_remote=is_remote,
        min_score=min_score,
        max_score=max_score,
        keywords=keywords,
        questions=questions,
    )
    session.add(role)
    session.commit()
    session.refresh(role)
    return _role_dict(role, company.name)


def list_roles(company_id: int, session: Session) -> list[dict]:
    """Return all active roles for a company, newest first.

    Raises:
      NotFoundError — company not found
    """
    company = session.get(Company, company_id)
    if not company:
        raise NotFoundError(f"Company {company_id} not found.")

    roles = session.exec(
        select(Role)
        .where(Role.company_id == company_id, Role.is_active == True)  # noqa: E712
        .order_by(Role.created_at.desc())
    ).all()
    return [_role_dict(r, company.name) for r in roles]


def _role_dict(role: Role, company_name: str) -> dict:
    return {
        "role_id": role.id,
        "company_id": role.company_id,
        "company_name": company_name,
        "title": role.title,
        "description": role.description,
        "location": role.location,
        "is_remote": role.is_remote,
        "min_score": role.min_score,
        "max_score": role.max_score,
        "keywords": role.keywords,
        "questions": role.questions,
        "is_active": role.is_active,
        "created_at": role.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Recruiter review queue
# ---------------------------------------------------------------------------

def get_role_candidates(role_id: int, session: Session) -> list[dict]:
    """Return candidates who liked this role and haven't been reviewed yet.

    Sorted by resume_score descending so the best matches appear first.
    This is the recruiter's candidate review queue before they swipe back.

    Raises:
      NotFoundError — role not found
    """
    role = session.get(Role, role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found.")

    pending_swipes = session.exec(
        select(Swipe).where(
            Swipe.role_id == role_id,
            Swipe.candidate_direction == SwipeDirection.like,
            Swipe.recruiter_direction.is_(None),
        )
    ).all()

    result = []
    for swipe in pending_swipes:
        candidate = session.get(Candidate, swipe.candidate_id)
        if not candidate:
            continue
        result.append({
            "candidate_id": candidate.id,
            "name": candidate.name,
            "email": candidate.email,
            "resume_score": candidate.resume_score,
            "resume_score_pct": round((candidate.resume_score or 0.0) * 100, 1),
            "summary": candidate.summary,
            "top_skills": candidate.top_skills,
            "swiped_at": swipe.candidate_swiped_at.isoformat() if swipe.candidate_swiped_at else None,
            # keyword screening result — null until POST .../keyword-filter is called
            "keyword_score": swipe.keyword_score,
            "keyword_reasoning": swipe.keyword_reasoning,
            "keyword_approved": swipe.keyword_approved,
        })

    result.sort(key=lambda x: x["resume_score"] or 0.0, reverse=True)
    return result


# ---------------------------------------------------------------------------
# Keyword screening
# ---------------------------------------------------------------------------

def screen_candidate_keywords(candidate_id: int, role_id: int, session: Session) -> dict:
    """Run keyword-match screening for a candidate against a role.

    Requires the candidate to have already swiped like on the role (they must
    be in the review queue). Persists the result on the Swipe row so the
    recruiter can see it alongside the candidate card without re-running.

    Returns {candidate_id, role_id, keyword_score, reasoning, approve_for_interview}.

    Raises:
      NotFoundError  — candidate, role, or a like-swipe from candidate not found
      AIServiceError — Claude call failed or returned unparseable output
    """
    candidate = session.get(Candidate, candidate_id)
    if not candidate:
        raise NotFoundError(f"Candidate {candidate_id} not found.")

    role = session.get(Role, role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found.")

    swipe = session.exec(
        select(Swipe).where(
            Swipe.candidate_id == candidate_id,
            Swipe.role_id == role_id,
            Swipe.candidate_direction == SwipeDirection.like,
        )
    ).first()
    if swipe is None:
        raise NotFoundError(
            f"Candidate {candidate_id} has not liked role {role_id}. "
            "Keyword screening requires the candidate to be in the review queue."
        )

    try:
        result = _keyword_match(
            role_title=role.title,
            company_name=_company_name_for_role(role, session),
            role_description=role.description,
            keywords=", ".join(role.keywords or []),
            resume_summary=candidate.summary or "",
            top_skills=", ".join(candidate.top_skills or []),
        )
    except (anthropic.APIError, anthropic.APIConnectionError, anthropic.APITimeoutError) as e:
        raise AIServiceError(f"Keyword screening API error: {e}") from e
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        raise AIServiceError(f"Keyword screening returned invalid output: {e}") from e

    try:
        raw_score = result.get("keyword_score", 0.0)
        keyword_score = float(raw_score)
        if not (0.0 <= keyword_score <= 1.0):
            raise ValueError(f"keyword_score out of range: {keyword_score}")

        reasoning = str(result.get("reasoning", ""))

        raw_approved = result.get("approve_for_interview", False)
        if not isinstance(raw_approved, bool):
            raise TypeError(
                f"approve_for_interview must be a JSON boolean, got {type(raw_approved).__name__}: {raw_approved!r}"
            )
        approved = raw_approved
    except (TypeError, ValueError) as e:
        raise AIServiceError(f"Keyword screening returned invalid output: {e}") from e

    # Persist on the swipe row for cheap re-reads
    swipe.keyword_score = keyword_score
    swipe.keyword_reasoning = reasoning
    swipe.keyword_approved = approved
    session.add(swipe)
    session.commit()

    return {
        "candidate_id": candidate_id,
        "role_id": role_id,
        "keyword_score": keyword_score,
        "reasoning": reasoning,
        "approve_for_interview": approved,
    }


def _company_name_for_role(role: Role, session: Session) -> str:
    company = session.get(Company, role.company_id)
    return company.name if company else "Company"


# ---------------------------------------------------------------------------
# Active interviews
# ---------------------------------------------------------------------------

def get_active_interviews(session: Session, company_id: int | None = None) -> list[dict]:
    """Return all matches currently in the interviewing state.

    Optionally scoped to a single company via company_id.
    Returns lightweight dashboard-card dicts suitable for a live monitor view.
    """
    query = select(Match).where(Match.status == MatchStatus.interviewing)
    matches = session.exec(query).all()

    result: list[dict] = []
    for match in matches:
        role = session.get(Role, match.role_id)
        if role is None:
            continue
        if company_id is not None and role.company_id != company_id:
            continue
        candidate = session.get(Candidate, match.candidate_id)
        if candidate is None:
            continue
        result.append({
            "match_id": match.id,
            "role_id": role.id,
            "role_title": role.title,
            "candidate_id": candidate.id,
            "candidate_name": candidate.name,
            "top_skills": candidate.top_skills,
            "matched_at": match.matched_at.isoformat(),
        })

    return result


# ---------------------------------------------------------------------------
# Recruiter dashboard
# ---------------------------------------------------------------------------

def get_role_dashboard(role_id: int, session: Session) -> dict:
    """Return recruiter dashboard data for a role.

    Splits matches into active (pending / interviewing) and completed,
    including parsed interview summaries for completed candidates.

    Raises:
      NotFoundError — role not found
    """
    role = session.get(Role, role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found.")

    company = session.get(Company, role.company_id)
    company_name = company.name if company else "Company"

    matches = session.exec(
        select(Match)
        .where(Match.role_id == role_id)
        .order_by(Match.matched_at.desc())
    ).all()

    active: list[dict] = []
    completed: list[dict] = []

    for match in matches:
        candidate = session.get(Candidate, match.candidate_id)
        if not candidate:
            continue

        base = {
            "match_id": match.id,
            "candidate_id": candidate.id,
            "name": candidate.name,
            "resume_score_pct": round((candidate.resume_score or 0.0) * 100, 1),
            "top_skills": candidate.top_skills,
            "matched_at": match.matched_at.isoformat(),
        }

        if match.status == MatchStatus.completed:
            summary = json.loads(match.interview_summary) if match.interview_summary else {}
            completed.append({
                **base,
                "final_score": match.final_score,
                "recommendation": match.recommendation,
                "summary": summary,
                "completed_at": match.completed_at.isoformat() if match.completed_at else None,
            })
        else:
            active.append({
                **base,
                "status": match.status,
            })

    return {
        "role": _role_dict(role, company_name),
        "active": active,
        "completed": completed,
    }


# ---------------------------------------------------------------------------
# Candidate comparison
# ---------------------------------------------------------------------------

def compare_role_candidates(role_id: int, keep_top_pct: float, session: Session) -> dict:
    """Rank all completed candidates for a role and return advance/reject split.

    Composite score = 0.4 * resume_score + 0.6 * interview_score.
    keep_top_pct controls the advance/reject boundary (0.0–1.0).

    Raises:
      NotFoundError — role not found
    """
    role = session.get(Role, role_id)
    if not role:
        raise NotFoundError(f"Role {role_id} not found.")

    completed_matches = session.exec(
        select(Match).where(
            Match.role_id == role_id,
            Match.status == MatchStatus.completed,
        )
    ).all()

    if not completed_matches:
        return {"advance": [], "reject": [], "total": 0, "cutoff": 0}

    candidates_data: list[dict] = []
    for match in completed_matches:
        candidate = session.get(Candidate, match.candidate_id)
        if not candidate:
            continue
        resume_score = candidate.resume_score or 0.0
        interview_score = match.final_score or 0.0
        candidates_data.append({
            "match_id": match.id,
            "candidate_id": candidate.id,
            "name": candidate.name,
            "resume_score": resume_score,
            "resume_score_pct": round(resume_score * 100, 1),
            "interview_score": interview_score,
            "interview_score_pct": round(interview_score * 100, 1),
            # total_score is added by rank_candidates
            "total_score": round(0.4 * resume_score + 0.6 * interview_score, 3),
            "recommendation": match.recommendation,
            "top_skills": candidate.top_skills,
            "completed_at": match.completed_at.isoformat() if match.completed_at else None,
        })

    ranked = comparison_service.rank_candidates(candidates_data)
    return comparison_service.apply_cutoff(ranked, keep_top_pct=keep_top_pct)


# ---------------------------------------------------------------------------
# Private helpers (grade validation)
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
