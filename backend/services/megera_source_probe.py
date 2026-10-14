"""Read-only privacy-safe geometry probe for Eberron Megera Crepuscolare.

Emits counters and booleans only, never third-party source text or OCR images.
This is NOT a verification or authorization to modify review status.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def compact_word(value: Any) -> str:
    folded = unicodedata.normalize("NFKD", str(value or "")).casefold()
    folded = "".join(x for x in folded if not unicodedata.combining(x))
    return re.sub(r"[^a-z0-9]", "", folded)


def page_safe_geometry(page: Any, page_number: int) -> dict[str, Any]:
    words = page.get_text("words", sort=True)
    lines: dict[tuple[int, int], list[Any]] = {}
    for word in words:
        if len(word) < 7:
            continue
        lines.setdefault((int(word[5]), int(word[6])), []).append(word)
    targets = []
    all_words = [compact_word(w[4]) for w in words]
    for line in lines.values():
        tokens = [compact_word(w[4]) for w in line]
        phrase = "".join(tokens)
        title = "megeracrepuscolare" in phrase
        ca_label = "classearmatura" in phrase
        hp_label = "puntiferita" in phrase
        speed_label = "velocita" in phrase
        if title or ca_label or hp_label or speed_label:
            targets.append({
                "x": round(min(float(w[0]) for w in line) / page.rect.width, 3),
                "y": round(min(float(w[1]) for w in line) / page.rect.height, 3),
                "title": title,
                "ca_label": ca_label,
                "hp_label": hp_label,
                "speed_label": speed_label,
                "has_17": "17" in tokens,
                "has_82": "82" in tokens,
                "has_15d8": "15d8" in tokens,
                "has_9": "9" in tokens,
            })
    return {
        "page": page_number,
        "words": len(words),
        "megera_mentions": all_words.count("megera"),
        "crepuscolare_mentions": all_words.count("crepuscolare"),
        "title_lines": sum(x["title"] for x in targets),
        "ca_labels": sum(x["ca_label"] for x in targets),
        "hp_labels": sum(x["hp_label"] for x in targets),
        "speed_labels": sum(x["speed_label"] for x in targets),
        "lines": targets[:15],
    }
