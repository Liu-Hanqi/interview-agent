#!/usr/bin/env python3
import json
import re
import time
import random
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.xiaolincoding.com"
CATEGORIES = ["tcp", "udp", "http", "https", "socket"]
DEFAULT_DIFFICULTY = "medium"
HEADERS_POOL = [
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"},
]
DELAY = 1.5


def random_headers() -> dict:
    return random.choice(HEADERS_POOL).copy()


def fetch_page(url: str) -> str:
    session = requests.Session()
    for attempt in range(3):
        try:
            resp = session.get(url, headers=random_headers(), timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt == 2:
                raise RuntimeError(f"Failed to fetch {url}") from e
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def extract_qa_from_html(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    questions = []
    counter = 1

    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        if any(kw in text for kw in ["目录", "导航", "相关", "推荐", "评论"]):
            continue

        next_elem = tag.find_next_sibling()
        answer_parts = []
        answer_str = ""
        while next_elem:
            if next_elem.name in ["h2", "h3"]:
                break
            if next_elem.name in ["p", "li"]:
                part_text = next_elem.get_text(strip=True)
                answer_parts.append(part_text)
                answer_str += part_text + " "
            next_elem = next_elem.find_next_sibling()

        seed = text
        if not re.search(r"[？?]", seed):
            seed = seed + "？"

        knowledge_anchors = [category]
        for c in CATEGORIES:
            if c in answer_str.lower():
                knowledge_anchors.append(c)

        questions.append({
            "id": f"{category}-{counter:03d}",
            "pool": "fundamentals",
            "category": category,
            "difficulty": DEFAULT_DIFFICULTY,
            "seed": seed,
            "knowledge_anchors": list(set(knowledge_anchors)),
        })
        counter += 1

    return questions


def save_questions(questions: list[dict], category: str, output_dir: Path):
    output_dir = output_dir / category
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{category}-001.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(questions)} questions → {out_path.name}")


def main():
    questions_dir = Path(__file__).parent.parent / "questions" / "fundamentals"
    topics = {
        "tcp": "/network/3_tcp/tcp_interview.html",
        "http": "/network/2_http/http_interview.html",
        "https": "/network/2_http/https_rsa.html",
        "ip": "/network/4_ip/ip_base.html",
        "network-base": "/network/1_base/tcp_ip_model.html",
    }
    for category, path in topics.items():
        print(f"Scraping {category}...")
        try:
            html = fetch_page(BASE_URL + path)
            qs = extract_qa_from_html(html, category)
            print(f"  Found {len(qs)} questions")
            save_questions(qs, category, questions_dir)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(DELAY)


if __name__ == "__main__":
    main()