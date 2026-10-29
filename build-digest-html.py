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
from transport_news import render as render_transport_news
from econ_news import render as render_econ
from saved_items import item_controls, item_id

AUTO_DIR = Path(__file__).resolve().parent
DIGEST_DIR = AUTO_DIR / "digests"
DEADLINE_FILE = AUTO_DIR / "open-deadlines.json"
OUT_FILE = AUTO_DIR.parent / "career-digest.html"
SAVED_SCRIPT = AUTO_DIR / "saved-items.js"
CALENDAR_SCRIPT = AUTO_DIR / "calendar.js"

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
KEYINFO_RE = re.compile(r"^\s+[-*]\s*Key info:\s*(?P<info>.+)$", re.IGNORECASE)


def parse_digest(path):
    """-> {'date': str, 'sections': {cls: [item, ...]}, 'notes': [str, ...]}

    Linked bullets are items. An indented "- Key info: ..." bullet attaches to
    the item above it. Unlinked bullets are the scanner's own status notes.
    """
    sections = {cls: [] for _, cls in CATEGORIES}
    notes = []
    last = None
    heading_to_cls = {h: c for h, c in CATEGORIES}
    current = None

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        km = KEYINFO_RE.match(line)
        if km and last is not None and current is not None:
            last["key_info"] = km.group("info").strip()
            continue
        if line.startswith("## "):
            last = None
            current = heading_to_cls.get(line[3:].strip())
            continue
        if not line.startswith("-") or current is None:
            continue
        if EMPTY_RE.search(line):
            continue

        m = LINK_RE.match(line)
        if not m:
            m = PLAIN_RE.match(line)
            if m:
                notes.append(m.group("note").strip())
            last = None
            continue
        note = m.group("note").strip()
        title, url = m.group("title").strip(), m.group("url").strip()

        deadline = None
        dm = DEADLINE_RE.search(note)
        if dm:
            deadline = dm.group("dl").rstrip(".")
            note = note[: dm.start()].strip().rstrip(".").rstrip(",")

        last = {"title": title, "url": url, "note": note, "deadline": deadline, "key_info": ""}
        sections[current].append(last)

    return {"date": path.stem, "sections": sections, "notes": notes}


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
    bits.append(item_controls("career", LABELS[cls], cls, it["title"], it["url"], it["note"], scan_date,
                              key_info=it["key_info"], deadline=it["deadline"], past=True))
    if it["note"]:
        bits.append(f'<p class="note">{esc(it["note"])}</p>')
    if it["key_info"]:
        bits.append(f'<p class="keyinfo">{esc(it["key_info"])}</p>')
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
            key_info=f'{r.get("org", "")} | {r.get("event", "")}'.strip(" |"),
            deadline=r["_label"], past=True,
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


MONTHS = {m.lower(): i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
ISO_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
TEXT_DATE_RE = re.compile(r"\b([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})\b")
TENTATIVE_RE = re.compile(r"~|expected|tentative|unconfirmed|unverified|approx", re.IGNORECASE)


def parse_deadline_date(text):
    """First calendar date in a deadline string, or None ("rolling", "not listed")."""
    if not text:
        return None
    m = ISO_DATE_RE.search(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = TEXT_DATE_RE.search(text)
    if m and m.group(1)[:3].lower() in MONTHS:
        try:
            return date(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
        except ValueError:
            return None
    return None


def calendar_events(digests):
    """Every dated deadline from open-deadlines.json and the scan digests."""
    events, seen = [], set()

    rows = []
    if DEADLINE_FILE.is_file():
        try:
            rows = json.loads(DEADLINE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            rows = []
    for r in rows:
        d = parse_deadline_date(r.get("deadline") or "")
        if not d:
            continue
        key = (r.get("url") or r.get("title"), d)
        if key in seen:
            continue
        seen.add(key)
        save_note = f'{r.get("event", "")} · due {d.strftime("%b %d, %Y")}. {r.get("note", "")}'
        events.append({
            "id": item_id("career", "Deadline", r.get("title", ""), r.get("url", ""), save_note),
            "date": d.isoformat(), "title": r.get("title", ""), "url": r.get("url", ""),
            "tag": r.get("category", "conf"), "label": "Deadline",
            "detail": r.get("event", ""),
            "tentative": r.get("confidence") not in (None, "confirmed"),
        })

    for dg in digests:
        for _, cls in CATEGORIES:
            for it in dg["sections"][cls]:
                d = parse_deadline_date(it["deadline"])
                if not d:
                    continue
                key = (it["url"] or it["title"], d)
                if key in seen:
                    continue
                seen.add(key)
                events.append({
                    "id": item_id("career", LABELS[cls], it["title"], it["url"], it["note"]),
                    "date": d.isoformat(), "title": it["title"] or it["note"], "url": it["url"] or "",
                    "tag": cls, "label": LABELS[cls],
                    "detail": f'From scan {dg["date"]}',
                    "tentative": bool(TENTATIVE_RE.search(it["deadline"] + " " + it["note"])),
                })
    events.sort(key=lambda e: e["date"])
    return events


def main():
    deadlines = load_deadlines()
    deadline_html = render_deadlines(deadlines)
    ai_html = render_ai_watch()
    news_html = render_transport_news()
    econ_html = render_econ()

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
        if d["notes"]:
            note_items = "".join(f"<li>{esc(n)}</li>" for n in d["notes"])
            body.append(
                f'<details class="scan-notes"><summary>Scan notes ({len(d["notes"])}) '
                f'— what was checked, closed, or skipped</summary><ul>{note_items}</ul></details>'
            )

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
    calendar_js = CALENDAR_SCRIPT.read_text(encoding="utf-8")
    events = calendar_events(digests)
    # "</" is escaped so a title can never close the <script> tag early
    events_json = json.dumps(events, ensure_ascii=False).replace("</", "<\\/")

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
.tag.community{{color:var(--conf)}} .tag.leaders{{color:var(--hot)}}
.tag.av{{color:var(--company)}} .tag.maps{{color:var(--faculty)}} .tag.tdata{{color:var(--journal)}}
.tag.rideshare{{color:var(--rinst)}} .tag.policy{{color:var(--conf)}} .tag.evidence{{color:var(--hot)}}
.keyinfo{{margin:6px 0 0;font-size:12.5px;color:var(--ink);background:var(--chip);
 border-radius:6px;padding:5px 9px}}
.past-btn[aria-pressed="true"]{{color:var(--faculty)}}
.scan-notes{{margin:18px 0 0;border-top:1px solid var(--line);padding-top:10px;font-size:12.5px;color:var(--soft)}}
.scan-notes summary{{padding:4px 0;font-weight:600;font-size:12.5px}}
.scan-notes ul{{margin:6px 0 0;padding-left:18px}}
.scan-notes li{{margin:0 0 6px}}
.cal-head{{display:flex;align-items:center;gap:8px;margin:0 0 12px;flex-wrap:wrap}}
.cal-head h2{{font-size:18px;margin:0 6px;min-width:150px}}
.cal-head .save-btn{{margin-left:0}}
#cal-ics{{margin-left:auto}}
.cal-grid{{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));border:1px solid var(--line);
 border-radius:12px;overflow:hidden;background:var(--card)}}
.cal-dow{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--soft);
 padding:7px 6px;border-bottom:1px solid var(--line);background:var(--chip)}}
.cal-day{{min-height:92px;padding:5px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);
 min-width:0;font:inherit;text-align:left;background:transparent;color:inherit;display:flex;flex-direction:column;gap:3px}}
.cal-day:nth-child(7n){{border-right:0}}
.cal-day.out{{opacity:.4}}
.cal-num{{font-size:12px;font-weight:600;color:var(--soft);font-variant-numeric:tabular-nums}}
.cal-day.today .cal-num{{background:var(--accent);color:#fff;border-radius:999px;padding:0 6px;align-self:flex-start}}
.cal-ev{{display:block;font-size:11px;line-height:1.3;padding:2px 5px;border-radius:4px;background:var(--chip);
 border-left:3px solid currentColor;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;text-decoration:none}}
.cal-ev.tentative{{border-left-style:dashed}}
.cal-ev.past{{opacity:.55}}
.cal-more{{font-size:11px;color:var(--soft)}}
.cal-ev.faculty,.cal-list .faculty{{color:var(--faculty)}} .cal-ev.postdoc,.cal-list .postdoc{{color:var(--postdoc)}}
.cal-ev.rinst,.cal-list .rinst{{color:var(--rinst)}} .cal-ev.conf,.cal-list .conf{{color:var(--conf)}}
.cal-ev.journal,.cal-list .journal{{color:var(--journal)}} .cal-ev.company,.cal-list .company{{color:var(--company)}}
.cal-list{{margin-top:18px}}
.dlrow.past .left{{opacity:.5}}
@media(max-width:620px){{
 .cal-day{{min-height:54px;padding:3px}}
 .cal-ev{{font-size:0;padding:0;height:6px;border-left:0;background:currentColor}}
 .cal-head h2{{min-width:0;font-size:16px}}
}}
.tag.central{{color:var(--accent)}} .tag.inflation{{color:var(--hot)}} .tag.markets{{color:var(--faculty)}}
.tag.global{{color:var(--company)}} .tag.views{{color:var(--journal)}}
.ind-group{{margin:14px 0 8px}}
.ind-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px}}
.ind{{display:flex;flex-direction:column;gap:2px;border:1px solid var(--line);border-radius:9px;padding:10px 12px;
 text-decoration:none;color:var(--ink);min-width:0}}
.ind:hover{{border-color:var(--accent)}}
.ind-l{{font-size:12px;color:var(--soft)}}
.ind-v{{font-size:21px;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.01em}}
.ind-ds{{display:flex;gap:8px;flex-wrap:wrap;font-size:11.5px;font-variant-numeric:tabular-nums}}
.ind-d{{color:var(--soft)}}
.ind-date{{font-size:11px;color:var(--soft)}}
.facts{{display:grid;grid-template-columns:max-content 1fr;gap:3px 12px;margin:8px 0 0;font-size:13px}}
.facts dt{{color:var(--soft);font-weight:600}}
.facts dd{{margin:0}}
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
  <button class="tab" id="calendar-tab" type="button" role="tab" aria-controls="calendar-panel" aria-selected="false" data-tab="calendar">Calendar</button>
  <button class="tab" id="news-tab" type="button" role="tab" aria-controls="news-panel" aria-selected="false" data-tab="news">Transportation News</button>
  <button class="tab" id="econ-tab" type="button" role="tab" aria-controls="econ-panel" aria-selected="false" data-tab="econ">Economy</button>
  <button class="tab" id="saved-tab" type="button" role="tab" aria-controls="saved-panel" aria-selected="false" data-tab="saved">Saved <span id="saved-tab-count"></span></button>
  <button class="tab" id="past-tab" type="button" role="tab" aria-controls="past-panel" aria-selected="false" data-tab="past">Past <span id="past-tab-count"></span></button>
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
<section class="tab-panel" id="calendar-panel" role="tabpanel" aria-labelledby="calendar-tab" hidden>
<div class="sub">Submission and application deadlines · {len(events)} dated</div>
<p class="manage-hint">Only deadlines with a real date appear here ("rolling" or "not listed" ones don't). Items you Remove from a feed also leave the calendar. Dashed = date not confirmed.</p>
<div class="cal-head">
  <button class="save-btn" type="button" id="cal-prev" aria-label="Previous month">‹</button>
  <h2 id="cal-title" aria-live="polite"></h2>
  <button class="save-btn" type="button" id="cal-next" aria-label="Next month">›</button>
  <button class="save-btn" type="button" id="cal-today">Today</button>
  <button class="save-btn" type="button" id="cal-ics">Download .ics</button>
</div>
<div class="cal-grid" id="cal-grid" role="grid"></div>
<section class="panel cal-list"><h2 id="cal-list-title">Deadlines this month</h2><ul class="dls" id="cal-list"></ul></section>
<script type="application/json" id="calendar-data">{events_json}</script>
</section>
<section class="tab-panel" id="news-panel" role="tabpanel" aria-labelledby="news-tab" hidden>
<p class="manage-hint">Remove hides an item in this browser. Expand Removed news items to restore it.</p>
<details class="panel removed-panel" id="news-removed" hidden><summary>Removed news items <span id="news-removed-count"></span></summary><ul class="items" id="news-removed-list"></ul></details>
{news_html}
</section>
<section class="tab-panel" id="econ-panel" role="tabpanel" aria-labelledby="econ-tab" hidden>
<p class="manage-hint">Remove hides an article in this browser. Expand Removed economy items to restore it.</p>
<details class="panel removed-panel" id="econ-removed" hidden><summary>Removed economy items <span id="econ-removed-count"></span></summary><ul class="items" id="econ-removed-list"></ul></details>
{econ_html}
</section>
<section class="tab-panel" id="saved-panel" role="tabpanel" aria-labelledby="saved-tab" hidden>
<div class="sub">Items saved from Career Opportunities, AI Watch, Transportation News, and Economy</div>
<p class="ai-intro">Saved items stay in this browser when the daily page is rebuilt. Use the same browser and file location to see them later. Removing an item from a feed does not unsave it.</p>
<div id="saved-content" aria-live="polite"></div>
</section>
<section class="tab-panel" id="past-panel" role="tabpanel" aria-labelledby="past-tab" hidden>
<div class="sub">Opportunities you kept with Past save</div>
<p class="ai-intro">A summary of each posting or call is stored here when you click Past save, so the topic, salary, location, rank and deadline stay readable after the original link is taken down. Stored in this browser, like Saved.</p>
<div id="past-content" aria-live="polite"></div>
</section>
<footer>Rebuilt {esc(built)} · generated from career, AI Watch, Transportation News, and Economy digests in 05 Career/automation/</footer>
<script>
{saved_js}
</script>
<script>
{calendar_js}
</script>
</div></body></html>
"""
    OUT_FILE.write_text(doc, encoding="utf-8")
    print(f"HTML dashboard -> {OUT_FILE} "
          f"({len(digests)} digest(s), {grand} items, {len(deadlines)} open deadline(s))")


if __name__ == "__main__":
    main()
