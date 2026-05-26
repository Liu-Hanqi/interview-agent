"""LangGraph interview agent — nodes, graph, and entry point."""

from langgraph.graph import StateGraph, END

from interview_agent.state import InterviewState
from interview_agent.nodes import (
    select_question,
    ask_question,
    receive_answer,
    should_followup,
    generate_followup,
    score_answer,
    advance_pool,
    compile_report,
)


def build_graph() -> StateGraph:
    g = StateGraph(InterviewState)

    # Nodes
    g.add_node("select_question", select_question.select_next_question)
    g.add_node("ask_question", ask_question.ask_question)
    g.add_node("receive_answer", receive_answer.receive_answer)
    g.add_node("should_followup", should_followup.should_followup)
    g.add_node("generate_followup", generate_followup.generate_followup)
    g.add_node("score_answer", score_answer.score_answer)
    g.add_node("advance_pool", advance_pool.advance_pool)
    g.add_node("compile_report", compile_report.compile_report)

    # Entry
    g.set_entry_point("select_question")

    # Main flow: select → ask → receive → should_followup
    g.add_edge("select_question", "ask_question")
    g.add_edge("ask_question", "receive_answer")

    # Conditional: follow-up loop or exit to scoring
    g.add_conditional_edges(
        "receive_answer",
        should_followup.should_followup,
        {
            "generate_followup": "generate_followup",
            "score_answer": "score_answer",
        },
    )

    # Follow-up loop: generate → ask (re-ask with follow-up question)
    g.add_edge("generate_followup", "ask_question")

    # After scoring: advance pool or compile report
    g.add_conditional_edges(
        "score_answer",
        _after_score,
        {
            "advance_pool": "advance_pool",
            "compile_report": "compile_report",
        },
    )

    # Pool advancement loops back to select_question for next pool
    g.add_edge("advance_pool", "select_question")

    # Terminal
    g.add_edge("compile_report", END)

    return g


def _after_score(state: InterviewState) -> str:
    """Routing after score_answer: if all pools done → compile_report."""
    if state.get("_interview_done"):
        return "compile_report"
    return "advance_pool"


interview_graph = build_graph()