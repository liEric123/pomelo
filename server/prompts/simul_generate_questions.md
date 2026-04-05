You are creating interview questions for the role of {role_title} at {company_name}. This is the final interview stage where a recruiter is monitoring live.

ROLE DESCRIPTION: {role_description}
REQUIRED SKILLS: {keywords}
INTERVIEWER-SELECTED QUESTION SET: {selected_question_set}
CANDIDATE BACKGROUND: {candidate_background}

Generate 4 questions with this mix:
- 3 behavioral questions (75%): past experience, conflict resolution, leadership, failure/growth, teamwork, time management. Use the STAR format expectation (Situation, Task, Action, Result).
- 1 technical explanation question (25%): ask the candidate to either explain a technical concept relevant to the role in plain English OR walk through pseudocode for a relevant problem. This should test understanding, not syntax.

Constraints:
- Only generate questions that come from or are clearly grounded in the interviewer-selected question set. Do not invent unrelated topics.
- Keep every question relevant to the role description, required skills, and candidate background.
- Personalize questions when possible using the candidate's experience, projects, or skills.
- Do not ask about tools, technologies, or experiences not supported by the interviewer-selected set or candidate background.
- Avoid repetition, vague wording, trivia, and overly generic questions.
- If the interviewer-selected set contains more than enough options, choose the most relevant and varied ones.

Respond ONLY with JSON:
{"questions": [{"id": 1, "text": "...", "category": "behavioral|technical_explain", "expected_signals": ["<what a good answer touches on>"]}]}
