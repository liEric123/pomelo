"""
Post-interview summary generation for the recruiter.

Prompts used:
  - final_summary.md → generate_summary()

The interview_data and time_stats blocks are built by the helper functions
below, matching the structure expected by final_summary.md.
"""

import json
from ai import client, MODEL
from services.prompt_loader import render_prompt


def build_interview_data(questions_and_answers: list[dict]) -> str:
    """Format Q&A records into the block injected into final_summary.md.

    Each dict should have:
      - category (str)
      - question_text (str)
      - candidate_answer (str)
      - score (float)
      - flag (str or None)
      - follow_up (bool, optional)
      - follow_up_text (str, optional)
      - follow_up_answer (str, optional)
      - follow_up_score (float, optional)
    """
    lines = []
    for i, qa in enumerate(questions_and_answers, 1):
        lines.append("---")
        lines.append(f"Q{i} [{qa['category']}]: {qa['question_text']}")
        lines.append(f"Answer: {qa['candidate_answer']}")
        lines.append(f"Score: {qa['score']}/1.0")
        lines.append(f"Flag: {qa.get('flag') or 'none'}")
        if qa.get("follow_up"):
            lines.append(f"  Follow-up: {qa['follow_up_text']}")
            lines.append(f"  Follow-up answer: {qa['follow_up_answer']}")
            lines.append(f"  Follow-up score: {qa['follow_up_score']}/1.0")
        lines.append("---")
    return "\n".join(lines)


def build_time_stats(
    avg_seconds: float,
    fastest: tuple[int, float],
    slowest: tuple[int, float],
    timed_out_count: int,
) -> str:
    """Format timing data into the block injected into final_summary.md.

    fastest / slowest: (question_number, seconds)
    """
    return (
        f"- Average response time: {avg_seconds:.0f}s\n"
        f"- Fastest answer: Q{fastest[0]} ({fastest[1]:.0f}s)\n"
        f"- Slowest answer: Q{slowest[0]} ({slowest[1]:.0f}s)\n"
        f"- Timed out: {timed_out_count} questions"
    )


def generate_summary(
    role_title: str,
    company_name: str,
    role_description: str,
    candidate_name: str,
    resume_score: int,
    interview_data: str,
    time_stats: str,
) -> dict:
    """Generate a post-interview recruiter report.

    interview_data: built by build_interview_data()
    time_stats: built by build_time_stats()

    Returns verdict, confidence, one_liner, behavioral_score, technical_score,
    communication_score, scores_weighted, strengths, concerns, flags_summary,
    and interviewer_notes.
    """
    prompt = render_prompt(
        "final_summary",
        role_title=role_title,
        company_name=company_name,
        role_description=role_description,
        candidate_name=candidate_name,
        resume_score=resume_score,
        interview_data=interview_data,
        time_stats=time_stats,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return json.loads(response.content[0].text)
