"""
Real-time answer grading for both preliminary and simulation interviews.

The same prompt is used for both interview types.

Prompts used:
  - simul_evaluate_answer.md → grade_answer()
"""

from ai import client, MODEL
from services.prompt_loader import parse_json_response, render_prompt


def grade_answer(
    role_title: str,
    company_name: str,
    category: str,
    question_text: str,
    expected_signals: str,
    candidate_answer: str,
    seconds: int,
    max_seconds: int = 120,
) -> dict:
    """Grade a single interview answer.

    category: "behavioral" or "technical_explain"
    expected_signals: comma-separated or newline-separated list of signals.
    seconds: how long the candidate took to answer.

    Returns score (0.0-1.0), rationale, flag, recruiter_hint.
    """
    prompt = render_prompt(
        "simul_evaluate_answer",
        role_title=role_title,
        company_name=company_name,
        category=category,
        question_text=question_text,
        expected_signals=expected_signals,
        candidate_answer=candidate_answer,
        seconds=seconds,
        max_seconds=max_seconds,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(response.content[0].text)
