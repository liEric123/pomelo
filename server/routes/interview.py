from typing import Optional

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session

from database import get_session

router = APIRouter(prefix="/interviews", tags=["interviews"])


# --- Candidate WebSocket ---

@router.websocket("/{match_id}/ws")
async def interview_websocket(
    match_id: int,
    websocket: WebSocket,
    session: Session = Depends(get_session),
):
    """WebSocket endpoint for the candidate's interview session.

    Incoming message types (from candidate):
      - {"type": "answer", "question_id": int, "text": str, "elapsed_seconds": int}
      - {"type": "frame", "data": "<base64>"}

    Outgoing message types (to candidate):
      - {"type": "question", "id": int, "text": str, "category": str, "max_seconds": int}
      - {"type": "follow_up", "text": str}
      - {"type": "interview_complete"}

    Flow (coordinator):
      1. Accept connection, load match + role + questions
      2. Send first question
      3. On each answer: grade → emit score event to recruiter SSE → optionally
         generate follow-up suggestion in background → advance to next question
      4. After last answer: generate summary, update match status, emit completion
    """
    await websocket.accept()
    try:
        pass  # TODO: implement interview loop
    except WebSocketDisconnect:
        pass


# --- Recruiter injection ---

class InjectRequest(BaseModel):
    question_text: str
    after_question_id: Optional[int] = None  # inject after this question; None = next


@router.post("/{match_id}/inject")
def inject_question(
    match_id: int,
    body: InjectRequest,
    session: Session = Depends(get_session),
):
    """Recruiter injects a follow-up question into the active interview.

    The question is queued and delivered to the candidate after their
    current answer is submitted, regardless of which question they are on.
    """
    pass


# --- Recruiter SSE stream ---

@router.get("/{match_id}/stream")
async def interview_stream(
    match_id: int,
    session: Session = Depends(get_session),
):
    """SSE stream for the recruiter's live interview dashboard.

    Event types pushed to the recruiter:
      - transcript  {"question_id": int, "text": str, "role": "question|answer|follow_up"}
      - score       {"question_id": int, "score": float, "flag": str, "recruiter_hint": str}
      - frame       {"data": "<base64>"}
      - interview_complete {"summary": {...}}
    """
    async def event_generator():
        pass  # TODO: implement SSE event loop

    return StreamingResponse(event_generator(), media_type="text/event-stream")

