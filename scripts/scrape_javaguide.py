#!/usr/bin/env python3
import json
import re
import time
import random
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://javaguide.cn"
CATEGORY_MAP = {
    "Java基础": "java-basic",
    "JVM": "jvm",
    "并发": "concurrency",
    "MySQL": "mysql",
    "计算机网络": "network",
}
DEFAULT_DIFFICULTY = "medium"
HEADERS_POOL = [
    {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "X-Captcha-Code": "8888",
    },
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Captcha-Code": "8888",
    },
    {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "X-Captcha-Code": "8888",
    },
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
            # JavaGuide 的 HTML 声明了 utf-8 但服务器返回 ISO-8859-1，强制覆盖
            resp.encoding = "utf-8"
            return resp.text
        except requests.RequestException as e:
            if attempt == 2:
                raise RuntimeError(f"Failed to fetch {url} after 3 attempts") from e
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def extract_qa_from_html(html: str, topic: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    questions = []

    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        if any(kw in text for kw in ["目录", "导航", "相关", "推荐", "评论", "上一页", "下一页"]):
            continue

        next_elem = tag.find_next_sibling()
        answer_parts = []
        while next_elem:
            if next_elem.name in ["h2", "h3"]:
                break
            if next_elem.name in ["p", "li"]:
                answer_parts.append(next_elem.get_text(strip=True))
            next_elem = next_elem.find_next_sibling()

        seed = text
        if seed.startswith("#"):
            seed = re.sub(r"^#+\s*", "", seed).strip()
        if not re.search(r"[？?]", seed):
            seed = seed + "？"

        knowledge_anchors = [topic]
        answer_text = " ".join(answer_parts)
        known_anchors = [
            "类加载器", "运行时数据区", "执行引擎", "GC", "堆", "栈",
            "乐观锁", "悲观锁", "ReentrantLock", "synchronized",
            "ThreadLocal", "volatile", "final",
            "TCP", "UDP", "HTTP", "HTTPS", "三次握手", "四次挥手",
            "索引", "B+树", "事务", "MVCC", "redo log", "undo log",
        ]
        for anchor in known_anchors:
            if anchor in answer_text:
                knowledge_anchors.append(anchor)

        questions.append({
            "id": "",
            "pool": "fundamentals",
            "category": topic,
            "difficulty": DEFAULT_DIFFICULTY,
            "seed": seed,
            "knowledge_anchors": list(set(knowledge_anchors)),
        })

    return questions


def save_questions(questions: list[dict], category: str, output_dir: Path):
    output_dir = output_dir / category
    output_dir.mkdir(parents=True, exist_ok=True)

    counter = 1
    batch = []
    for q in questions:
        q["id"] = f"{category}-{counter:03d}"
        batch.append(q)
        if len(batch) >= 50:
            _write_batch(batch, output_dir, category, counter)
            batch = []
        counter += 1
    if batch:
        _write_batch(batch, output_dir, category, counter)


def _write_batch(batch: list[dict], output_dir: Path, category: str, start: int):
    file_index = (start - 1) // 50 + 1
    out_path = output_dir / f"{category}-{file_index:03d}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {len(batch)} questions → {out_path.name}")


def main():
    questions_dir = Path(__file__).parent.parent / "questions" / "fundamentals"
    topics_url = {
        "Java基础": "/java/basis/java-basic-questions-01.html",
        "JVM": "https://interview.javaguide.cn/java/java-jvm.html",
        "并发": "/java/concurrent/java-concurrent-questions-01.html",
        "MySQL": "/database/mysql/mysql-questions-01.html",
        "计算机网络": "/cs-basics/network/other-network-questions.html",
    }

    for topic, path in topics_url.items():
        print(f"Scraping {topic}...")
        try:
            url = BASE_URL + path if path.startswith("/") else path
            html = fetch_page(url)
            qs = extract_qa_from_html(html, topic)
            print(f"  Found {len(qs)} questions")
            save_questions(qs, topic, questions_dir)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(DELAY)


if __name__ == "__main__":
    main()