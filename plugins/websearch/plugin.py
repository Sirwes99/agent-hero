import html
import re

import requests

from agenthero.common import truncate

UA = "Mozilla/5.0 (Windows NT 10.0; Win64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def _unredirect(url):
    """Resolve DuckDuckGo's //duckduckgo.com/l/?uddg=... redirect wrapper."""
    if "uddg=" in url:
        from urllib.parse import parse_qs, urlparse

        q = parse_qs(urlparse(url).query)
        return html.unescape(q.get("uddg", [url])[0])
    return url


def _ddg(query):
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": UA},
        timeout=30,
    )
    resp.raise_for_status()
    results = []
    for block in re.split(r'<h2 class="result__title">', resp.text)[1:]:
        m_a = re.search(r'class="result__a"[^>]*href="(.*?)"[^>]*>(.*?)</a>', block, re.S)
        if not m_a:
            continue
        url = _unredirect(html.unescape(m_a.group(1)))
        title = re.sub(r"<[^>]+>", "", m_a.group(2)).strip()
        m_s = re.search(r'class="result__snippet">(.*?)</div>', block, re.S)
        snippet = re.sub(r"<[^>]+>", "", m_s.group(1)).strip() if m_s else ""
        results.append({"title": title, "url": url, "snippet": snippet})
    return results


def _to_text(html_doc):
    html_doc = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html_doc, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", html_doc)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def handle(tool_name, args):
    if tool_name == "web_search":
        query = str(args.get("query", "")).strip()
        if not query:
            return "ERROR: 'query' is required"
        max_results = int(args.get("max_results", 8))
        try:
            results = _ddg(query)[:max_results]
        except Exception as e:
            return f"ERROR: search failed: {e}"
        if not results:
            return "No results found."
        lines = [
            f"{i + 1}. {r['title']}\n   {r['url']}\n   {truncate(r['snippet'], 300)}"
            for i, r in enumerate(results)
        ]
        return "\n".join(lines)

    if tool_name == "fetch_url":
        url = str(args.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            return "ERROR: url must start with http(s)://"
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=60)
            resp.raise_for_status()
            text = _to_text(resp.text)
            return truncate(text, int(args.get("max_chars", 20000)))
        except Exception as e:
            return f"ERROR: fetch failed: {e}"

    return f"ERROR: unknown tool '{tool_name}' in plugin 'websearch'"
