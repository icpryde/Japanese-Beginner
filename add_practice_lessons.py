#!/usr/bin/env python3
"""
add_practice_lessons.py — create link-card lessons for the auto-generated
weekly practice quizzes (weeks without an official course test), inserted
after each week's "Week N Review" lesson. Idempotent.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
LESSONS = CONTENT / "lessons"
MANIFEST = CONTENT / "manifest.json"
WEEKS = [4, 5, 6, 7, 9, 10, 11]

CARD = """<div class="fr-view">
<p>No official test this week — so here's an auto-generated practice quiz built
from this week's vocabulary: listening questions with native audio, picture
questions, and Japanese⇄English multiple choice. Different focus every attempt.</p>
<a href="../weeks/week{n}-practice.html" class="test-link-card">
  <span class="test-link-icon">📝</span>
  <div class="test-link-info">
    <h3>Take the Week {n} Practice Quiz</h3>
    <p>30 questions from Week {n} vocabulary · listening, pictures, multiple choice</p>
  </div>
  <span class="test-link-arrow">→</span>
</a>
</div>"""


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lessons = manifest["lessons"]
    existing = {str(l["id"]) for l in lessons}
    added = 0
    for n in WEEKS:
        lid = f"practice_week{n}"
        if lid in existing:
            print(f"{lid}: already present")
            continue
        anchor = next((l for l in lessons
                       if re.fullmatch(rf"Week {n} Review", str(l.get("title", "")).strip(), re.I)), None)
        if anchor is None:
            print(f"{lid}: no 'Week {n} Review' anchor found — skipped")
            continue
        item = {"id": lid, "title": f"Week {n} Practice Quiz", "type": "reference",
                "section": anchor.get("section"), "section_type": anchor.get("section_type", "day"),
                "week": n, "day": int(anchor.get("day", n * 5) or n * 5)}
        lessons.insert(lessons.index(anchor) + 1, item)
        (LESSONS / f"{lid}.json").write_text(json.dumps({
            "id": lid, "title": item["title"], "primary_type": "reference",
            "section": item["section"], "section_type": "day",
            "week": n, "day": item["day"],
            "html": CARD.format(n=n),
            "videos": [], "downloads": [], "images": [],
            "has_video": False, "has_images": False, "has_downloads": False,
            "placeholder": False,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        for s in manifest["sections"]:
            if s.get("label") == item["section"]:
                s["lesson_count"] = s.get("lesson_count", 0) + 1
        added += 1
        print(f"{lid}: inserted after 'Week {n} Review'")
    manifest["total_lessons"] = len(lessons)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"done: +{added}, total {manifest['total_lessons']}")


if __name__ == "__main__":
    main()
