"""Receive and store the candidate's answer."""

from interview_agent.state import InterviewState, Turn


def receive_answer(state: InterviewState) -> InterviewState:
    """Append the candidate's answer to the conversation history."""
    history = state.get("history", [])
    last_question = state.get("current_question", "")

    # The pending_answer is set by the CLI before calling this node
    pending = state.get("pending_answer", "") or "[候选人表示不清楚]"

    turn: Turn = {
        "question": last_question,
        "answer": pending,
        "followups": [],
        "differentiating_value": "LOW",
    }
    history.append(turn)
    state["history"] = history
    # Clear pending
    state["pending_answer"] = None
    return state