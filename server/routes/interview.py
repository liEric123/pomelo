"""
Interview routes: candidate WebSocket, recruiter SSE stream, recruiter question injection.

Route responsibilities:
  - Accept/validate connections
  - Drive the WebSocket message loop
  - Delegate persistence and AI calls to coordinator and services
  - Map domain exceptions to HTTP/WS error codes
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from database import get_session
from models import InterviewMessage, MessageRole
from services import interview_session as session_mgr
from services.grading_service import grade_answer
from services.hiring_coordinator import (
    start_interview,
    complete_interview,
    InvalidInterviewState,
    NotFoundError,
    AIServiceError,
)
from services.followup_service import generate_followup

router = APIRouter(prefix="/interviews", tags=["interviews"])


# ---------------------------------------------------------------------------
# Candidate WebSocket
# ---------------------------------------------------------------------------

@router.websocket("/{match_id}/ws")
async def interview_websocket(
    match_id: int,
    websocket: WebSocket,
    db: Session = Depends(get_session),
):
    """WebSocket endpoint for the candidate's interview session.

    Incoming:
      {"type": "answer", "text": str, "elapsed_seconds": int}
      {"type": "frame",  "data": "<base64>"}

    Outgoing:
      {"type": "question",          "id", "index", "text", "category", "max_seconds"}
      {"type": "follow_up",         "text": str}
      {"type": "interview_complete"}
      {"type": "error",             "detail": str}
    """
    await websocket.accept()

    # ----- initialize session -----
    try:
        first_q = await asyncio.to_thread(start_interview, match_id, db)
    except NotFoundError as e:
        await websocket.send_json({"type": "error", "detail": str(e)})
        await websocket.close(code=4004)
        return
    except InvalidInterviewState as e:
        await websocket.send_json({"type": "error", "detail": str(e)})
        await websocket.close(code=4009)
        return
    except AIServiceError as e:
        await websocket.send_json({"type": "error", "detail": str(e)})
        await websocket.close(code=4502)
        return

    await websocket.send_json({"type": "question", **first_q})
    await session_mgr.emit_event(match_id, "transcript", {
        "question_id": first_q["id"], "text": first_q["text"], "role": "question",
    })

    sess = session_mgr.get_session(match_id)

    # ----- message loop -----
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "detail": "Invalid JSON."})
                continue

            msg_type = msg.get("type")

            if msg_type == "answer":
                await _handle_answer(websocket, db, match_id, sess, msg)
                if sess.is_complete:
                    break

            elif msg_type == "frame":
                # Relay frame to recruiter; do not persist (too large for DB)
                await session_mgr.emit_event(match_id, "frame", {"data": msg.get("data")})

            else:
                await websocket.send_json({"type": "error", "detail": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        pass


async def _handle_answer(
    websocket: WebSocket,
    db: Session,
    match_id: int,
    sess: session_mgr.InterviewSession,
    msg: dict,
) -> None:
    """Process one candidate answer: persist, grade, emit, advance."""
    answer_text: str = msg.get("text", "").strip()
    elapsed: int = int(msg.get("elapsed_seconds", 0))

    # Which question is being answered?
    if sess.awaiting_injected:
        # Answering a recruiter-injected follow-up — use stored question text for grading
        current_q = {
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

    # Grade (run in thread — synchronous Anthropic call)
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

    # Update answer message with grade
    flags = [grade["flag"]] if grade.get("flag") else []
    answer_msg.score = grade.get("score", 0.0)
    answer_msg.score_label = _score_label(grade.get("score", 0.0))
    answer_msg.flags = flags
    answer_msg.grade_reasoning = grade.get("rationale")
    db.add(answer_msg)
    db.commit()

    # Record timing
    sess.elapsed_times.append(elapsed)

    # Emit to recruiter
    await session_mgr.emit_event(match_id, "transcript", {
        "question_id": current_q["id"], "text": answer_text, "role": "answer",
    })
    await session_mgr.emit_event(match_id, "score", {
        "question_id": current_q["id"],
        "score": grade.get("score"),
        "flag": grade.get("flag"),
        "recruiter_hint": grade.get("recruiter_hint"),
    })

    # Background follow-up suggestion (non-blocking)
    asyncio.create_task(
        _suggest_followup_background(match_id, current_q, answer_text, grade)
    )

    # Decide what to send next
    if sess.awaiting_injected:
        # Just finished an injected question — go back to normal flow
        sess.awaiting_injected = False

    # Check inject queue before advancing scheduled questions
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
        await websocket.send_json({"type": "follow_up", "text": injected_text})
        await session_mgr.emit_event(match_id, "transcript", {
            "question_id": None, "text": injected_text, "role": "follow_up",
        })
        return  # wait for the answer to this injected question

    # Advance to next scheduled question
    if not sess.awaiting_injected:
        sess.current_index += 1

    if sess.current_index < len(sess.questions):
        next_q = sess.questions[sess.current_index]
        # Persist the outgoing question message
        q_msg = InterviewMessage(
            match_id=match_id,
            role=MessageRole.question,
            content=next_q["text"],
            question_index=sess.current_index,
        )
        db.add(q_msg)
        db.commit()
        await websocket.send_json({"type": "question", **_question_payload(next_q, sess.current_index)})
        await session_mgr.emit_event(match_id, "transcript", {
            "question_id": next_q["id"], "text": next_q["text"], "role": "question",
        })
    else:
        # All questions answered — complete
        sess.is_complete = True
        try:
            summary = await asyncio.to_thread(complete_interview, match_id, db)
        except AIServiceError:
            summary = {"verdict": "MAYBE", "one_liner": "Summary generation failed."}
        await websocket.send_json({"type": "interview_complete"})
        await session_mgr.emit_event(match_id, "interview_complete", {"summary": summary})


async def _suggest_followup_background(
    match_id: int,
    question: dict,
    answer_text: str,
    grade: dict,
) -> None:
    """Generate a follow-up suggestion and emit it to the recruiter as a suggestion event.

    The candidate is never blocked waiting for this — it runs as a background task.
    The recruiter may then inject it via POST /inject if they choose.
    """
    try:
        suggestion = await asyncio.to_thread(
            generate_followup,
            category=question.get("category", "behavioral"),
            current_question=question.get("text", ""),
            candidate_answer=answer_text,
            rationale=grade.get("rationale", ""),
            score=grade.get("score", 0.0),
        )
        await session_mgr.emit_event(match_id, "suggestion", {"text": suggestion})
    except Exception:
        pass  # Follow-up suggestion is best-effort; never surface errors to candidate


def _score_label(score: float) -> str:
    if score >= 0.8:
        return "strong"
    if score >= 0.5:
        return "adequate"
    return "weak"


def _question_payload(q: dict, index: int) -> dict:
    return {
        "id": q["id"],
        "index": index,
        "text": q["text"],
        "category": q["category"],
        "max_seconds": session_mgr.MAX_SECONDS_PER_ANSWER,
    }


# ---------------------------------------------------------------------------
# Recruiter question injection
# ---------------------------------------------------------------------------

class InjectRequest(BaseModel):
    question_text: str
    after_question_id: Optional[int] = None  # reserved for future ordering; currently ignored


@router.post("/{match_id}/inject")
def inject_question(
    match_id: int,
    body: InjectRequest,
    session: Session = Depends(get_session),
):
    """Queue a recruiter-injected follow-up question for the active interview.

    The question is delivered to the candidate after their current answer is submitted.
    Returns 404 if the session is not active.
    """
    if not body.question_text.strip():
        raise HTTPException(status_code=400, detail="question_text must not be empty.")
    ok = session_mgr.push_inject(match_id, body.question_text.strip())
    if not ok:
        raise HTTPException(status_code=404, detail=f"No active interview session for match {match_id}.")
    return {"queued": True}


# ---------------------------------------------------------------------------
# Recruiter SSE stream
# ---------------------------------------------------------------------------

@router.get("/{match_id}/stream")
async def interview_stream(match_id: int):
    """SSE stream for the recruiter's live interview dashboard.

    Event types:
      transcript        {"question_id", "text", "role": "question|answer|follow_up"}
      score             {"question_id", "score", "flag", "recruiter_hint"}
      suggestion        {"text"}  — AI-generated follow-up suggestion for recruiter review
      frame             {"data": "<base64>"}
      interview_complete {"summary": {...}}
    """
    # Create SSE queue now so events aren't missed if recruiter connects early
    q = session_mgr.get_sse_queue(match_id)
    if q is None:
        # Pre-create queue; the candidate WebSocket will also call get_or_create
        from services.interview_session import _sse_queues
        import asyncio as _asyncio
        _sse_queues[match_id] = _asyncio.Queue()
        q = _sse_queues[match_id]

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent proxy timeouts
                    yield ": keepalive\n\n"
                    continue

                payload = json.dumps(event)
                yield f"data: {payload}\n\n"

                if event.get("type") == "interview_complete":
                    break
        finally:
            session_mgr.remove_sse_queue(match_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
