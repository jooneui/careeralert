"""Render the Economy tab: FRED indicators plus dated news digests."""

from pathlib import Path

from ai_watch import esc, load_feed, render_feed_history
from econ_indicators import render as render_indicators

AUTO_DIR = Path(__file__).resolve().parent
ECON_DIGEST_DIR = AUTO_DIR / "econ-news-digests"

# (heading in the .md, css/state key, short label)
SECTIONS = [
    ("Central Banks & Rates", "central", "Rates"),
    ("Inflation & Jobs", "inflation", "Inflation"),
    ("Markets & Investment", "markets", "Markets"),
    ("Global Economy & Currencies", "global", "Global"),
    ("Outlook & Opinions", "views", "Outlook"),
]


def render():
    digests = load_feed(ECON_DIGEST_DIR, SECTIONS)
    latest = digests[0]["date"] if digests else "not scanned yet"
    total = sum(len(items) for digest in digests for items in digest["sections"].values())
    out = [f'<div class="sub">Latest economy scan <strong>{esc(latest)}</strong> · {len(digests)} scan(s) · {total} linked items</div>']
    out.append('<p class="ai-intro">Indicator numbers come straight from the St. Louis Fed (FRED). The articles below explain what moved them: central-bank decisions, inflation and jobs releases, market moves, the global economy, and named forecasters\' views. Information only, not investment advice.</p>')
    out.append(render_indicators())
    out.append(render_feed_history(digests, SECTIONS, "econ", "Economy Scan History"))
    return "".join(out)
