"""Choose only usable JianYing music and text-style candidates.

This module deliberately does not scrape JianYing's recommendation feed.  That
feed is account-, region-, membership- and version-dependent, so an agent must
first collect candidates from the currently visible JianYing UI.  The helpers
here validate that hand-off and provide a deterministic local-library fallback.
"""

import csv
import json
import os
from datetime import datetime, timezone
from typing import Any, Iterable


SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_CSV = os.path.join(SKILL_ROOT, "data", "cloud_music_library.csv")
TEXT_STYLES_CSV = os.path.join(SKILL_ROOT, "data", "cloud_text_styles.csv")
ARTIST_EFFECT_ROOT = os.path.join(SKILL_ROOT, "assets", "artistEffect")


def _read_csv(path: str) -> list[dict[str, str]]:
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as source:
        rows = [line for line in source if not line.startswith("#")]
    return list(csv.DictReader(rows)) if rows else []


def load_local_music_candidates() -> list[dict[str, Any]]:
    """Return previously indexed music; these are not claimed to be live recommendations."""
    result = []
    for row in _read_csv(MUSIC_CSV):
        music_id = (row.get("music_id") or "").strip()
        if not music_id:
            continue
        try:
            duration_s = float(row.get("duration_s") or 0)
        except ValueError:
            duration_s = 0.0
        result.append(
            {
                "id": music_id,
                "title": row.get("title") or "",
                "categories": row.get("categories") or "",
                "duration_s": duration_s,
                "source": "local_index",
            }
        )
    return result


def load_local_text_style_candidates() -> list[dict[str, str]]:
    """Return styles whose local JianYing effect resources are present."""
    result = []
    for row in _read_csv(TEXT_STYLES_CSV):
        style_id = (row.get("style_id") or row.get("id") or "").strip()
        if style_id and os.path.isdir(os.path.join(ARTIST_EFFECT_ROOT, style_id)):
            result.append(
                {
                    "id": style_id,
                    "title": row.get("name_hint") or row.get("name") or style_id,
                    "categories": row.get("categories") or "",
                    "source": "local_style_cache",
                }
            )
    return result


def validate_ui_candidates(
    candidates: Iterable[dict[str, Any]], kind: str, *, allow_membership: bool = True
) -> list[dict[str, Any]]:
    """Keep only candidates observed in the current JianYing UI.

    A caller should record the visible title and an ID if the UI/draft exposes
    one. This skill assumes a JianYing membership by default, so paid items
    remain eligible unless ``allow_membership`` is explicitly disabled. Items
    the current UI marks unavailable are always rejected.
    """
    accepted = []
    for raw in candidates:
        item = dict(raw)
        if item.get("source") != "jianying_ui" or not str(item.get("title") or "").strip():
            continue
        if item.get("kind") not in {kind, None, ""}:
            continue
        if item.get("available") is False:
            continue
        if item.get("membership_required") is True and not allow_membership:
            continue
        accepted.append(item)
    return accepted


def rank_candidates(
    candidates: Iterable[dict[str, Any]],
    *,
    intent: str = "",
    video_duration_s: float | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Rank candidate metadata without inventing availability or popularity."""
    keywords = {token.lower() for token in str(intent).replace("/", " ").split() if token}
    ranked = []
    for position, raw in enumerate(candidates):
        item = dict(raw)
        searchable = f"{item.get('title', '')} {item.get('categories', '')}".lower()
        hits = sum(keyword in searchable for keyword in keywords)
        duration_s = item.get("duration_s")
        duration_bonus = 0
        if video_duration_s and isinstance(duration_s, (int, float)) and duration_s >= video_duration_s:
            duration_bonus = 1
        item["score"] = hits * 10 + duration_bonus
        item["selection_reason"] = "metadata keyword match" if hits else "eligible candidate"
        ranked.append((item, position))
    ranked.sort(key=lambda pair: (-pair[0]["score"], pair[1]))
    return [item for item, _ in ranked[: max(0, limit)]]


def make_selection_record(
    *,
    video_summary: str,
    music: dict[str, Any] | None,
    text_style: dict[str, Any] | None,
) -> dict[str, Any]:
    """Create a reviewable record; callers decide where and whether to save it."""
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "video_summary": video_summary,
        "music": music,
        "text_style": text_style,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Rank verified JianYing native-asset candidates")
    parser.add_argument("--intent", default="")
    parser.add_argument("--duration-s", type=float)
    parser.add_argument("--kind", choices=("music", "text-style"), required=True)
    parser.add_argument("--limit", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    candidates = (
        load_local_music_candidates()
        if args.kind == "music"
        else load_local_text_style_candidates()
    )
    result = rank_candidates(
        candidates, intent=args.intent, video_duration_s=args.duration_s, limit=args.limit
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        for item in result:
            print(f"{item['id']}\t{item['title']}\t{item['selection_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
