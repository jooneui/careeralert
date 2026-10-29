"""Render the Transportation News panel from dated Markdown digests."""

from pathlib import Path

from ai_watch import esc, load_feed, render_feed_history

AUTO_DIR = Path(__file__).resolve().parent
NEWS_DIGEST_DIR = AUTO_DIR / "transport-news-digests"

# (heading in the .md, css/state key, short label)
SECTIONS = [
    ("Autonomous Vehicles", "av", "AV"),
    ("Maps & Navigation", "maps", "Maps"),
    ("Traffic Data & Open Data", "tdata", "Traffic Data"),
    ("Ride-hailing & Shared Mobility", "rideshare", "Ride-hailing"),
    ("Policy & Safety", "policy", "Policy"),
    ("Research Evidence", "evidence", "Research"),
]


def render():
    digests = load_feed(NEWS_DIGEST_DIR, SECTIONS)
    latest = digests[0]["date"] if digests else "not scanned yet"
    total = sum(len(items) for digest in digests for items in digest["sections"].values())
    out = [f'<div class="sub">Latest news scan <strong>{esc(latest)}</strong> · {len(digests)} scan(s) · {total} linked items</div>']
    out.append('<p class="ai-intro">Where the technology stands: autonomous-vehicle deployments, map and navigation products, traffic-data and open-map projects, ride-hailing companies, the regulation around them, and new research that measures their real-world effects. Company blogs and engineering posts first; news coverage when the company has not posted.</p>')
    out.append(render_feed_history(digests, SECTIONS, "news", "News Scan History"))
    return "".join(out)
