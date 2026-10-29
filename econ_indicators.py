"""Economic indicators from FRED (St. Louis Fed), no API key needed.

  python3 econ_indicators.py fetch   -> downloads series, writes econ-indicators.json
  render()                          -> HTML panel for the dashboard (no network)

Numbers come straight from FRED, not from an AI scan. If a download fails,
the last good value for that series is kept and marked stale.
"""

import csv
import io
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from ai_watch import esc

AUTO_DIR = Path(__file__).resolve().parent
DATA_FILE = AUTO_DIR / "econ-indicators.json"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start}"
FRED_PAGE = "https://fred.stlouisfed.org/series/{sid}"

# (group, series id, label, unit, transform, decimals)
#   transform "level": value as published; "yoy": % change from 12 months earlier
SERIES = [
    ("Interest rates", "DFEDTARU", "Fed funds target (upper)", "%", "level", 2),
    ("Interest rates", "DGS2", "2-year Treasury yield", "%", "level", 2),
    ("Interest rates", "DGS10", "10-year Treasury yield", "%", "level", 2),
    ("Interest rates", "MORTGAGE30US", "30-year mortgage rate", "%", "level", 2),
    ("Inflation & jobs", "CPIAUCSL", "CPI inflation (all items, YoY)", "%", "yoy", 1),
    ("Inflation & jobs", "CPILFESL", "Core CPI (ex food & energy, YoY)", "%", "yoy", 1),
    ("Inflation & jobs", "UNRATE", "Unemployment rate", "%", "level", 1),
    ("Currencies", "DTWEXBGS", "Broad US dollar index", "", "level", 2),
    ("Currencies", "DEXKOUS", "USD → KRW (won per dollar)", "₩", "level", 2),
    ("Currencies", "DEXJPUS", "USD → JPY (yen per dollar)", "¥", "level", 2),
    ("Currencies", "DEXUSEU", "EUR → USD (dollars per euro)", "$", "level", 4),
    ("Currencies", "DEXCHUS", "USD → CNY (yuan per dollar)", "¥", "level", 4),
]
GROUP_NOTES = {
    "Interest rates": "Treasury yields are daily; the mortgage rate is weekly (Freddie Mac).",
    "Inflation & jobs": "Monthly, seasonally adjusted (BLS). Released about two weeks after the month ends.",
    "Currencies": "Daily noon buying rates in New York (Federal Reserve H.10), about a week behind.",
}


def _download(sid, start):
    url = FRED_CSV.format(sid=sid, start=start.isoformat())
    # FRED stalls requests from unfamiliar user agents; system curl is accepted.
    text = subprocess.run(
        ["/usr/bin/curl", "-sS", "--fail", "-m", "30", url],
        capture_output=True, text=True, check=True,
    ).stdout
    rows = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) != 2 or row[0].lower().startswith("observation") or row[0] == "DATE":
            continue
        try:
            rows.append((date.fromisoformat(row[0]), float(row[1])))
        except ValueError:
            continue  # "." marks a missing day (holiday)
    if not rows:
        raise ValueError("no observations")
    return rows


def _yoy(rows):
    by_month = {(d.year, d.month): v for d, v in rows}
    out = []
    for d, v in rows:
        prev = by_month.get((d.year - 1, d.month))
        if prev:
            out.append((d, (v / prev - 1) * 100))
    return out


def _at_or_before(rows, target):
    best = None
    for d, v in rows:
        if d <= target:
            best = (d, v)
    return best


def fetch():
    old = {}
    if DATA_FILE.is_file():
        try:
            old = {s["id"]: s for s in json.loads(DATA_FILE.read_text(encoding="utf-8")).get("series", [])}
        except (OSError, json.JSONDecodeError):
            old = {}

    start = date.today() - timedelta(days=800)
    out, failures = [], []
    for group, sid, label, unit, transform, decimals in SERIES:
        try:
            rows = _download(sid, start)
            if transform == "yoy":
                rows = _yoy(rows)
            last_d, last_v = rows[-1]
            m = _at_or_before(rows, last_d - timedelta(days=28))
            y = _at_or_before(rows, last_d - timedelta(days=365))
            out.append({
                "id": sid, "group": group, "label": label, "unit": unit, "decimals": decimals,
                "date": last_d.isoformat(), "value": last_v,
                "m_ago": m[1] if m else None, "y_ago": y[1] if y else None,
                "stale": False,
            })
        except Exception as exc:  # network, HTTP, or parse error: keep last good value
            failures.append(f"{sid}: {exc}")
            if sid in old:
                out.append({**old[sid], "stale": True})
    DATA_FILE.write_text(json.dumps({
        "fetched": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "series": out,
        "failures": failures,
    }, indent=2), encoding="utf-8")
    print(f"econ indicators: {len(out) - len(failures)} fresh, {len(failures)} failed")
    for f in failures:
        print("  FAILED", f)
    return 0 if len(failures) < len(SERIES) else 1


def _fmt(v, decimals, unit):
    s = f"{v:,.{decimals}f}"
    if unit == "%":
        return s + "%"
    if unit in ("₩", "¥", "$"):
        return unit + s
    return s


def _delta(now, then, decimals, unit, label):
    if then is None:
        return ""
    diff = now - then
    if unit == "%":
        txt = f"{diff:+.2f} pt"
    else:
        txt = f"{(diff / then * 100):+.1f}%" if then else f"{diff:+.{decimals}f}"
    cls = "up" if diff > 0 else "down" if diff < 0 else ""
    return f'<span class="ind-d {cls}">{esc(label)} {esc(txt)}</span>'


def render():
    if not DATA_FILE.is_file():
        return '<p class="empty">Indicators have not been downloaded yet. They update with the daily scan.</p>'
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return '<p class="empty">Indicator file could not be read.</p>'

    parts = [f'<section class="panel"><h2>Key Indicators <span class="psub">from FRED · downloaded {esc(data.get("fetched", "?"))}</span></h2>']
    groups = []
    for s in data.get("series", []):
        if s["group"] not in groups:
            groups.append(s["group"])
    for g in groups:
        parts.append(f'<h3 class="ind-group">{esc(g)}</h3><div class="ind-grid">')
        for s in (x for x in data["series"] if x["group"] == g):
            d, u = s["decimals"], s["unit"]
            stale = ' <span class="conf warn">not updated</span>' if s.get("stale") else ""
            parts.append(
                f'<a class="ind" href="{esc(FRED_PAGE.format(sid=s["id"]))}" target="_blank" rel="noopener">'
                f'<span class="ind-l">{esc(s["label"])}</span>'
                f'<span class="ind-v">{esc(_fmt(s["value"], d, u))}</span>'
                f'<span class="ind-ds">{_delta(s["value"], s.get("m_ago"), d, u, "1M")}'
                f'{_delta(s["value"], s.get("y_ago"), d, u, "1Y")}</span>'
                f'<span class="ind-date">as of {esc(s["date"])}{stale}</span></a>'
            )
        parts.append(f'</div><p class="note sub">{esc(GROUP_NOTES.get(g, ""))}</p>')
    parts.append('<p class="foot">Changes compare with the latest value about one month and one year earlier. '
                 'For CPI they are changes in the inflation rate, in percentage points. Click a tile for its FRED chart. '
                 'Information only, not investment advice.</p></section>')
    return "".join(parts)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fetch":
        sys.exit(fetch())
    print(__doc__)
