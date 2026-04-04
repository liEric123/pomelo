A candidate previously answered an interview question. The interviewer has decided that a follow-up should be asked. Generate one short follow-up that probes deeper into the candidate's earlier response.

CATEGORY: {category}
ORIGINAL QUESTION: {current_question}
CANDIDATE ANSWER: {candidate_answer}
GRADING RATIONALE: {rationale_from_step_2}
SCORE: {score_from_step_2}

The follow-up should help clarify, deepen, or verify the earlier answer. It should be directly tied to what the candidate already said and should focus on the most important missing, weak, or ambiguous point.

Good follow-up targets include:
- a vague or underdeveloped detail
- a missing part of the behavioral example
- an outcome that was mentioned but not measured
- a strong claim without supporting evidence
- unclear ownership or personal contribution
- a technical explanation missing a key tradeoff
- an unstated assumption, edge case, or constraint
- a partially correct answer that needs clarification

For behavioral: ask about a specific detail they mentioned, ask what they would do differently in hindsight, ask how they measured the result, or ask them to clarify their personal contribution.

For technical_explain: ask about a tradeoff they did not mention, ask them to walk through an edge case, ask about an assumption they made, or ask how their approach would change under a different constraint.

Constraints:
- Ask exactly one concise follow-up question.
- Do not repeat the original question.
- Do not ask multiple-part questions.
- Do not make up details that were not in the candidate's answer.
- Keep the wording natural and recruiter-like.

Respond ONLY with JSON:
{"follow_up": "<one concise follow-up question>"}
