"""
Interview question selection and generation.

Preliminary interview: random.sample(role.questions, 4) — no AI.
Simulation interview:  AI-generated via simul_generate_questions.md.

Prompts used:
  - simul_generate_questions.md → generate_simul_questions()
"""

import json
import random
from ai import client, MODEL
from services.prompt_loader import render_prompt


def pick_prelim_questions(role_questions: list[str], n: int = 4) -> list[str]:
    """Randomly select n questions from the role's question set for the preliminary interview."""
    return random.sample(role_questions, min(n, len(role_questions)))


def generate_simul_questions(
    role_title: str,
    company_name: str,
    role_description: str,
    keywords: str,
    selected_question_set: str,
    candidate_background: str,
) -> list[dict]:
    """Generate 8 AI simulation interview questions (6 behavioral + 2 technical_explain).

    selected_question_set: formatted string of questions the recruiter has chosen.
    candidate_background: candidate summary + top skills as a formatted string.

    Returns list of dicts: {id, text, category, expected_signals}.
    """
    prompt = render_prompt(
        "simul_generate_questions",
        role_title=role_title,
        company_name=company_name,
        role_description=role_description,
        keywords=keywords,
        selected_question_set=selected_question_set,
        candidate_background=candidate_background,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    result = json.loads(response.content[0].text)
    return result["questions"]
