"""爬取 LeetCode 提交页面，解析 AC/WA 状态。"""

import re
from urllib.parse import urlparse

import httpx

SUBMISSION_URL_RE = re.compile(
    r"leetcode\.com/problems/([^/]+)/submissions/(\d+)"
)


def _parse_submission_page(html: str) -> dict:
    status_map = {
        "Accepted": "AC",
        "Wrong Answer": "WA",
        "Time Limit Exceeded": "TLE",
        "Memory Limit Exceeded": "MLE",
        "Runtime Error": "RE",
    }
    for label, code in status_map.items():
        pattern = rf'class="[^"]*text-\[#\w+\][^"]*">\s*{label}\s*<'
        if re.search(pattern, html, re.IGNORECASE):
            return {"status": code}

    for label, code in status_map.items():
        if label in html:
            return {"status": code}

    return {"status": "UNKNOWN", "raw_hint": html[:500]}


def scrape_submission(url: str) -> dict:
    match = SUBMISSION_URL_RE.search(url)
    if match:
        slug = match.group(1)
        submission_id = match.group(2)
        target_url = f"https://leetcode.com/problems/{slug}/submissions/{submission_id}/"
    else:
        parsed = urlparse(url)
        if "/problems/" in parsed.path:
            parts = parsed.path.split("/problems/")
            if len(parts) > 1:
                slug = parts[1].strip("/")
                target_url = f"https://leetcode.com/problems/{slug}/submissions/"
            else:
                raise ValueError(f"无法解析 LeetCode URL: {url}")
        else:
            raise ValueError(f"无法解析 LeetCode URL: {url}")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    client = httpx.Client(trust_env=False, timeout=15.0)
    try:
        resp = client.get(target_url, headers=headers)
        resp.raise_for_status()
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}
    finally:
        client.close()

    result = _parse_submission_page(resp.text)
    result["url"] = target_url
    result["slug"] = slug
    return result
