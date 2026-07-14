#!/usr/bin/env python3
"""
add_quiz_lessons.py — create lesson pages + manifest entries for the two
Quiz-type reviews that the original import skipped (Quiz lessons were out of
import_local.py's scope). Each page is a link card to its weekly test page.

Idempotent: skips anything already present in the manifest.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
LESSONS = CONTENT / "lessons"
MANIFEST = CONTENT / "manifest.json"

ENTRIES = [
    {
        "id": "quiz_week8", "title": "Week 8 Review Quiz",
        "week": 8, "day": 40, "anchor_id": "13962987",  # after "Week 8 Review"
        "test_href": "../weeks/week8-test.html",
        "card_title": "Take the Week 8 Test",
        "card_sub": "30 questions — cumulative review of Weeks 4–8 · listening, reading, and grammar",
    },
    {
        "id": "quiz_week9_12", "title": "Week 9-12 Quiz Review",
        "week": 12, "day": 60, "anchor_id": "14711514",  # after "Week 12 Review"
        "test_href": "../weeks/week9-12-test.html",
        "card_title": "Take the Week 9–12 Test",
        "card_sub": "30 questions — cumulative review of Weeks 9–12 · listening, reading, and multi-select",
    },
]

CARD = """<div class="fr-view">
<p>This cumulative review test covers everything from the previous weeks —
listening comprehension, reading, grammar, and vocabulary. Audio questions use
the original course recordings. You can retake it as many times as you like.</p>
<a href="{href}" class="test-link-card">
  <span class="test-link-icon">📝</span>
  <div class="test-link-info">
    <h3>{title}</h3>
    <p>{sub}</p>
  </div>
  <span class="test-link-arrow">→</span>
</a>
</div>"""


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lessons = manifest["lessons"]
    existing = {str(l["id"]) for l in lessons}
    added = 0

    for e in ENTRIES:
        if e["id"] in existing:
            print(f"{e['id']}: already in manifest, skipping")
            continue
        anchor = next((l for l in lessons if str(l["id"]) == e["anchor_id"]), None)
        if anchor is None:
            raise SystemExit(f"anchor {e['anchor_id']} not found for {e['id']}")
        section = anchor.get("section")
        item = {"id": e["id"], "title": e["title"], "type": "reference",
                "section": section, "section_type": anchor.get("section_type", "day"),
                "week": e["week"], "day": e["day"]}
        lessons.insert(lessons.index(anchor) + 1, item)

        lesson_json = {
            "id": e["id"], "title": e["title"], "primary_type": "reference",
            "section": section, "section_type": "day",
            "week": e["week"], "day": e["day"],
            "html": CARD.format(href=e["test_href"], title=e["card_title"], sub=e["card_sub"]),
            "videos": [], "downloads": [], "images": [],
            "has_video": False, "has_images": False, "has_downloads": False,
            "placeholder": False,
        }
        (LESSONS / f"{e['id']}.json").write_text(
            json.dumps(lesson_json, ensure_ascii=False, indent=2), encoding="utf-8")

        for s in manifest["sections"]:
            if s.get("label") == section:
                s["lesson_count"] = s.get("lesson_count", 0) + 1
        added += 1
        print(f"{e['id']}: inserted after {e['anchor_id']} in '{section}'")

    manifest["total_lessons"] = len(lessons)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: +{added} lessons, total {manifest['total_lessons']}")


if __name__ == "__main__":
    main()
