#!/usr/bin/env python3
"""
Generate scenario questions by calling MiniMax LLM in-process.
Each question is written to disk immediately after generation (no accumulation).

Usage:
    uv run python scripts/generate_scenario_questions.py --count 10 --category foundation
    uv run python scripts/generate_scenario_questions.py --count 10 --category business
    uv run python scripts/generate_scenario_questions.py --count 20   # both categories
"""
import argparse
import json
import re
import sys
import traceback
from pathlib import Path

# Add project root to path so we can import interview_agent.llm
sys.path.insert(0, str(Path(__file__).parent.parent))

from interview_agent.llm import generate

# ─── Schema ────────────────────────────────────────────────────────────────────

SCHEMA_FIELDS = [
    "id", "pool", "category", "difficulty", "seed",
    "knowledge_anchors", "depth_trigger_pattern",
    "expected_depth", "typical_duration_rounds",
]

FOUNDATION_TOPICS = [
    "多线程与并发：线程池调参、锁粒度选择、并发容器选型",
    "缓存系统：穿透/击穿/雪崩、本地缓存+Redis双层架构、热点key处理",
    "消息队列：顺序消费保障、幂等设计、延迟队列选型（Kafka vs RocketMQ）",
    "分布式系统：一致性hash分桶、Leader选举（Raft）、分桶策略取舍",
    "JVM调优：GC频率高排查、堆外内存泄漏、Metaspace满",
    "数据库：高并发锁冲突、慢查询优化、连接池配置",
    "分布式锁：Redisson实现、锁超时与续期、脑裂防护",
    "异步编程：Future异步链、CompletableFuture编排、响应式流背压",
    "微服务治理：熔断降级（Sentinel）、超时策略、服务链路追踪",
    "性能分析：接口耗时火焰图、OOM快速定位、N+1查询检测",
]

BUSINESS_TOPICS = [
    "酒店预订库存：预扣库存+超时释放、超售防护、状态机流转",
    "价格计算：汇率动态切换、促销叠加规则、差价保护机制",
    "订单幂等：全局幂等Token、状态机防重复提交、退款补偿事务",
    "供应商拉取：房源数据同步映射、动态配库优先级、价格库存冲突处理",
    "用户权益：会员等级计算、积分体系设计、优惠券核销原子性",
    "搜索排序：分页深度限制、ES打分因子、权重动态配置",
    "推送系统：设备Token管理、离线推送队列、送达率监控",
    "风控规则：IP画像、接口限流、异地登录检测",
    "结算对账：日结账务核对、分账比例计算、退款补款平账",
    "活动秒杀：库存预热、请求削峰、限购一人一单校验",
]

PROMPT_TEMPLATE = """你是一个资深面试题出题专家。请为以下话题出一道高质量场景面试题，严格按JSON格式输出，不要有多余文字，不要用markdown包裹。

话题：{topic}
难度：{difficulty}
分类：{category}

输出格式（严格JSON，不要markdown包裹）：
{{
  "id": "scenario-{category}-{idx:03d}",
  "pool": "scenario",
  "category": "{category}",
  "difficulty": "{difficulty}",
  "seed": "一个开放性问题，能自然引发2-3轮追问，中文，模拟真实面试开场",
  "knowledge_anchors": ["关键词1", "关键词2", "关键词3"],
  "depth_trigger_pattern": "描述什么样的回答特征会触发追问（不是追问条件）",
  "expected_depth": {expected_depth},
  "typical_duration_rounds": {typical_rounds}
}}

要求：
- seed 必须是中文，模拟真实面试场景，不暴露答案不给提示
- knowledge_anchors 包含3-6个候选人应该自然提及的概念
- depth_trigger_pattern 描述的是候选人回答中的特征，不是AI的追问逻辑
- difficulty 固定为 hard（foundation）或 medium（business）"""


def build_prompt(topic: str, category: str, idx: int) -> str:
    difficulty = "hard" if category == "foundation" else "medium"
    expected_depth = 3 if category == "foundation" else 2
    typical_rounds = 3 if category == "foundation" else 2
    return PROMPT_TEMPLATE.format(
        topic=topic,
        category=category,
        difficulty=difficulty,
        expected_depth=expected_depth,
        typical_rounds=typical_rounds,
        idx=idx,
    )


def parse_json(raw: str) -> dict | None:
    """Strip markdown fences then parse JSON."""
    cleaned = re.sub(r"```(?:json)?\s*", "", raw.strip())
    cleaned = re.sub(r"\s*```", "", cleaned.strip())
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None


def validate(q: dict, idx: int, category: str) -> list[str]:
    """Return list of error strings; empty list = valid."""
    errors = []
    for field in SCHEMA_FIELDS:
        if field not in q or q[field] is None:
            errors.append(f"[{idx}] missing field: {field}")
    if q.get("pool") != "scenario":
        errors.append(f"[{idx}] pool must be 'scenario'")
    if q.get("category") != category:
        errors.append(f"[{idx}] category must be '{category}'")
    if q.get("difficulty") not in ("hard", "medium"):
        errors.append(f"[{idx}] difficulty must be 'hard' or 'medium'")
    if not isinstance(q.get("knowledge_anchors", []), list):
        errors.append(f"[{idx}] knowledge_anchors must be a list")
    elif not (3 <= len(q["knowledge_anchors"]) <= 6):
        errors.append(f"[{idx}] knowledge_anchors must have 3-6 items, got {len(q['knowledge_anchors'])}")
    return errors


def write_questions(questions: list[dict], out_path: Path, category: str):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding="utf-8"))
    # Deduplicate by id
    existing_ids = {q["id"] for q in existing}
    new_ones = [q for q in questions if q["id"] not in existing_ids]
    all_q = existing + new_ones
    out_path.write_text(json.dumps(all_q, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Wrote {len(new_ones)} new questions → {out_path} (total: {len(all_q)})")
    return len(new_ones)


def generate_one(topic: str, category: str, idx: int, max_retries: int = 2) -> dict | None:
    prompt = build_prompt(topic, category, idx)
    for attempt in range(max_retries):
        try:
            resp = generate(system="你是一个资深面试题出题专家。", user=prompt, model="claude-sonnet")
            parsed = parse_json(resp.raw)
            if parsed is None:
                print(f"    [WARN] Failed to parse JSON (attempt {attempt+1}/{max_retries})", file=sys.stderr)
                continue
            errors = validate(parsed, idx, category)
            if errors:
                print(f"    [WARN] Validation errors: {errors}", file=sys.stderr)
                continue
            return parsed
        except Exception:
            traceback.print_exc()
            print(f"    [WARN] Generation error (attempt {attempt+1}/{max_retries})", file=sys.stderr)
    return None


def run_category(category: str, topics: list[str], out_path: Path):
    print(f"\n{'='*60}")
    print(f"Generating {category} ({len(topics)} questions)...")
    questions = []
    for i, topic in enumerate(topics, start=1):
        print(f"  [{i}/{len(topics)}] {topic[:30]}...")
        q = generate_one(topic, category, i)
        if q:
            questions.append(q)
            print(f"    ✓ {q['id']} — seed: {q['seed'][:40]}...")
        else:
            print(f"    ✗ FAILED after {2} retries, skipping", file=sys.stderr)
        # Write immediately after each question
        if q:
            write_questions([q], out_path, category)

    print(f"\nDone: {len(questions)}/{len(topics)} questions generated for {category}")
    return questions


def main():
    parser = argparse.ArgumentParser(description="Generate scenario questions via LLM")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--category", default="both",
                        choices=["foundation", "business", "both"])
    parser.add_argument("--out", default="questions/scenario")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent / args.out
    base_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    if args.category in ("foundation", "both"):
        topics = FOUNDATION_TOPICS[:args.count]
        out_path = base_dir / "foundation" / "foundation-001.json"
        results["foundation"] = run_category("foundation", topics, out_path)

    if args.category in ("business", "both"):
        topics = BUSINESS_TOPICS[:args.count]
        out_path = base_dir / "business" / "business-001.json"
        results["business"] = run_category("business", topics, out_path)

    total = sum(len(v) for v in results.values())
    print(f"\n{'='*60}")
    print(f"ALL DONE: {total} scenario questions generated")
    for cat, qs in results.items():
        print(f"  {cat}: {len(qs)} questions")


if __name__ == "__main__":
    main()