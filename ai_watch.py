"""Render the AI Watch panel from dated Markdown digests and wiki JSON."""

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from saved_items import item_controls

AUTO_DIR = Path(__file__).resolve().parent
AI_DIGEST_DIR = AUTO_DIR / "ai-watch-digests"
WIKI_FILE = AUTO_DIR / "ai-watch-wiki.json"

SECTIONS = [
    ("Model Releases & Agentic Capabilities", "releases", "Releases"),
    ("Performance & Benchmarks", "performance", "Performance"),
    ("Local LLMs", "local", "Local LLMs"),
    ("AI in Research", "research", "Research"),
    ("Community Views", "community", "Community"),
]
LINK_RE = re.compile(r"^-\s*\[(?P<title>.+?)\]\((?P<url>https?://[^)]+)\)\s*(?:—|--|-)?\s*(?P<note>.*)$")


def esc(value):
    return html.escape(str(value), quote=True)


def safe_url(value):
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") and parsed.netloc else ""


def parse_digest(path):
    sections = {key: [] for _, key, _ in SECTIONS}
    heading_to_key = {heading: key for heading, key, _ in SECTIONS}
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
                sections[current].append({
                    "title": match.group("title"),
                    "url": url,
                    "note": match.group("note").strip(),
                })
    return {"date": path.stem, "sections": sections}


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
    files = sorted(AI_DIGEST_DIR.glob("????-??-??.md"), reverse=True) if AI_DIGEST_DIR.is_dir() else []
    digests = [parse_digest(path) for path in files]
    latest = digests[0]["date"] if digests else "not scanned yet"
    total = sum(len(items) for digest in digests for items in digest["sections"].values())
    out = [f'<div class="sub ai-sub">Latest AI scan <strong>{esc(latest)}</strong> · {len(digests)} scan(s) · {total} linked items</div>']
    out.append('<p class="ai-intro">Model releases, agent benchmarks, locally runnable models, research uses, and public discussion. Performance claims link to their test conditions; community views are labeled as opinions.</p>')
    out.append(render_wiki())
    out.append('<h2 class="shead">AI Scan History</h2>')
    if not digests:
        out.append('<p class="empty">The first AI scan has not run yet.</p>')
    for index, digest in enumerate(digests):
        count = sum(len(v) for v in digest["sections"].values())
        counts = " · ".join(f"{len(digest['sections'][key])} {label.lower()}" for _, key, label in SECTIONS if digest["sections"][key]) or "no new linked items"
        out.append(f'<details class="card"{" open" if index == 0 else ""}><summary><span class="date">{esc(digest["date"])}</span><span class="n">{count}</span><span class="counts">{esc(counts)}</span></summary><div class="body">')
        if not count:
            out.append('<p class="empty">No new linked items in this scan.</p>')
        for heading, key, label in SECTIONS:
            items = digest["sections"][key]
            if not items:
                continue
            out.append(f'<h3>{esc(heading)}</h3><ul class="items">')
            for item in items:
                out.append(f'<li class="item"><span class="tag {key}">{esc(label)}</span><a class="t" href="{esc(item["url"])}" target="_blank" rel="noopener">{esc(item["title"])}</a>')
                out.append(item_controls("ai", label, key, item["title"], item["url"], item["note"], digest["date"]))
                if item["note"]:
                    out.append(f'<p class="note">{esc(item["note"])}</p>')
                out.append('</li>')
            out.append('</ul>')
        out.append('</div></details>')
    return "".join(out)
