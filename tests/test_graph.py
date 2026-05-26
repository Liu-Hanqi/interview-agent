"""Tests for the LangGraph interview graph."""

from interview_agent.graph import interview_graph
from interview_agent.state import InterviewState


def test_graph_compiles():
    assert interview_graph is not None
    assert "select_question" in interview_graph.nodes
    assert "compile_report" in interview_graph.nodes


def test_initial_state():
    state: InterviewState = {
        "history": [],
        "current_pool": "algorithm",
        "followup_count": 0,
        "total_followups": 0,
        "scores": [],
        "candidate_profile": "Java后端",
        "current_question": None,
        "pending_answer": None,
    }
    assert state["current_pool"] == "algorithm"
    assert state["total_followups"] == 0