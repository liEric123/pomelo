"""
Cosine similarity matching between candidate skill vectors and role keyword vectors.

Both vectors use the same fixed vocabulary defined in resume_service.SKILL_VOCABULARY,
so they are directly comparable dimension-by-dimension.
"""

import numpy as np

from services.resume_service import SKILL_VOCABULARY

# Case-insensitive index into the shared vocabulary
_ROLE_VOCAB_INDEX: dict[str, int] = {s.lower(): i for i, s in enumerate(SKILL_VOCABULARY)}


def build_role_vector(keywords: list[str]) -> list[float]:
    """Convert a role's keyword list into a fixed-dimension binary vector.

    Each keyword present in SKILL_VOCABULARY gets a 1.0 in its slot.
    Unrecognized keywords are ignored.
    """
    vector = [0.0] * len(SKILL_VOCABULARY)
    for kw in keywords:
        idx = _ROLE_VOCAB_INDEX.get(kw.lower())
        if idx is not None:
            vector[idx] = 1.0
    return vector


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two equal-length vectors.

    Returns 0.0 if either vector is all zeros (avoids division by zero).
    """
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))
