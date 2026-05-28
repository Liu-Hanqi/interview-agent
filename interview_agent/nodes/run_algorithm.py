"""Algorithm 题池节点 — 随机选题，不调用 LLM。"""

import json
import random
from pathlib import Path

from interview_agent.state import InterviewState


def run_algorithm(state: InterviewState) -> InterviewState:
    """从 algorithm 题池随机选一题，写入 state['current_question']。

    JSON 结构（来自 scrape_leetcode.py）：
    {
      "id": "algorithm-3936",
      "pool": "algorithm",
      "category": "easy",
      "difficulty": "easy",
      "seed": "Minimum Swaps to Move Zeros to End",
      "knowledge_anchors": [],
      "title_slug": "minimum-swaps-to-move-zeros-to-end",
      "leetcode_id": 3936,
      "ac_rate": 0.6056,
      "total_acs": 29081,
      "total_submitted": 48017,
      "url": "https://leetcode.com/problems/minimum-swaps-to-move-zeros-to-end/"
    }
    """
    pool_dir = Path(__file__).parent.parent.parent / "questions" / "algorithm"
    json_files = list(pool_dir.glob("*.json"))

    questions = []
    for f in json_files:
        try:
            data = json.loads(f.read_text())
            if isinstance(data, list):
                questions.extend(data)
            elif isinstance(data, dict):
                questions.append(data)
        except Exception:
            continue

    if not questions:
        raise RuntimeError("algorithm 题池为空，请先运行 scrape_leetcode.py")

    picked = random.choice(questions)

    # 转换 ac_rate 小数为百分比显示
    ac_rate = picked.get("ac_rate", 0)
    if isinstance(ac_rate, float) and ac_rate <= 1:
        ac_rate_str = f"{ac_rate * 100:.1f}%"
    else:
        ac_rate_str = str(ac_rate)

    # slug 转标题格式：minimum-swaps-to-move-zeros-to-end → "Minimum Swaps to Move Zeros to End"
    slug = picked.get("title_slug", "")
    title = slug.replace("-", " ").title() if slug else picked.get("seed", "Unknown")

    q_text = (
        f"📋 {title}\n"
        f"🔗 {picked.get('url', '')}\n"
        f"⭐ 难度：{picked.get('difficulty', 'N/A')}\n"
        f"📊 通过率：{ac_rate_str}\n"
        f"🏷️ 标签：{', '.join(picked.get('knowledge_anchors', []) or ['无'])}"
    )

    state["current_question"] = q_text
    state["current_pool"] = "algorithm"
    state["_algorithm_meta"] = {
        "slug": slug,
        "leetcode_id": picked.get("leetcode_id"),
        "title": title,
        "seed": picked.get("seed", ""),
        "difficulty": picked.get("difficulty", ""),
        "url": picked.get("url", ""),
        "ac_rate": ac_rate_str,
    }

    return state