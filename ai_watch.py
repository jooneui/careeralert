"""Render the AI Watch panel from dated Markdown digests and wiki JSON.

parse_feed_digest() and render_feed_history() are shared with transport_news.py.
"""

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from saved_items import item_controls

AUTO_DIR = Path(__file__).resolve().parent
AI_DIGEST_DIR = AUTO_DIR / "ai-watch-digests"
WIKI_FILE = AUTO_DIR / "ai-watch-wiki.json"

# (heading in the .md, css/state key, short label)
SECTIONS = [
    ("Model Releases & Agentic Capabilities", "releases", "Releases"),
    ("Performance & Benchmarks", "performance", "Performance"),
    ("Local LLMs", "local", "Local LLMs"),
    ("AI in Research", "research", "Research"),
    ("Leaders on AI's Future", "leaders", "Outlook"),
    ("Community Views", "community", "Community"),
]
LINK_RE = re.compile(r"^-\s*\[(?P<title>.+?)\]\((?P<url>https?://[^)]+)\)\s*(?:—|--|-)?\s*(?P<note>.*)$")


def esc(value):
    return html.escape(str(value), quote=True)


def safe_url(value):
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc else ""


def parse_feed_digest(path, sections):
    out = {key: [] for _, key, _ in sections}
    heading_to_key = {heading: key for heading, key, _ in sections}
    current = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            current = heading_to_key.get(line[3:].strip())
            continue
        if current is None:
            continue
        match = LINK_RE.match(line)
        if match:
            url = safe_url(match.group("url"))
            if url:
                out[current].append({
                    "title": match.group("title"),
                    "url": url,
                    "note": match.group("note").strip(),
                })
    return {"date": path.stem, "sections": out}


def load_feed(digest_dir, sections):
    files = sorted(digest_dir.glob("????-??-??.md"), reverse=True) if digest_dir.is_dir() else []
    return [parse_feed_digest(path, sections) for path in files]


def render_feed_history(digests, sections, source, heading):
    out = [f'<h2 class="shead">{esc(heading)}</h2>']
    if not digests:
        out.append('<p class="empty">The first scan has not run yet.</p>')
    for index, digest in enumerate(digests):
        count = sum(len(v) for v in digest["sections"].values())
        counts = " · ".join(
            f"{len(digest['sections'][key])} {label.lower()}"
            for _, key, label in sections if digest["sections"][key]
        ) or "no new linked items"
        out.append(f'<details class="card"{" open" if index == 0 else ""}><summary><span class="date">{esc(digest["date"])}</span><span class="n">{count}</span><span class="counts">{esc(counts)}</span></summary><div class="body">')
        if not count:
            out.append('<p class="empty">No new linked items in this scan.</p>')
        for section_heading, key, label in sections:
            items = digest["sections"][key]
            if not items:
                continue
            out.append(f'<h3>{esc(section_heading)}</h3><ul class="items">')
            for item in items:
                out.append(f'<li class="item"><span class="tag {key}">{esc(label)}</span><a class="t" href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["title"])}</a>')
                out.append(item_controls(source, label, key, item["title"], item["url"], item["note"], digest["date"]))
                if item["note"]:
                    out.append(f'<p class="note">{esc(item["note"])}</p>')
                out.append('</li>')
            out.append('</ul>')
        out.append('</div></details>')
    return "".join(out)


def render_wiki():
    if not WIKI_FILE.exists():
        return ""
    try:
        data = json.loads(WIKI_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return '<p class="empty">AI Wiki could not be loaded. Check automation/ai-watch-wiki.json.</p>'
    parts = ['<section class="panel ai-wiki"><h2>AI Wiki <span class="psub">Quick guide and primary sources</span></h2>']
    parts.append('<div class="wiki-grid">')
    for topic in data.get("topics", []):
        parts.append(f'<article class="wiki-topic"><h3>{esc(topic.get("title", ""))}</h3>')
        parts.append(f'<p class="note">{esc(topic.get("summary", ""))}</p>')
        links = []
        for link in topic.get("links", []):
            url = safe_url(link.get("url", ""))
            if url:
                links.append(f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(link.get("label", "Source"))}</a>')
        if links:
            parts.append(f'<p class="wiki-links">{" · ".join(links)}</p>')
        parts.append("</article>")
    parts.append('</div><p class="foot">Edit <code>automation/ai-watch-wiki.json</code> to update this guide.</p></section>')
    return "".join(parts)


def render():
    digests = load_feed(AI_DIGEST_DIR, SECTIONS)
    latest = digests[0]["date"] if digests else "not scanned yet"
    total = sum(len(items) for digest in digests for items in digest["sections"].values())
    out = [f'<div class="sub ai-sub">Latest AI scan <strong>{esc(latest)}</strong> · {len(digests)} scan(s) · {total} linked items</div>']
    out.append('<p class="ai-intro">Model releases, agent benchmarks, locally runnable models, research uses, what AI-company leaders and prominent researchers say about where AI is heading, and public discussion. Performance claims link to their test conditions; leader statements and community views are labeled as opinions.</p>')
    out.append(render_wiki())
    out.append(render_feed_history(digests, SECTIONS, "ai", "AI Scan History"))
    return "".join(out)
