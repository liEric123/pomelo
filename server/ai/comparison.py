"""
Thin coordination layer for candidate ranking.

comparison_service.py handles the pure math. This module assembles the
total_score for each candidate from their component scores before ranking.
"""

from models import Candidate, Match, Role


def compute_total_score(
    resume_score: int,
    keyword_score: float,
    interview_weighted_score: float,
) -> float:
    """Compute a single comparable total score from component scores.

    Weights (adjust as needed for demo tuning):
      - resume_score (BRS 1-100, normalized to 0-1): 30%
      - keyword_score (0-1):                          20%
      - interview_weighted_score (0-1):               50%

    Returns a float 0.0-1.0.
    """
    pass


def build_ranking_payload(role: Role, completed_matches: list[Match]) -> dict:
    """Assemble and rank all completed candidates for a role.

    For each match, loads scores, computes total_score, then calls
    comparison_service.rank_candidates() and apply_cutoff().

    Returns the structured advance/reject result from comparison_service.

    Calls:
      - compute_total_score()  (per candidate)
      - comparison_service.rank_candidates()
      - comparison_service.apply_cutoff()
    """
    pass
