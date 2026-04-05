"""
Interview routes: candidate WebSocket, recruiter SSE stream, recruiter question injection.

Route responsibilities:
  - Accept/validate connections
  - Drive the WebSocket message loop
  - Delegate all business logic to hiring_coordinator
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
from services import interview_session as session_mgr
from services.followup_service import generate_followup
from services.hiring_coordinator import (
    AnswerResult,
    process_interview_answer,
    inject_recruiter_question,
    start_interview,
    InvalidInterviewState,
    NotFoundError,
    AIServiceError,
)

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
        opening_message = await asyncio.to_thread(start_interview, match_id, db)
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

    emit_transcript = opening_message.pop("emit_transcript", False)
    await websocket.send_json(opening_message)
    if emit_transcript:
        role = "question" if opening_message["type"] == "question" else "follow_up"
        await session_mgr.emit_event(match_id, "transcript", {
            "question_id": opening_message.get("id"),
            "text": opening_message["text"],
            "role": role,
        })

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
                done = await _handle_answer(websocket, db, match_id, msg)
                if done:
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
    msg: dict,
) -> bool:
    """Delegate answer processing to the coordinator and send the resulting WS message.

    Returns True when the interview is complete and the loop should exit.
    """
    answer_text: str = msg.get("text", "").strip()
    elapsed: int = int(msg.get("elapsed_seconds", 0))

    try:
        result: AnswerResult = await process_interview_answer(match_id, answer_text, elapsed, db)
    except InvalidInterviewState as e:
        await websocket.send_json({"type": "error", "detail": str(e)})
        return False

    # Fire background follow-up suggestion — never blocks the candidate
    asyncio.create_task(
        _suggest_followup_background(match_id, result.graded_question, answer_text, result.grade)
    )

    if result.next_action == "follow_up":
        await websocket.send_json({"type": "follow_up", "text": result.follow_up_text})
        return False

    if result.next_action == "question":
        await websocket.send_json({"type": "question", **result.next_question})
        return False

    # next_action == "complete"
    await websocket.send_json({"type": "interview_complete"})
    return True


async def _suggest_followup_background(
    match_id: int,
    question: dict,
    answer_text: str,
    grade: dict,
) -> None:
    """Generate a follow-up suggestion and emit it to the recruiter SSE stream.

    Best-effort — errors are swallowed so the candidate flow is never affected.
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
        pass


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
    try:
        inject_recruiter_question(match_id, body.question_text.strip())
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"queued": True}


# ---------------------------------------------------------------------------
# Recruiter SSE stream
# ---------------------------------------------------------------------------

@router.get("/{match_id}/stream")
async def interview_stream(match_id: int):
    """SSE stream for the recruiter's live interview dashboard.

    Event types:
      transcript         {"question_id", "text", "role": "question|answer|follow_up"}
      score              {"question_id", "score", "flag", "recruiter_hint"}
      suggestion         {"text"}  — AI-generated follow-up suggestion for recruiter review
      frame              {"data": "<base64>"}
      interview_complete {"summary": {...}}
    """
    # Pre-create queue so the recruiter can connect before the candidate
    q = session_mgr.ensure_sse_queue(match_id)

    async def event_generator():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue

                yield f"data: {json.dumps(event)}\n\n"

                if event.get("type") == "interview_complete":
                    break
        finally:
            session_mgr.remove_sse_queue(match_id, q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering
        },
    )
