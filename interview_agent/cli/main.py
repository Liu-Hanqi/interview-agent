"""Candidate-facing CLI for the interview agent."""

import argparse
import json
import sys

from interview_agent.graph import interview_graph
from interview_agent.state import InterviewState


POOL_DISPLAY = {
    "algorithm": "算法题 (10%)",
    "fundamentals": "八股文 (50%)",
    "scenario": "场景题 (40%)",
}


def _print(msg: str) -> None:
    print(msg, flush=True)


def _input(prompt: str) -> str:
    return input(prompt).strip()


def _print_report(report: dict) -> None:
    _print("\n" + "=" * 50)
    _print("              面试报告")
    _print("=" * 50)
    _print(f"  总分：{report['total_score']} / 100")
    _print(f"  场景题得分：{report['scenario_score']} / 40")

    if report.get("peak_chains"):
        for chain in report["peak_chains"]:
            _print(f"  峰值链：{chain['rounds']}轮 (+{chain['peak_bonus']}分)")

    if report.get("strong_points"):
        _print("\n  亮点：")
        for pt in report["strong_points"]:
            _print(f"    ✓ {pt}")

    if report.get("weak_points"):
        _print("\n  薄弱点：")
        for pt in report["weak_points"]:
            _print(f"    ✗ {pt}")

    _print("\n" + "=" * 50)


def start_interview(profile: str, pool: str = "algorithm") -> dict:
    """Run a full interview session via the CLI."""
    app = interview_graph.compile()

    state: InterviewState = {
        "history": [],
        "current_pool": pool,
        "followup_count": 0,
        "total_followups": 0,
        "scores": [],
        "candidate_profile": profile,
        "current_question": None,
        "pending_answer": None,
    }

    _print(f"\n🎯 面试开始 — 岗位：{profile}")
    _print(f"题池顺序：algorithm → fundamentals → scenario")
    _print(f"提示：输入 '跳过' 跳过当前题，输入 '退出' 结束面试\n")

    visited_pools = set()

    while True:
        # Select + Ask
        state = app.invoke("select_question", state)
        state = app.invoke("ask_question", state)

        if state["current_pool"] not in visited_pools:
            visited_pools.add(state["current_pool"])
            _print(f"\n[{POOL_DISPLAY.get(state['current_pool'], state['current_pool'])}]")

        _print(f"\n面试官：{state['current_question']}")

        # Gather answer
        raw = _input("\n候选人回答：").strip()

        if raw in ("退出", "quit", "exit"):
            _print("\n面试结束（主动退出）")
            break

        if raw == "跳过":
            state["pending_answer"] = "[候选人跳过此题]"
        else:
            state["pending_answer"] = raw

        state = app.invoke("receive_answer", state)

        # Follow-up loop
        while True:
            routing = app.invoke("should_followup", state)

            if routing == "score_answer":
                state = app.invoke("score_answer", state)
                break

            # generate_followup
            state = app.invoke("generate_followup", state)
            _print(f"\n追问：{state['current_question']}")

            raw = _input("\n候选人回答：").strip()
            if raw in ("退出", "quit", "exit"):
                state["pending_answer"] = "[候选人主动退出]"
                state = app.invoke("receive_answer", state)
                _print("\n面试结束")
                return state.get("_report", {})

            if raw == "跳过":
                state["pending_answer"] = "[候选人跳过此题]"
            else:
                state["pending_answer"] = raw

            state = app.invoke("receive_answer", state)

        # After scoring — advance or end
        if state.get("_interview_done"):
            state = app.invoke("compile_report", state)
            _print_report(state.get("_report", {}))
            break

        state = app.invoke("advance_pool", state)

    return state.get("_report", {})


def main() -> None:
    parser = argparse.ArgumentParser(description="面试 Agent CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="开始一场面试")
    start.add_argument("--profile", "-p", default="Java后端工程师", help="岗位描述")
    start.add_argument("--pool", default="algorithm", help="起始题池")

    args = parser.parse_args()

    if args.command == "start":
        start_interview(profile=args.profile, pool=args.pool)


if __name__ == "__main__":
    main()