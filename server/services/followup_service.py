"""
Follow-up question generation for the simulation interview.

Follow-ups are generated in the background after an answer is graded.
The recruiter decides whether to inject one — the candidate is never
blocked waiting for this to complete.

Prompts used:
  - simul_followup.md → generate_followup()
"""

import json
from ai import client, MODEL
from services.prompt_loader import render_prompt


def generate_followup(
    category: str,
    current_question: str,
    candidate_answer: str,
    rationale: str,
    score: float,
) -> str:
    """Generate one follow-up question for a candidate's answer.

    category: "behavioral" or "technical_explain"
    rationale: the grading rationale from grading_service.grade_answer()
    score: the 0.0-1.0 score from grading_service.grade_answer()

    Returns a single follow-up question string.
    """
    prompt = render_prompt(
        "simul_followup",
        category=category,
        current_question=current_question,
        candidate_answer=candidate_answer,
        rationale_from_step_2=rationale,
        score_from_step_2=score,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    result = json.loads(response.content[0].text)
    return result["follow_up"]
