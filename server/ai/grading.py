"""
Thin coordination layer for answer grading and follow-up generation.

Used by the interview WebSocket loop. grading_service and followup_service
own the prompt rendering and Anthropic calls.
"""

from models import InterviewMessage, Role


def grade_and_suggest_followup(
    role: Role,
    question: dict,
    candidate_answer: str,
    elapsed_seconds: int,
) -> tuple[dict, str | None]:
    """Grade an answer and optionally generate a follow-up suggestion.

    This is the main call during the interview loop. It runs grading
    synchronously (result is needed immediately for the SSE score event),
    then follow-up generation can be run in the background.

    Returns:
      - grade: dict with score, rationale, flag, recruiter_hint
      - follow_up: suggested follow-up question string, or None if not generated

    Calls:
      - grading_service.grade_answer()
      - followup_service.generate_followup()  (optional / background)
    """
    pass


def grade_prelim_answer(
    role: Role,
    question_text: str,
    candidate_answer: str,
    elapsed_seconds: int,
) -> dict:
    """Grade a single preliminary interview answer.

    Preliminary questions have no expected_signals, so an empty string is passed.
    Same grading prompt as the simulation interview.

    Returns: score, rationale, flag, recruiter_hint.

    Calls:
      - grading_service.grade_answer()
    """
    pass
