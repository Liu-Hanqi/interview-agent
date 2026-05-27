#!/usr/bin/env python3
"""
Scrape LeetCode problem list via public API (no auth required).

Output: questions/algorithm/algorithm-{easy,medium,hard}.json
Each file contains problem objects with id/title/slug/difficulty/ac_rate.
"""
import json
import time
from pathlib import Path

import requests

BASE_URL = "https://leetcode.com"
API_URL = f"{BASE_URL}/api/problems/all/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}
DIFFICULTY_MAP = {1: "easy", 2: "medium", 3: "hard"}
OUT_BASE = Path(__file__).parent.parent / "questions" / "algorithm"


def fetch_all() -> list[dict]:
    print("Fetching LeetCode problem list...")
    session = requests.Session()
    session.trust_env = False  # disable system-proxy so we connect directly
    resp = session.get(API_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    pairs = data.get("stat_status_pairs", [])
    print(f"  Total problems: {len(pairs)}")
    return pairs


def transform(pairs: list[dict]) -> dict[str, list[dict]]:
    by_difficulty = {"easy": [], "medium": [], "hard": []}
    for i, pair in enumerate(pairs, start=1):
        stat = pair.get("stat", {})
        diff_level = pair.get("difficulty", {}).get("level", 0)
        difficulty = DIFFICULTY_MAP.get(diff_level, "medium")
        qid = stat.get("frontend_question_id", i)
        title = stat.get("question__title", "")
        slug = stat.get("question__title_slug", "")
        total_acs = stat.get("total_acs", 0)
        total_submitted = stat.get("total_submitted", 1)
        ac_rate = round(total_acs / total_submitted, 4) if total_submitted > 0 else 0.0

        question = {
            "id": f"algorithm-{qid}",
            "pool": "algorithm",
            "category": difficulty,
            "difficulty": difficulty,
            "seed": title,
            "knowledge_anchors": [],  # LeetCode doesn't provide topic tags via this API
            "title_slug": slug,
            "leetcode_id": qid,
            "ac_rate": ac_rate,
            "total_acs": total_acs,
            "total_submitted": total_submitted,
            "url": f"{BASE_URL}/problems/{slug}/",
        }
        by_difficulty[difficulty].append(question)

    return by_difficulty


def save(by_difficulty: dict[str, list[dict]]):
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    for difficulty, questions in by_difficulty.items():
        out_path = OUT_BASE / f"algorithm-{difficulty}.json"
        out_path.write_text(
            json.dumps(questions, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"  Wrote {len(questions)} {difficulty} problems → {out_path.name}")


def main():
    pairs = fetch_all()
    by_difficulty = transform(pairs)
    save(by_difficulty)

    total = sum(len(v) for v in by_difficulty.values())
    print(f"\nDone: {total} algorithm questions saved")


if __name__ == "__main__":
    main()