"""
Candidate ranking and cutoff — no AI, pure math.

Candidates are ranked by total_score. The recruiter controls the cutoff
(top N or top X%). Default is top 50%.
"""


def rank_candidates(candidates: list[dict]) -> list[dict]:
    """Sort candidates by total_score descending and attach a rank field.

    Each dict must have at least: candidate_id, candidate_name, total_score.
    Returns the same list sorted and annotated with rank (1 = best).
    """
    sorted_candidates = sorted(candidates, key=lambda c: c["total_score"], reverse=True)
    for i, c in enumerate(sorted_candidates, 1):
        c["rank"] = i
    return sorted_candidates


def apply_cutoff(
    ranked: list[dict],
    keep_top_n: int | None = None,
    keep_top_pct: float | None = None,
) -> dict:
    """Split ranked candidates into advance / reject groups.

    Pass keep_top_n (integer) or keep_top_pct (0.0–1.0).
    If neither is passed, defaults to top 50%.

    Returns:
      {advance: [...], reject: [...], total: int, cutoff: int}
    """
    total = len(ranked)
    if keep_top_n is not None:
        cutoff = min(keep_top_n, total)
    elif keep_top_pct is not None:
        cutoff = max(1, round(total * keep_top_pct))
    else:
        cutoff = max(1, round(total * 0.5))

    return {
        "advance": ranked[:cutoff],
        "reject": ranked[cutoff:],
        "total": total,
        "cutoff": cutoff,
    }
