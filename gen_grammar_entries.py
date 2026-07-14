#!/usr/bin/env python3
"""
gen_grammar_entries.py — auto-generate REAL_SLIDE_ENTRIES + PAGE_AUDIO_MAP_OVERRIDES
for grammar-slide days that extract_grammar_slides.py has downloaded, so
import_grammar_slides.py doesn't need hand-editing.

Writes grammar_slide_entries_extra.json:
  {"entries": [{id, day, title, folder, anchor_id}, ...],
   "overrides": {id: {page_index: audio_index}, ...}}

import_grammar_slides.py loads this file automatically if present.

Usage: python3 gen_grammar_entries.py 26-60
"""
import os, re, json, urllib.parse, sys
from extract_grammar_slides import fetch_curriculum, api, dayof, lessonof, GRAMMAR_ROOT, parse_days

REPO = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(REPO, "content", "manifest.json")
AUDIO_PRIORITY = {".m4a": 0, ".mp3": 1, ".wav": 2}


def find_anchor(manifest_lessons, day, L):
    """Pick a stable local-manifest lesson id to insert the slides after."""
    dl = [l for l in manifest_lessons if int(l.get("day", 0) or 0) == day]
    pats = [
        rf"^Day\s*{day}\s*Lesson\s*{L}\b.*grammar\s*video",
        rf"^Day\s*{day}\s*Lesson\s*{L}\b.*video\s*repetition",
        rf"^Day\s*{day}\s*Lesson\s*{L}\b.*\(\s*video",
        rf"^Day\s*{day}\s*Lesson\s*{L}\b",
    ]
    for pat in pats:
        for l in dl:
            if re.search(pat, str(l.get("title", "")), re.I):
                return str(l["id"])
    for l in dl:  # fallbacks
        if "grammar homework" in str(l.get("title", "")).lower():
            return str(l["id"])
    return str(dl[-1]["id"]) if dl else None


def audio_sort_index(folder):
    """Replicate import_grammar_slides.py audio ordering -> {filename: index}."""
    auds = [f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in AUDIO_PRIORITY]
    auds.sort(key=lambda n: (AUDIO_PRIORITY.get(os.path.splitext(n)[1].lower(), 9), n.lower()))
    return {n: i for i, n in enumerate(auds)}, len(auds)


def build(days):
    cur = fetch_curriculum()
    manifest = json.load(open(MANIFEST))
    mlessons = manifest["lessons"]
    contents = cur["contents"]
    entries, overrides, skipped = [], {}, []

    for day in days:
        week = (day - 1) // 5 + 1
        lessons = sorted(
            [c for c in contents if dayof(c.get("name", "")) == day
             and c.get("contentable_type") == "Presentation"
             and re.search(r"grammar\s*slide", c.get("name", ""), re.I)],
            key=lambda c: c.get("position", 0))
        seen_L = {}
        for idx, c in enumerate(lessons, 1):
            L = lessonof(c["name"])
            seen_L[L] = seen_L.get(L, 0) + 1
            suffix = "" if seen_L[L] == 1 else f"_{seen_L[L]}"
            eid = f"gs_w{week:02d}_d{day:02d}_l{L:02d}{suffix}"
            folder_rel = f"Week {week}/Day {day}/{idx}. Day {day} Lesson {L}"
            folder_abs = os.path.join(GRAMMAR_ROOT, folder_rel)
            if not os.path.isdir(folder_abs):
                skipped.append((day, L, "folder not downloaded"))
                continue
            anchor = find_anchor(mlessons, day, L)
            if not anchor:
                skipped.append((day, L, "no anchor in manifest"))
                continue
            entries.append({"id": eid, "day": day,
                            "title": f"Day {day} Lesson {L} - Grammar Slides",
                            "folder": folder_rel, "anchor_id": anchor})
            # per-slide audio override from the API positions
            pres = api(f"presentations/{c['contentable_id']}")
            items = sorted(pres.get("presentation_items", []), key=lambda it: it.get("position", 0))
            aud_idx, n_aud = audio_sort_index(folder_abs)
            if n_aud > 1:
                omap = {}
                for pos, it in enumerate(items):
                    au = it.get("audio_file_url")
                    if not au:
                        continue
                    fn = urllib.parse.unquote(au.split("/")[-1])
                    if fn in aud_idx:
                        omap[pos] = aud_idx[fn]
                if len(set(omap.values())) > 1:  # only meaningful if slides use different audios
                    overrides[eid] = omap
    return entries, overrides, skipped


if __name__ == "__main__":
    days = parse_days(sys.argv[1:]) if len(sys.argv) > 1 else list(range(26, 61))
    entries, overrides, skipped = build(days)
    out = os.path.join(REPO, "grammar_slide_entries_extra.json")
    json.dump({"entries": entries, "overrides": overrides},
              open(out, "w"), ensure_ascii=False, indent=2)
    print(f"generated {len(entries)} entries, {len(overrides)} multi-audio overrides -> {out}")
    if skipped:
        print(f"skipped {len(skipped)}:")
        for s in skipped[:20]:
            print("  ", s)
    # summary by day
    from collections import Counter
    print("entries per day:", dict(sorted(Counter(e['day'] for e in entries).items())))
