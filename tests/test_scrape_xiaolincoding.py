from scripts.scrape_xiaolincoding import extract_qa_from_html


def test_extract_qa_from_html_finds_questions():
    html = """
    <html><body>
    <h2>什么是 TCP 协议？</h2>
    <p>TCP 是传输控制协议，提供可靠的面向连接的传输。</p>
    <h2>TCP 和 UDP 的区别是什么？</h2>
    <p>TCP 可靠有序，UDP 不可靠但速度快。</p>
    </body></html>
    """
    qs = extract_qa_from_html(html, "tcp")
    assert len(qs) == 2
    assert "TCP" in qs[0]["seed"]
    assert qs[0]["category"] == "tcp"
    assert "tcp" in qs[0]["knowledge_anchors"]


def test_extract_qa_skips_navigation():
    html = """
    <html><body>
    <h2>目录</h2><p>...</p>
    <h2>相关推荐</h2><p>...</p>
    <h2>HTTP 协议的特点是什么？</h2>
    <p>HTTP 是无状态的应用层协议。</p>
    </body></html>
    """
    qs = extract_qa_from_html(html, "http")
    assert len(qs) == 1
    assert "HTTP" in qs[0]["seed"]