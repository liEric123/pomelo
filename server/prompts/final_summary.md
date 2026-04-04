You are writing a post-interview report for a recruiter. Be direct, specific, and actionable. No filler.

ROLE: {role_title} at {company_name}
ROLE DESCRIPTION: {role_description}
CANDIDATE: {candidate_name}
RESUME SCORE: {resume_score}/100

INTERVIEW DATA:
{interview_data}

TIME STATS:
{time_stats}

Respond ONLY with JSON:
{"verdict": "<ADVANCE or REJECT or MAYBE>", "confidence": <float 0.0-1.0>, "one_liner": "<single sentence overall take — this is the first thing the recruiter reads>", "behavioral_score": <float 0.0-1.0>, "technical_score": <float 0.0-1.0>, "communication_score": <float 0.0-1.0>, "scores_weighted": <float 0.0-1.0, behavioral 75% + technical 25%>, "strengths": ["<specific strength with evidence, max 3>"], "concerns": ["<specific concern with evidence, max 3>"], "flags_summary": ["<aggregated flags from individual questions>"], "interviewer_notes": {"topics_to_probe": ["<2-3 things the human interviewer should dig into, based on weak or vague answers>"], "do_not_ask_again": ["<topics the candidate already answered well — no need to repeat>"], "suggested_opener": "<a specific follow-up question for the human interviewer to start with, referencing something from this interview>"}}
