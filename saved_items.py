"""Build save/remove controls with stable item identities for the dashboard."""

import hashlib
import html
import json


def item_id(source, category, title, url, note):
    """Stable id shared by the feed buttons and the calendar."""
    display_title = title or note
    identity = "\x1f".join((source, url)) if url else "\x1f".join(
        (source, category, display_title, note)
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def item_controls(source, category, tag, title, url, note, seen_date,
                  key_info="", deadline="", past=False):
    display_title = title or note
    if not display_title:
        return ""
    item = {
        "id": item_id(source, category, title, url, note),
        "source": source,
        "category": category,
        "tag": tag,
        "title": display_title,
        "url": url or "",
        "note": note if title else "",
        "keyInfo": key_info or "",
        "deadline": deadline or "",
        "seenDate": seen_date,
    }
    payload = html.escape(json.dumps(item, ensure_ascii=False, separators=(",", ":")), quote=True)
    save_label = html.escape(f"Save {display_title}", quote=True)
    remove_label = html.escape(f"Remove {display_title} from this feed", quote=True)
    past_label = html.escape(f"Keep a summary of {display_title} in Past", quote=True)
    past_btn = (
        f'<button class="save-btn past-btn" type="button" data-past="{item["id"]}" '
        f'aria-pressed="false" aria-label="{past_label}">Past save</button>'
        if past else ""
    )
    return (
        f'<button class="save-btn" type="button" data-save="{payload}" '
        f'aria-pressed="false" aria-label="{save_label}">Save</button>'
        f'{past_btn}'
        f'<button class="remove-feed-btn" type="button" data-remove-feed="{item["id"]}" '
        f'aria-label="{remove_label}">Remove</button>'
    )
