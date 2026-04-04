"""
Thin coordination layer between routes/coordinator and scoring_service.

scoring_service.py owns the prompt rendering and Anthropic calls.
This module handles any pre/post processing that doesn't belong in a route.
"""

from models import Candidate, Role


def score_candidate_for_role(candidate: Candidate, role: Role) -> dict:
    """Run resume grading and keyword match for a candidate/role pair.

    Returns combined result:
      {
        "resume_score": int,          # BRS 1-100
        "summary": str,
        "top_skills": list[str],
        "keyword_score": float,       # 0.0-1.0
        "keyword_reasoning": str,
        "approve_for_interview": bool,
      }

    Calls:
      - scoring_service.grade_resume()
      - scoring_service.keyword_match()
    """
    pass


def score_after_prelim(candidate: Candidate, role: Role, interview_responses: str) -> dict:
    """Run post-preliminary-interview advancement scoring.

    Combines keyword match with behavioral rubric evaluation.
    interview_responses: formatted Q&A string from the preliminary interview.

    Returns:
      {
        "keyword_score": float,
        "behavioral_score": float | None,
        "reasoning": str,
        "approve_for_interview": bool,
      }

    Calls:
      - scoring_service.pre_ai_interview_score()
    """
    pass
