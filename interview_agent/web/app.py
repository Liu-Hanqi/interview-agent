"""Streamlit app — interactive interview UI."""

import streamlit as st
from dotenv import load_dotenv

from interview_agent.graph import interview_graph
from interview_agent.state import InterviewState, Turn

load_dotenv()

POOL_DISPLAY = {
    "algorithm": "算法题 (10%)",
    "fundamentals": "八股文 (50%)",
    "scenario": "场景题 (40%)",
}
POOL_ORDER = ["algorithm", "fundamentals", "scenario"]


def init_state():
    """初始化 session_state."""
    if "app" not in st.session_state:
        st.session_state.app = interview_graph.compile()
    if "state" not in st.session_state:
        st.session_state.state = None
    if "history" not in st.session_state:
        st.session_state.history = []
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "started" not in st.session_state:
        st.session_state.started = False
    if "finished" not in st.session_state:
        st.session_state.finished = False
    if "report" not in st.session_state:
        st.session_state.report = None


def _parse_algorithm_result(raw: str) -> str:
    """从用户输入中解析 LeetCode 做题结果。"""
    raw_lower = raw.lower().strip()
    if any(kw in raw_lower for kw in ("ac", "accepted", "正确", "过了", "pass")):
        return "AC"
    if any(kw in raw_lower for kw in ("wa", "wrong", "错误", "没过", "fail")):
        return "WA"
    if any(kw in raw_lower for kw in ("tle", "超时")):
        return "TLE"
    if any(kw in raw_lower for kw in ("skip", "跳过")):
        return "SKIPPED"
    return "UNKNOWN"


def start_interview(profile: str, pool: str = "algorithm"):
    app = st.session_state.app
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

    if pool == "algorithm":
        state = app.invoke("run_algorithm", state)
        st.session_state.messages.append({
            "role": "assistant",
            "content": (
                f"**【{POOL_DISPLAY.get(state['current_pool'], state['current_pool'])}】**\n\n"
                f"{state.get('current_question', '')}\n\n"
                "📌 请在 LeetCode 完成做题后，回复 **AC** 或 **WA**（或描述结果）"
            ),
        })
    else:
        state = app.invoke(state)
        state = app.invoke("ask_question", state)
        st.session_state.messages.append({
            "role": "assistant",
            "content": f"**【{POOL_DISPLAY.get(state['current_pool'], state['current_pool'])}】**\n\n{state.get('current_question', '')}"
        })

    st.session_state.state = state
    st.session_state.started = True
    st.session_state.finished = False
    st.session_state.report = None


def handle_answer(raw: str):
    app = st.session_state.app
    state = st.session_state.state

    if raw in ("退出", "quit", "exit"):
        state["pending_answer"] = "[候选人主动退出]"
        state = app.invoke("receive_answer", state)
        st.session_state.state = state
        st.session_state.finished = True
        _compile_and_show_report()
        return

    if state["current_pool"] == "algorithm":
        algo_status = _parse_algorithm_result(raw)
        state["_algorithm_status"] = algo_status
        state["pending_answer"] = f"[LeetCode {algo_status}] {raw}"

        # 记录到 history（无 LLM 调用）
        history = state.get("history", [])
        meta = state.get("_algorithm_meta", {})
        history.append({
            "question": state.get("current_question", ""),
            "answer": f"[LeetCode {algo_status}] {raw}",
            "followups": [],
            "differentiating_value": "LOW",
        })
        state["history"] = history
        st.session_state.state = state

        if state.get("_interview_done"):
            _compile_and_show_report()
        else:
            state = app.invoke("advance_pool", state)
            if not state.get("_interview_done"):
                state = app.invoke("select_question", state)
                state = app.invoke("ask_question", state)
                pool_label = POOL_DISPLAY.get(state["current_pool"], state["current_pool"])
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": (
                        f"\n---\n**【{pool_label}】**\n\n"
                        f"{state.get('current_question', '')}\n\n"
                        "💡 请回答"
                    ),
                })
            st.session_state.state = state
        return

    # fundamentals / scenario 路径
    if raw in ("跳过",):
        state["pending_answer"] = "[候选人跳过此题]"
    else:
        state["pending_answer"] = raw

    state = app.invoke("receive_answer", state)

    while True:
        routing = app.invoke("should_followup", state)
        if routing == "score_answer":
            state = app.invoke("score_answer", state)
            break

        state = app.invoke("generate_followup", state)
        followup_q = state.get("current_question", "")
        st.session_state.messages.append({"role": "assistant", "content": f"**追问：** {followup_q}"})
        st.session_state.state = state
        return

    st.session_state.state = state

    if state.get("_interview_done"):
        _compile_and_show_report()
    else:
        state = app.invoke("advance_pool", state)
        if not state.get("_interview_done"):
            state = app.invoke("select_question", state)
            state = app.invoke("ask_question", state)
            pool_label = POOL_DISPLAY.get(state["current_pool"], state["current_pool"])
            st.session_state.messages.append({
                "role": "assistant",
                "content": f"\n---\n**【{pool_label}】**\n\n{state.get('current_question', '')}"
            })
        st.session_state.state = state


def _compile_and_show_report():
    app = st.session_state.app
    state = st.session_state.state
    state = app.invoke("compile_report", state)
    st.session_state.report = state.get("_report", {})
    st.session_state.finished = True


st.set_page_config(page_title="面试 Agent", page_icon="🎯", layout="wide")

init_state()

st.title("🎯 面试 Agent")
st.caption("algorithm → fundamentals → scenario")

with st.sidebar:
    st.header("面试配置")
    profile = st.text_input("岗位描述", value="Java后端工程师")
    start_pool = st.selectbox("起始题池", POOL_ORDER, index=0)
    if st.button("🚀 开始面试", type="primary"):
        start_interview(profile, start_pool)
        st.rerun()

if not st.session_state.started:
    st.info("👈 在左侧填好配置，点击「开始面试」启动")
else:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if not st.session_state.finished:
        if prompt := st.chat_input("候选人回答"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            handle_answer(prompt)
            st.rerun()
    else:
        report = st.session_state.report
        if report:
            st.divider()
            st.subheader("📋 面试报告")
            col1, col2, col3 = st.columns(3)
            col1.metric("总分", f"{report.get('total_score', 0)} / 100")
            col2.metric("场景题得分", f"{report.get('scenario_score', 0)} / 40")
            if report.get("peak_chains"):
                pc = report["peak_chains"][0]
                col3.metric("峰值链", f"{pc['rounds']}轮 (+{pc['peak_bonus']}分)")
            if report.get("strong_points"):
                st.markdown("**✨ 亮点：**")
                for pt in report["strong_points"]:
                    st.markdown(f"- {pt}")
            if report.get("weak_points"):
                st.markdown("**⚠️ 薄弱点：**")
                for pt in report["weak_points"]:
                    st.markdown(f"- {pt}")
            if st.button("🔄 重新开始"):
                st.session_state.started = False
                st.session_state.finished = False
                st.session_state.messages = []
                st.session_state.state = None
                st.rerun()