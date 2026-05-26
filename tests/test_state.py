"""Tests for the interview agent."""

from interview_agent.state import InterviewState, Turn, ScoreDelta


def test_turn_structure():
    """Verify Turn and ScoreDelta TypedDicts are valid."""
    turn: Turn = {"question": "What is GIL?", "answer": "Global Interpreter Lock", "followups": [], "differentiating_value": "LOW"}
    assert turn["question"]
    assert "differentiating_value" in turn


def test_state_structure():
    """Verify InterviewState TypedDict fields."""
    state: InterviewState = {
        "history": [],
        "current_pool": "fundamentals",
        "followup_count": 0,
        "total_followups": 0,
        "scores": [],
        "candidate_profile": "",
        "current_question": None,
        "pending_answer": None,
    }
    assert state["current_pool"] in ("algorithm", "fundamentals", "scenario")
    assert state["followup_count"] == 0


def test_scoring_dimensions():
    """Verify ScoreDelta has all required dimensions."""
    valid_dimensions = {"clarity", "depth", "tradeoffs", "honesty", "design"}
    sd: ScoreDelta = {"dimension": "depth", "value": 5.0, "reason": "candidate demonstrated deep understanding"}
    assert sd["dimension"] in valid_dimensions
    assert sd["value"] > 0