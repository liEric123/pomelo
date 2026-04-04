"""
Resume skill extraction and fixed-dimension skill vector generation.

Used during candidate registration after resume grading.
The skill vector is stored in Candidate.embedding and used for feed matching.

Prompts used:
  - skill_vector.md → generate_skill_vector()
"""

from ai import client, MODEL
from services.prompt_loader import parse_json_response, render_prompt


# ---------------------------------------------------------------------------
# Skill vocabulary — defines the fixed vector dimensions.
# Order matters: vector index corresponds to skill position here.
# Add skills at the end to avoid shifting existing vectors.
# ---------------------------------------------------------------------------

SKILL_VOCABULARY: list[str] = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust",
    "C++", "C", "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R",
    # Frontend
    "React", "Vue", "Angular", "HTML", "CSS", "Next.js", "Tailwind CSS",
    # Backend
    "Node.js", "FastAPI", "Django", "Flask", "Express", "Spring Boot", "Rails",
    # Data / ML
    "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "Pandas", "NumPy", "PyTorch", "TensorFlow", "scikit-learn", "Spark",
    # Infrastructure / DevOps
    "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Linux", "Git",
    "CI/CD", "Terraform", "Nginx",
    # Practices / Concepts
    "REST API", "GraphQL", "WebSocket", "Microservices", "System Design",
    "Machine Learning", "Data Engineering", "Security",
]

# Lowercase lookup for case-insensitive matching
_VOCAB_INDEX: dict[str, int] = {s.lower(): i for i, s in enumerate(SKILL_VOCABULARY)}


def generate_skill_vector(resume_text: str, top_skills: list[str]) -> list[float]:
    """Ask Claude to extract {skill: proficiency} from the resume, then map to a fixed vector.

    Returns a list[float] of length len(SKILL_VOCABULARY). Unrecognized skills
    are ignored; missing vocabulary skills are 0.0.
    """
    prompt = render_prompt(
        "skill_vector",
        resume_text=resume_text,
        top_skills=", ".join(top_skills) if top_skills else "none identified yet",
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = parse_json_response(response.content[0].text)
    return _map_to_vector(raw)


def zero_skill_vector() -> list[float]:
    """Return an all-zero vector with the canonical skill dimensionality."""
    return [0.0] * len(SKILL_VOCABULARY)


def _map_to_vector(skill_proficiencies: dict) -> list[float]:
    """Map a {skill: proficiency} dict onto the fixed vocabulary vector."""
    vector = [0.0] * len(SKILL_VOCABULARY)
    for skill, proficiency in skill_proficiencies.items():
        idx = _VOCAB_INDEX.get(skill.lower())
        if idx is not None:
            # clamp to [0.0, 1.0]
            vector[idx] = max(0.0, min(1.0, float(proficiency)))
    return vector

