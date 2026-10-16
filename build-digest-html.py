#!/usr/bin/env python3
"""Build a single browsable HTML dashboard from all digests/*.md files.

Deterministic: no network, no LLM. Safe to re-run any time.
Saved items live in browser storage and are not overwritten by this build.
Reads  : <automation>/digests/*.md
Writes : <05 Career>/career-digest.html
"""
import html
import json
import re
from datetime import date, datetime
from pathlib import Path

from ai_watch import render as render_ai_watch
from saved_items import item_controls

AUTO_DIR = Path(__file__).resolve().parent
DIGEST_DIR = AUTO_DIR / "digests"
DEADLINE_FILE = AUTO_DIR / "open-deadlines.json"
OUT_FILE = AUTO_DIR.parent / "career-digest.html"
SAVED_SCRIPT = AUTO_DIR / "saved-items.js"

# section heading in the .md  ->  (display label, css class)
CATEGORIES = [
    ("Faculty Job Postings", "faculty"),
    ("Postdoc Positions", "postdoc"),
    ("Research Institution Positions", "rinst"),
    ("Conference Deadlines / CFPs", "conf"),
    ("Journal Special Issue CFPs", "journal"),
    ("Company Job Postings", "company"),
]
LABELS = {
    "faculty": "Faculty",
    "postdoc": "Postdoc",
    "rinst": "Research Inst",
    "conf": "Conference",
    "journal": "Journal",
    "company": "Company",
}

LINK_RE = re.compile(r"^-\s*\[(?P<title>.+?)\]\((?P<url>[^)]+)\)\s*(?:—|--|-)?\s*(?P<note>.*)$")
PLAIN_RE = re.compile(r"^-\s*(?P<note>.+)$")
DEADLINE_RE = re.compile(r"Deadline:\s*(?P<dl>.+?)\s*$", re.IGNORECASE)
EMPTY_RE = re.compile(r"no new items", re.IGNORECASE)


def parse_digest(path):
    """-> {'date': str, 'sections': {cls: [item, ...]}}"""
    sections = {cls: [] for _, cls in CATEGORIES}
    heading_to_cls = {h: c for h, c in CATEGORIES}
    current = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            current = heading_to_cls.get(line[3:].strip())
            continue
        if not line.startswith("-") or current is None:
            continue
        if EMPTY_RE.search(line):
            continue

        m = LINK_RE.match(line)
        if m:
            note = m.group("note").strip()
            title, url = m.group("title").strip(), m.group("url").strip()
        else:
            m = PLAIN_RE.match(line)
            if not m:
                continue
            note = m.group("note").strip()
            title, url = None, None

        deadline = None
        dm = DEADLINE_RE.search(note)
        if dm:
            deadline = dm.group("dl").rstrip(".")
            note = note[: dm.start()].strip().rstrip(".").rstrip(",")

        sections[current].append(
            {"title": title, "url": url, "note": note, "deadline": deadline}
        )

    return {"date": path.stem, "sections": sections}


def esc(s):
    return html.escape(s, quote=True) if s else ""


def render_item(it, cls, scan_date):
    bits = ['<li class="item">']
    bits.append(f'<span class="tag {cls}">{LABELS[cls]}</span>')
    if it["url"]:
        bits.append(
            f'<a class="t" href="{esc(it["url"])}" target="_blank" rel="noopener">{esc(it["title"])}</a>'
        )
    elif it["title"]:
        bits.append(f'<span class="t">{esc(it["title"])}</span>')
    if it["deadline"]:
        bits.append(f'<span class="dl">{esc(it["deadline"])}</span>')
    bits.append(item_controls("career", LABELS[cls], cls, it["title"], it["url"], it["note"], scan_date))
    if it["note"]:
        bits.append(f'<p class="note">{esc(it["note"])}</p>')
    bits.append("</li>")
    return "".join(bits)



CONF_BADGE = {
    "confirmed": ("verified", "ok"),
    "tentative": ("unconfirmed", "warn"),
    "expected": ("inferred", "warn"),
    "unknown": ("date unknown", "warn"),
}


def load_deadlines():
    """Open deadlines, soonest first. Past-dated entries are dropped."""
    if not DEADLINE_FILE.is_file():
        return []
    try:
        rows = json.loads(DEADLINE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    today = date.today()
    out = []
    for r in rows:
        days = None
        if r.get("deadline"):
            try:
                d = datetime.strptime(r["deadline"], "%Y-%m-%d").date()
            except ValueError:
                continue
            days = (d - today).days
            if days < 0:
                continue  # expired: stop showing it
            r["_days"] = days
            r["_label"] = d.strftime("%b %d, %Y")
        else:
            r["_days"] = None
            r["_label"] = r.get("deadline_label", "date TBA")
        out.append(r)

    # dated items first by urgency, undated afterwards
    out.sort(key=lambda r: (r["_days"] is None, r["_days"] if r["_days"] is not None else 0))
    return out


def render_deadlines(rows):
    if not rows:
        return ""

    items = []
    for r in rows:
        d = r["_days"]
        if d is None:
            urg, left = "tba", "TBA"
        elif d <= 45:
            urg, left = "hot", f"{d}d"
        elif d <= 120:
            urg, left = "soon", f"{d}d"
        else:
            urg, left = "far", f"{d}d"

        conf_txt, conf_cls = CONF_BADGE.get(r.get("confidence", ""), ("", ""))
        badge = f'<span class="conf {conf_cls}">{esc(conf_txt)}</span>' if conf_txt else ""
        save_note = f'{r.get("event", "")} · due {r["_label"]}. {r.get("note", "")}'
        controls = item_controls(
            "career", "Deadline", "deadline", r.get("title", ""),
            r.get("url", ""), save_note, date.today().isoformat(),
        )

        items.append(
            f'<li class="dlrow {urg}">'
            f'<span class="left">{esc(left)}</span>'
            f'<div class="mid">'
            f'<a class="t" href="{esc(r.get("url",""))}" target="_blank" rel="noopener">{esc(r.get("title",""))}</a>'
            f'{badge}'
            f'{controls}'
            f'<p class="note">{esc(r.get("event",""))} &nbsp;·&nbsp; due {esc(r["_label"])}</p>'
            f'<p class="note sub">{esc(r.get("note",""))}</p>'
            f'</div></li>'
        )

    hot = sum(1 for r in rows if r["_days"] is not None and r["_days"] <= 45)
    sub = f"{len(rows)} open · {hot} needing work now" if hot else f"{len(rows)} open"
    return (
        f'<section class="panel"><h2>Open Deadlines <span class="psub">{esc(sub)}</span></h2>'
        f'<ul class="dls">{"".join(items)}</ul>'
        f'<p class="foot">Shown until the date passes, whether or not it has been reported before. '
        f'Edit <code>automation/open-deadlines.json</code> to add or remove entries.</p></section>'
    )


def main():
    deadlines = load_deadlines()
    deadline_html = render_deadlines(deadlines)
    ai_html = render_ai_watch()

    files = sorted(DIGEST_DIR.glob("*.md"), reverse=True) if DIGEST_DIR.is_dir() else []
    digests = [parse_digest(p) for p in files]

    cards = []
    for i, d in enumerate(digests):
        total = sum(len(v) for v in d["sections"].values())
        counts = " · ".join(
            f"{len(d['sections'][c])} {LABELS[c].lower()}"
            for _, c in CATEGORIES
            if d["sections"][c]
        ) or "nothing new"

        body = []
        for heading, cls in CATEGORIES:
            items = d["sections"][cls]
            if not items:
                continue
            body.append(f'<h3>{esc(heading)}</h3><ul class="items">')
            body.extend(render_item(it, cls, d["date"]) for it in items)
            body.append("</ul>")
        if not body:
            body = ['<p class="empty">No new items in this scan.</p>']

        cards.append(
            f'<details class="card"{" open" if i == 0 else ""}>'
            f'<summary><span class="date">{esc(d["date"])}</span>'
            f'<span class="n">{total}</span>'
            f'<span class="counts">{esc(counts)}</span></summary>'
            f'<div class="body">{"".join(body)}</div></details>'
        )

    if not cards:
        cards = ['<p class="empty">No digests yet. The scan writes one each morning.</p>']

    latest = digests[0]["date"] if digests else "—"
    grand = sum(sum(len(v) for v in d["sections"].values()) for d in digests)
    built = datetime.now().strftime("%Y-%m-%d %H:%M")
    saved_js = SAVED_SCRIPT.read_text(encoding="utf-8")

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Career Alerts</title>
<style>
:root {{
  --bg:#f7f7f5; --card:#fff; --ink:#1a1a18; --soft:#6b6b66; --line:#e3e3df;
  --accent:#3b5bdb; --chip:#f0f0ed;
  --faculty:#2f6f4f; --conf:#8a5a1a; --journal:#5b3ea8; --company:#1f6b86;
  --hot:#c0392b; --soon:#b07415; --postdoc:#1f6b5c; --rinst:#8a3a5e;
}}
@media (prefers-color-scheme:dark) {{
  :root:not([data-theme="light"]) {{
    --bg:#16161a; --card:#1e1e24; --ink:#eceCea; --soft:#9a9a96; --line:#2e2e36;
    --accent:#8aa2ff; --chip:#26262e;
    --faculty:#7fd6a6; --conf:#e0b473; --journal:#b9a2f0; --company:#79c9e6;
    --hot:#d9534f; --soon:#c98b2e; --postdoc:#6fd0bc; --rinst:#e89ab8;
  }}
}}
:root[data-theme="dark"] {{
  --bg:#16161a; --card:#1e1e24; --ink:#ececea; --soft:#9a9a96; --line:#2e2e36;
  --accent:#8aa2ff; --chip:#26262e;
  --faculty:#7fd6a6; --conf:#e0b473; --journal:#b9a2f0; --company:#79c9e6;
  --hot:#d9534f; --soon:#c98b2e; --postdoc:#6fd0bc; --rinst:#e89ab8;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
 padding:32px 16px 64px}}
.wrap{{max-width:860px;margin:0 auto}}
header{{margin-bottom:28px}}
h1{{font-size:25px;margin:0 0 6px;letter-spacing:-.01em}}
.sub{{color:var(--soft);font-size:13.5px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;
 margin-bottom:12px;overflow:hidden}}
summary{{cursor:pointer;padding:14px 16px;display:flex;align-items:center;gap:12px;
 list-style:none;font-weight:600}}
summary::-webkit-details-marker{{display:none}}
summary:hover{{background:var(--chip)}}
.date{{font-variant-numeric:tabular-nums}}
.n{{background:var(--accent);color:#fff;border-radius:999px;padding:1px 9px;
 font-size:12px;font-weight:700;min-width:24px;text-align:center}}
.counts{{color:var(--soft);font-weight:400;font-size:13px;margin-left:auto;
 text-align:right}}
.body{{padding:4px 16px 18px;border-top:1px solid var(--line)}}
h3{{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--soft);
 margin:20px 0 10px}}
.items{{list-style:none;margin:0;padding:0}}
.item{{padding:11px 0;border-bottom:1px solid var(--line)}}
.item:last-child{{border-bottom:0}}
.tag{{display:inline-block;font-size:10.5px;font-weight:700;text-transform:uppercase;
 letter-spacing:.05em;padding:2px 7px;border-radius:5px;background:var(--chip);
 margin-right:8px;vertical-align:2px}}
.tag.faculty{{color:var(--faculty)}} .tag.conf{{color:var(--conf)}}
.tag.journal{{color:var(--journal)}} .tag.company{{color:var(--company)}}
.tag.postdoc{{color:var(--postdoc)}} .tag.rinst{{color:var(--rinst)}}
.t{{font-weight:600;color:var(--accent);text-decoration:none}}
.t:hover{{text-decoration:underline}}
.dl{{display:inline-block;margin-left:8px;font-size:12px;color:var(--soft);
 background:var(--chip);border-radius:5px;padding:1px 7px;white-space:nowrap}}
.note{{margin:5px 0 0;color:var(--soft);font-size:13.5px}}
.empty{{color:var(--soft);padding:12px 0}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;
 padding:16px 18px 10px;margin-bottom:22px}}
.panel h2{{font-size:15px;margin:0 0 12px;display:flex;align-items:baseline;gap:10px}}
.psub{{font-weight:400;font-size:12.5px;color:var(--soft)}}
.shead{{font-size:12px;text-transform:uppercase;letter-spacing:.07em;color:var(--soft);
 margin:0 0 10px 2px}}
.dls{{list-style:none;margin:0;padding:0}}
.dlrow{{display:flex;gap:13px;padding:11px 0;border-bottom:1px solid var(--line)}}
.dlrow:last-child{{border-bottom:0}}
.left{{flex:0 0 46px;text-align:center;font-weight:700;font-size:13px;
 font-variant-numeric:tabular-nums;border-radius:6px;padding:3px 0;height:fit-content;
 background:var(--chip);color:var(--soft)}}
.dlrow.hot .left{{background:var(--hot);color:#fff}}
.dlrow.soon .left{{background:var(--soon);color:#fff}}
.mid{{min-width:0;flex:1}}
.conf{{display:inline-block;margin-left:8px;font-size:10px;font-weight:700;
 text-transform:uppercase;letter-spacing:.04em;padding:1px 6px;border-radius:4px;
 background:var(--chip);color:var(--soft);vertical-align:2px}}
.conf.ok{{color:var(--faculty)}}
.conf.warn{{color:var(--conf)}}
.note.sub{{font-size:12.5px;opacity:.85;margin-top:3px}}
.foot{{color:var(--soft);font-size:11.5px;margin:12px 0 4px;border-top:1px solid var(--line);
 padding-top:10px}}
code{{background:var(--chip);padding:1px 4px;border-radius:3px;font-size:11px}}
footer{{margin-top:28px;color:var(--soft);font-size:12.5px;text-align:center}}
.tabs{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 24px;border-bottom:1px solid var(--line);padding-bottom:8px}}
.tab{{font:inherit;font-weight:650;color:var(--soft);background:transparent;border:0;border-radius:8px;
 padding:9px 13px;cursor:pointer}}
.tab:hover{{background:var(--chip);color:var(--ink)}}
.tab[aria-selected="true"]{{background:var(--accent);color:#fff}}
.tab-panel[hidden]{{display:none}}
.tab-panel>.sub{{margin-bottom:20px}}
.ai-intro{{font-size:14px;color:var(--soft);margin:0 0 20px}}
.wiki-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
.wiki-topic{{border:1px solid var(--line);border-radius:9px;padding:12px}}
.wiki-topic h3{{font-size:13px;text-transform:none;letter-spacing:0;color:var(--ink);margin:0 0 6px}}
.wiki-topic .note{{margin:0}}
.wiki-links{{font-size:12px;margin:8px 0 0}}
.wiki-links a{{color:var(--accent);text-decoration:none}}
.wiki-links a:hover{{text-decoration:underline}}
.tag.releases{{color:var(--accent)}} .tag.performance{{color:var(--journal)}}
.tag.local{{color:var(--faculty)}} .tag.research{{color:var(--rinst)}}
.tag.community{{color:var(--conf)}}
.tag.deadline{{color:var(--hot)}}
.save-btn{{font:inherit;font-size:12px;font-weight:600;color:var(--accent);background:var(--chip);
 border:1px solid var(--line);border-radius:6px;padding:3px 9px;margin-left:9px;cursor:pointer;
 vertical-align:2px}}
.save-btn:hover{{border-color:var(--accent)}}
.save-btn[aria-pressed="true"]{{color:var(--faculty)}}
.save-btn:disabled{{opacity:.5;cursor:not-allowed}}
.remove-feed-btn{{font:inherit;font-size:12px;font-weight:600;color:var(--soft);background:transparent;
 border:1px solid transparent;border-radius:6px;padding:3px 7px;margin-left:4px;cursor:pointer}}
.remove-feed-btn:hover{{color:var(--hot);border-color:var(--line)}}
.remove-feed-btn:disabled{{opacity:.5;cursor:not-allowed}}
.item[hidden],.dlrow[hidden]{{display:none}}
.saved-group{{margin-bottom:24px}}
.saved-group h3{{font-size:13px;color:var(--ink)}}
.saved-list{{list-style:none;margin:0;padding:0;background:var(--card);
 border:1px solid var(--line);border-radius:12px;padding:2px 16px}}
.saved-meta{{font-size:12px;color:var(--soft);margin:5px 0 0}}
.save-error{{color:var(--hot)}}
.manage-hint{{font-size:12px;color:var(--soft);margin:0 0 12px}}
.removed-panel{{padding:0 16px;margin-bottom:18px}}
.removed-panel summary{{padding:10px 0;font-size:12px;color:var(--soft)}}
.removed-panel[hidden]{{display:none}}
.removed-panel .items{{border-top:1px solid var(--line)}}
@media(max-width:620px){{.wiki-grid{{grid-template-columns:1fr}}.tabs{{gap:4px}}.tab{{padding:8px 10px}}}}
</style></head><body><div class="wrap">
<header>
  <h1>Career Alerts</h1>
  <div class="sub">Career opportunities and AI Watch</div>
</header>
<nav class="tabs" role="tablist" aria-label="Dashboard sections">
  <button class="tab" id="career-tab" type="button" role="tab" aria-controls="career-panel" aria-selected="true" data-tab="career">Career Opportunities</button>
  <button class="tab" id="ai-tab" type="button" role="tab" aria-controls="ai-panel" aria-selected="false" data-tab="ai">AI Watch</button>
  <button class="tab" id="saved-tab" type="button" role="tab" aria-controls="saved-panel" aria-selected="false" data-tab="saved">Saved <span id="saved-tab-count"></span></button>
</nav>
<p class="save-error" id="storage-error" role="alert" hidden>Browser storage is unavailable for this local file, so Save and Remove are disabled.</p>
<section class="tab-panel" id="career-panel" role="tabpanel" aria-labelledby="career-tab">
<div class="sub">Latest career scan <strong>{esc(latest)}</strong> · {len(digests)} scan(s) · {grand} items tracked</div>
<p class="manage-hint">Remove hides an item in this browser. Expand Removed career items to restore it.</p>
<details class="panel removed-panel" id="career-removed" hidden><summary>Removed career items <span id="career-removed-count"></span></summary><ul class="items" id="career-removed-list"></ul></details>
{deadline_html}
<h2 class="shead">Scan History</h2>
{"".join(cards)}
</section>
<section class="tab-panel" id="ai-panel" role="tabpanel" aria-labelledby="ai-tab" hidden>
<p class="manage-hint">Remove hides an item in this browser. Expand Removed AI Watch items to restore it.</p>
<details class="panel removed-panel" id="ai-removed" hidden><summary>Removed AI Watch items <span id="ai-removed-count"></span></summary><ul class="items" id="ai-removed-list"></ul></details>
{ai_html}
</section>
<section class="tab-panel" id="saved-panel" role="tabpanel" aria-labelledby="saved-tab" hidden>
<div class="sub">Items saved from Career Opportunities and AI Watch</div>
<p class="ai-intro">Saved items stay in this browser when the daily page is rebuilt. Use the same browser and file location to see them later. Removing an item from a feed does not unsave it.</p>
<div id="saved-content" aria-live="polite"></div>
</section>
<footer>Rebuilt {esc(built)} · generated from career and AI Watch digests in 05 Career/automation/</footer>
<script>
{saved_js}
</script>
</div></body></html>
"""
    OUT_FILE.write_text(doc, encoding="utf-8")
    print(f"HTML dashboard -> {OUT_FILE} "
          f"({len(digests)} digest(s), {grand} items, {len(deadlines)} open deadline(s))")


if __name__ == "__main__":
    main()
