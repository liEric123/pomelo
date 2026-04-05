"""
In-memory interview session state and per-connection SSE event queues.

One InterviewSession is created per active match when the candidate connects.
Each recruiter SSE subscriber gets its own queue so multiple dashboard tabs
can observe the same interview without stealing events from one another.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from models import Candidate, Role

MAX_SECONDS_PER_ANSWER = 120


@dataclass
class InterviewSession:
    match_id: int
    role: Role
    candidate: Candidate
    company_name: str
    questions: list[dict]           # [{id, text, category, expected_signals}, ...]
    current_index: int = 0
    awaiting_injected: bool = False  # True while candidate is answering a recruiter-injected Q
    current_injected_question: str = ""  # text of the injected question being answered
    inject_queue: deque = field(default_factory=deque)
    elapsed_times: list[int] = field(default_factory=list)  # seconds per answer, in order
    is_complete: bool = False


# Module-level singletons — intentionally simple for hackathon speed.
# All access must be from the same process (single-worker uvicorn).
_sessions: dict[int, InterviewSession] = {}
_sse_queues: dict[int, list[asyncio.Queue]] = {}


def create_session(
    match_id: int,
    role: Role,
    candidate: Candidate,
    company_name: str,
    questions: list[dict],
) -> InterviewSession:
    sess = InterviewSession(
        match_id=match_id,
        role=role,
        candidate=candidate,
        company_name=company_name,
        questions=questions,
    )
    _sessions[match_id] = sess
    return sess


def get_session(match_id: int) -> Optional[InterviewSession]:
    return _sessions.get(match_id)


def remove_session(match_id: int) -> None:
    """Remove the in-memory session. SSE queue is kept alive for final event delivery."""
    _sessions.pop(match_id, None)


def remove_sse_queue(match_id: int, queue: asyncio.Queue) -> None:
    """Remove one recruiter SSE subscriber queue for a match."""
    queues = _sse_queues.get(match_id)
    if not queues:
        return
    try:
        queues.remove(queue)
    except ValueError:
        return
    if not queues:
        _sse_queues.pop(match_id, None)


def push_inject(match_id: int, question_text: str) -> bool:
    """Queue a recruiter-injected question for this session.

    Returns False if the session is not active or already complete.
    """
    sess = _sessions.get(match_id)
    if sess is None or sess.is_complete:
        return False
    sess.inject_queue.append(question_text)
    return True


async def emit_event(match_id: int, event_type: str, data: dict) -> None:
    """Push an event to every active recruiter SSE subscriber for this match."""
    queues = list(_sse_queues.get(match_id, []))
    event = {"type": event_type, "data": data}
    for queue in queues:
        await queue.put(event)


def get_sse_queue(match_id: int) -> Optional[asyncio.Queue]:
    queues = _sse_queues.get(match_id)
    if not queues:
        return None
    return queues[0]


def ensure_sse_queue(match_id: int) -> asyncio.Queue:
    """Create and register one SSE queue for a recruiter connection."""
    queue = asyncio.Queue()
    _sse_queues.setdefault(match_id, []).append(queue)
    return queue
