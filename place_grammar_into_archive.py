#!/usr/bin/env python3
"""
place_grammar_into_archive.py — copy every grammar-slide lesson's ORIGINAL
files (original filenames, WAV masters) from the hand-organized
"Grammar Slides/" folder into the canonical raw archive
("Akamonkai Japanese 12 Week Beginner Course - content"), each in a folder
named with its true course position:  <ordinal>.<lesson name>Presentation

The original extraction numbered lesson folders by course position and skipped
Presentation lessons, leaving ordinal gaps — these folders fill those gaps.
The Grammar Slides/ source folder is NOT modified or deleted.

Usage: python3 place_grammar_into_archive.py [--dry-run]
"""
import os, re, sys, json, glob, shutil

REPO = os.path.dirname(os.path.abspath(__file__))
RAW = "/Users/kurisu/Documents/AI Apps/Akamonkai/Akamonkai Japanese 12 Week Beginner Course - content"
GS = "/Users/kurisu/Documents/AI Apps/Akamonkai/Grammar Slides"


def load_entries():
    """All 189 importer entries, per day, in course order."""
    src = open(os.path.join(REPO, "import_grammar_slides.py"), encoding="utf-8").read()
    legacy = re.findall(r'\{"id": "(gs_[a-z0-9_]+)", "day": (\d+), "title": "([^"]+)", "folder": "([^"]+)"', src)
    entries = [{"id": i, "day": int(d), "folder": f} for i, d, _t, f in legacy]
    extra = json.load(open(os.path.join(REPO, "grammar_slide_entries_extra.json")))
    known = {e["id"] for e in entries}
    for e in extra["entries"]:
        if e["id"] not in known:
            entries.append({"id": e["id"], "day": e["day"], "folder": e["folder"]})
    def order_key(e):
        # lesson number + part from the id (l01, l01_p2, l03_2 ...) for course order
        m = re.search(r"_l(\d+)(?:_p?(\d+))?$", e["id"])
        lesson = int(m.group(1)) if m else 99
        part = int(m.group(2)) if m and m.group(2) else 0
        return (lesson, part)

    by_day = {}
    for e in entries:
        by_day.setdefault(e["day"], []).append(e)
    for day in by_day:
        by_day[day].sort(key=order_key)
    return by_day


def load_presentations():
    cur = json.load(open(os.path.join(REPO, ".grammar_curriculum_cache.json")))
    by_day = {}
    for c in cur["contents"]:
        if c["contentable_type"] != "Presentation":
            continue
        # 'gramma\w*' also catches the site's "Grammas slides" typo (Day 2)
        if not re.search(r"gramma\w*\s*slide", c.get("name", ""), re.I):
            continue
        m = re.search(r"Day\s*(\d+)", c["name"])
        if not m:
            continue
        by_day.setdefault(int(m.group(1)), []).append(c)
    for day in by_day:
        by_day[day].sort(key=lambda c: c["position"])
    return by_day


def day_folder(day):
    hits = glob.glob(f"{RAW}/*Day {day}")
    return hits[0] if len(hits) == 1 else None


def source_folder(rel):
    p = os.path.join(GS, rel)
    if os.path.isdir(p):
        return p
    alt = os.path.join(GS, rel.replace("Week 2/", "Week 2 & 3/", 1))
    return alt if os.path.isdir(alt) else None


def main(dry=False):
    entries = load_entries()
    pres = load_presentations()
    copied = skipped = 0
    lessons_done = 0
    problems = []
    for day in sorted(pres):
        ents, prs = entries.get(day, []), pres[day]
        if len(ents) != len(prs):
            problems.append(f"day {day}: {len(ents)} source folders vs {len(prs)} lessons on site — skipped")
            continue
        dst_day = day_folder(day)
        if not dst_day:
            problems.append(f"day {day}: archive day folder not found — skipped")
            continue
        existing_ordinals = {int(m.group(1)) for f in os.listdir(dst_day) if (m := re.match(r"(\d+)\.", f))}
        for e, c in zip(ents, prs):
            src = source_folder(e["folder"])
            if not src:
                problems.append(f"day {day} {e['id']}: source folder missing ({e['folder']})")
                continue
            ordinal = c["position"] + 1
            name = re.sub(r'[/:]', "-", c["name"]).strip()
            dst = os.path.join(dst_day, f"{ordinal}.{name}Presentation")
            note = " (ordinal collides with existing lesson folder)" if ordinal in existing_ordinals else ""
            files = [f for f in os.listdir(src) if f != ".DS_Store" and os.path.isfile(os.path.join(src, f))]
            if dry:
                print(f"day {day}: {os.path.basename(dst)}  <- {len(files)} files{note}")
                lessons_done += 1
                continue
            os.makedirs(dst, exist_ok=True)
            for f in files:
                s, d = os.path.join(src, f), os.path.join(dst, f)
                if os.path.exists(d) and os.path.getsize(d) == os.path.getsize(s):
                    skipped += 1
                    continue
                shutil.copy2(s, d)
                copied += 1
            if note:
                problems.append(f"day {day}: {os.path.basename(dst)}{note}")
            lessons_done += 1
    print(f"\n{'[dry] ' if dry else ''}placed {lessons_done} lessons; copied {copied} files, {skipped} already present")
    if problems:
        print("notes:")
        for p in problems:
            print("  -", p)


if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
