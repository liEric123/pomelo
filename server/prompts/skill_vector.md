Extract the top technical skills from this resume and estimate the candidate's proficiency in each one.

RESUME TEXT:
{resume_text}

SKILLS ALREADY IDENTIFIED:
{top_skills}

Instructions:
- Include up to 20 skills with clear evidence in the resume.
- Use standard, capitalized skill names (e.g. "Python", "React", "PostgreSQL").
- Proficiency is a float from 0.0 to 1.0:
    1.0 = expert / used extensively in production or high-impact work
    0.7 = proficient / used in real projects with clear outcomes
    0.5 = working knowledge / mentioned with some context
    0.3 = basic / listed without strong evidence
- Do not include skills with no evidence in the resume.
- Do not invent skills not present in the text.

Return ONLY valid JSON — no markdown, no explanation:
{"Python": 0.9, "React": 0.7, "PostgreSQL": 0.6}
