"""Compile the final interview report."""

from interview_agent.state import InterviewState, Turn


def _sum_by_dimension(scores: list[dict], dim: str) -> float:
    return sum(s["value"] for s in scores if s["dimension"] == dim)


def compile_report(state: InterviewState) -> InterviewState:
    """Build the final structured report from accumulated scores."""
    scores = state.get("scores", [])

    # Per-dimension sums
    clarity = _sum_by_dimension(scores, "clarity")
    depth = _sum_by_dimension(scores, "depth")
    tradeoffs = _sum_by_dimension(scores, "tradeoffs")
    honesty = _sum_by_dimension(scores, "honesty")

    # Peak bonuses
    peak_total = _sum_by_dimension(scores, "peak_bonus")

    # Strong / weak points from score records
    strong = [s["reason"] for s in scores if s["value"] > 0 and s["dimension"] in ("clarity", "depth", "tradeoffs")]
    weak = [s["reason"] for s in scores if s["value"] < 0]

    report = {
        "total_score": round(clarity + depth + tradeoffs + honesty + peak_total, 1),
        "algorithm_score": 0,  # filled by caller based on pool
        "fundamentals_score": 0,
        "scenario_score": round(depth + tradeoffs + peak_total, 1),
        "peak_chains": [
            {"rounds": _sum_by_dimension(scores, "peak_bonus") // 5, "peak_bonus": int(peak_total)}
        ] if peak_total > 0 else [],
        "strong_points": list(set(strong))[:5],
        "weak_points": list(set(weak))[:5],
    }

    state["_report"] = report
    return state