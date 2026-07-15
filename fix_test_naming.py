#!/usr/bin/env python3
"""
fix_test_naming.py — one-shot cleanup of test/quiz lesson naming so the nav is
unambiguous for every test:
    <Week N Test>                (interactive test link-card lesson)
    <Week N Test — Answer Key>   (styled key page)
Also creates the Week 3 interactive-test lesson (quiz_week3).
Idempotent.
"""
import json, re
from pathlib import Path

ROOT = Path(__file__).parent
CONTENT = ROOT / "content"
LESSONS = CONTENT / "lessons"
MANIFEST = CONTENT / "manifest.json"

RENAMES = {
    "quiz_week8": "Week 8 Test",
    "quiz_week9_12": "Week 9–12 Test",
    "Week 3 - Review quiz Answers": "Week 3 Test — Answer Key",
    "Week 8 Review Quiz Answers": "Week 8 Test — Answer Key",
    "Week 9-12 Quiz Review Answers": "Week 9–12 Test — Answer Key",
}

CARD = """<div class="fr-view">
<p>This review test covers the previous weeks — listening comprehension,
video questions, grammar, and vocabulary. You can retake it as many times as
you like.</p>
<a href="../weeks/week3-test.html" class="test-link-card">
  <span class="test-link-icon">📝</span>
  <div class="test-link-info">
    <h3>Take the Week 3 Test</h3>
    <p>30 questions — review of Weeks 1–3 · listening, video, and multi-select</p>
  </div>
  <span class="test-link-arrow">→</span>
</a>
</div>"""


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    lessons = manifest["lessons"]

    # 1) renames (manifest + lesson JSONs)
    for lid, new_title in RENAMES.items():
        for l in lessons:
            if str(l["id"]) == lid and l.get("title") != new_title:
                l["title"] = new_title
                print(f"manifest: {lid} -> {new_title!r}")
        p = LESSONS / f"{lid}.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("title") != new_title:
                d["title"] = new_title
                p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2) create quiz_week3 ahead of the answer key (after Day 15 Grammar Homework)
    if not any(str(l["id"]) == "quiz_week3" for l in lessons):
        anchor = next((l for l in lessons
                       if re.match(r"Day\s*15\b.*Grammar\s*Homework\s*$", str(l.get("title", "")), re.I)
                       and int(l.get("day", 0) or 0) == 15), None)
        if anchor is None:
            raise SystemExit("Day 15 Grammar Homework anchor not found")
        item = {"id": "quiz_week3", "title": "Week 3 Test", "type": "reference",
                "section": anchor.get("section"), "section_type": anchor.get("section_type", "day"),
                "week": 3, "day": 15}
        lessons.insert(lessons.index(anchor) + 1, item)
        lesson_json = {
            "id": "quiz_week3", "title": "Week 3 Test", "primary_type": "reference",
            "section": anchor.get("section"), "section_type": "day", "week": 3, "day": 15,
            "html": CARD, "videos": [], "downloads": [], "images": [],
            "has_video": False, "has_images": False, "has_downloads": False,
            "placeholder": False,
        }
        (LESSONS / "quiz_week3.json").write_text(
            json.dumps(lesson_json, ensure_ascii=False, indent=2), encoding="utf-8")
        for s in manifest["sections"]:
            if s.get("label") == anchor.get("section"):
                s["lesson_count"] = s.get("lesson_count", 0) + 1
        print("created quiz_week3 (Week 3 Test) after Day 15 Grammar Homework")

    manifest["total_lessons"] = len(lessons)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("total lessons:", manifest["total_lessons"])


if __name__ == "__main__":
    main()
