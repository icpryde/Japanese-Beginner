#!/usr/bin/env python3
"""
merge_study_map.py — after parallel build_vocab_day.py runs, wire every built
vocab deck into content/study/lesson_study_map.json in one deterministic pass
(avoids concurrent read-modify-write races on the shared map).
"""
import json, os, glob

REPO = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(REPO, "content")
SPECS = os.path.join(CONTENT, "study", "vocab_specs")
MAP = os.path.join(CONTENT, "study", "lesson_study_map.json")

sm = json.load(open(MAP))
added = 0
for p in sorted(glob.glob(os.path.join(SPECS, "day_*.json"))):
    spec = json.load(open(p))
    week, day, lid = spec["week"], spec["day"], str(spec["lesson_id"])
    deck_id = f"week_{week:02d}/day_{day:02d}_vocabulary"
    deck_path = os.path.join(CONTENT, "study", "decks", f"week_{week:02d}", f"day_{day:02d}_vocabulary.json")
    if not os.path.exists(deck_path):
        print(f"skip day {day}: deck not built")
        continue
    existing = sm.get(lid, [])
    if deck_id not in existing:
        sm[lid] = [deck_id] + [d for d in existing if d != deck_id]
        added += 1

json.dump(sm, open(MAP, "w"), ensure_ascii=False, indent=2)
print(f"study map: +{added} lessons mapped, {len(sm)} total entries")
