"""
Resume scoring and keyword matching.

Prompts used:
  - resume_grade.md    → grade_resume()
  - keyword_match.md   → keyword_match()
  - pre_ai_interview.md → pre_ai_interview_score()
"""

from ai import client, MODEL
from services.prompt_loader import parse_json_response, render_prompt


def grade_resume(
    resume_text: str,
    role_title: str,
    company_name: str,
    role_description: str,
    keywords: str,
    resume_summary: str = "",
    top_skills: str = "",
    interview_responses: str = "",
) -> dict:
    """Grade a resume against a role. Returns score (int/100), summary, top_skills."""
    prompt = render_prompt(
        "resume_grade",
        role_title=role_title,
        company_name=company_name,
        role_description=role_description,
        keywords=keywords,
        resume_summary=resume_summary,
        top_skills=top_skills,
        interview_responses=interview_responses,
        resume_text=resume_text,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(response.content[0].text)


def keyword_match(
    role_title: str,
    company_name: str,
    role_description: str,
    keywords: str,
    resume_summary: str,
    top_skills: str,
) -> dict:
    """Resume-only keyword match. Returns keyword_score, reasoning, approve_for_interview."""
    prompt = render_prompt(
        "keyword_match",
        role_title=role_title,
        company_name=company_name,
        role_description=role_description,
        keywords=keywords,
        resume_summary=resume_summary,
        top_skills=top_skills,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(response.content[0].text)


def pre_ai_interview_score(
    role_title: str,
    company_name: str,
    role_description: str,
    keywords: str,
    resume_summary: str,
    top_skills: str,
    interview_responses: str = "",
) -> dict:
    """Post-preliminary-interview scoring.

    Combines keyword match with optional behavioral rubric scoring.
    Pass interview_responses as a formatted string of Q&A pairs,
    or leave empty to score on resume evidence alone.

    Returns keyword_score, behavioral_score (or null), reasoning, approve_for_interview.
    """
    prompt = render_prompt(
        "pre_ai_interview",
        role_title=role_title,
        company_name=company_name,
        role_description=role_description,
        keywords=keywords,
        resume_summary=resume_summary,
        top_skills=top_skills,
        interview_responses=interview_responses,
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_json_response(response.content[0].text)
