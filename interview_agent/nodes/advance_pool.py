"""Advance to the next question pool."""

from interview_agent.state import InterviewState


POOL_ORDER = ["algorithm", "fundamentals", "scenario"]


def advance_pool(state: InterviewState) -> InterviewState:
    """Move from current_pool to the next one, or end the interview."""
    current = state.get("current_pool", "algorithm")
    idx = POOL_ORDER.index(current) if current in POOL_ORDER else 0

    if idx < len(POOL_ORDER) - 1:
        state["current_pool"] = POOL_ORDER[idx + 1]
        state["followup_count"] = 0  # reset per-pool
    else:
        # All pools exhausted — mark for end
        state["_interview_done"] = True

    return state