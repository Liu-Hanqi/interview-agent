"""Decide whether to continue with a follow-up question."""

from interview_agent.state import InterviewState


def should_followup(state: InterviewState) -> str:
    """Return the name of the next node.

    Decision logic:
    - total_followups >= 10 → stop all follow-ups → score_answer
    - last answer was dismissive ("不清楚"/"不知道") → score_answer
    - otherwise → generate_followup
    """
    total = state.get("total_followups", 0)
    if total >= 10:
        return "score_answer"

    history = state.get("history", [])
    if history:
        last_answer = history[-1].get("answer", "")
        if "不清楚" in last_answer or "不知道" in last_answer:
            return "score_answer"

    return "generate_followup"