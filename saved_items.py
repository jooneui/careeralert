"""Build save/remove controls with stable item identities for the dashboard."""

import hashlib
import html
import json


def item_controls(source, category, tag, title, url, note, seen_date):
    display_title = title or note
    if not display_title:
        return ""
    identity = "\x1f".join((source, url)) if url else "\x1f".join(
        (source, category, display_title, note)
    )
    item = {
        "id": hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24],
        "source": source,
        "category": category,
        "tag": tag,
        "title": display_title,
        "url": url or "",
        "note": note if title else "",
        "seenDate": seen_date,
    }
    payload = html.escape(json.dumps(item, ensure_ascii=False, separators=(",", ":")), quote=True)
    save_label = html.escape(f"Save {display_title}", quote=True)
    remove_label = html.escape(f"Remove {display_title} from this feed", quote=True)
    return (
        f'<button class="save-btn" type="button" data-save="{payload}" '
        f'aria-pressed="false" aria-label="{save_label}">Save</button>'
        f'<button class="remove-feed-btn" type="button" data-remove-feed="{item["id"]}" '
        f'aria-label="{remove_label}">Remove</button>'
    )
