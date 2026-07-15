#!/usr/bin/env python3
"""
fix_grammar_audio_maps.py — rebuild every grammar-slide lesson's per-slide
audio map from the course API (the ground truth), fixing two systemic bugs:

  1. The course re-uploads the same audio file once per slide (different
     upload-hash filenames), so the API extractor saved duplicate copies —
     lessons showed 2-4 identical players with confusing labels.
     -> duplicate files are deleted from the extractor-created folders
        (Weeks 6-12) and mirrored in the raw-archive Presentation folders.
        Hand-collected folders (days 1-25) are never modified.

  2. Slides with NO narration were silently mapped to audio #1.
     -> now mapped to -1 (no player shown on that slide).

Writes accurate overrides for ALL lessons into grammar_slide_entries_extra.json.
Then run: GS_REIMPORT_IDS=<all> import_grammar_slides.py ; transcode_audio.py ;
build_site.py.
"""
import os, re, json, glob, time, urllib.parse
from extract_grammar_slides import api as _api

REPO = os.path.dirname(os.path.abspath(__file__))
_PRES_CACHE = os.path.join(REPO, ".presentations_cache")
os.makedirs(_PRES_CACHE, exist_ok=True)


def fetch_presentation(cid):
    """api('presentations/<id>') with retries, pacing, and a disk cache."""
    cache = os.path.join(_PRES_CACHE, f"{cid}.json")
    if os.path.exists(cache):
        return json.load(open(cache))
    last = None
    for attempt in range(4):
        try:
            time.sleep(0.3 * (attempt + 1))
            d = _api(f"presentations/{cid}")
            json.dump(d, open(cache, "w"), ensure_ascii=False)
            return d
        except Exception as e:
            last = e
    raise RuntimeError(f"presentation {cid} failed after retries: {last}")
GS = "/Users/kurisu/Documents/AI Apps/Akamonkai/Grammar Slides"
RAW = "/Users/kurisu/Documents/AI Apps/Akamonkai/Akamonkai Japanese 12 Week Beginner Course - content"
AUDIO_PRIORITY = {".m4a": 0, ".mp3": 1, ".wav": 2}
HASH_RE = re.compile(r"^[A-Za-z0-9]{18,22}_")


def logical(name):
    return HASH_RE.sub("", name)


def load_entries_by_day():
    src = open(os.path.join(REPO, "import_grammar_slides.py"), encoding="utf-8").read()
    legacy = re.findall(r'\{"id": "(gs_[a-z0-9_]+)", "day": (\d+), "title": "[^"]+", "folder": "([^"]+)"', src)
    entries = [{"id": i, "day": int(d), "folder": f} for i, d, f in legacy]
    extra = json.load(open(os.path.join(REPO, "grammar_slide_entries_extra.json")))
    known = {e["id"] for e in entries}
    entries += [{"id": e["id"], "day": e["day"], "folder": e["folder"]}
                for e in extra["entries"] if e["id"] not in known]

    def order_key(e):
        m = re.search(r"_l(\d+)(?:_p?(\d+))?$", e["id"])
        return (int(m.group(1)) if m else 99, int(m.group(2)) if m and m.group(2) else 0)

    by_day = {}
    for e in entries:
        by_day.setdefault(e["day"], []).append(e)
    for d in by_day:
        by_day[d].sort(key=order_key)
    return by_day


def load_presentations_by_day():
    cur = json.load(open(os.path.join(REPO, ".grammar_curriculum_cache.json")))
    by_day = {}
    for c in cur["contents"]:
        if c["contentable_type"] != "Presentation":
            continue
        if not re.search(r"gramma\w*\s*slide", c.get("name", ""), re.I):
            continue
        m = re.search(r"Day\s*(\d+)", c["name"])
        if m:
            by_day.setdefault(int(m.group(1)), []).append(c)
    for d in by_day:
        by_day[d].sort(key=lambda c: c["position"])
    return by_day


def resolve_folder(rel):
    p = os.path.join(GS, rel)
    if os.path.isdir(p):
        return p
    alt = os.path.join(GS, rel.replace("Week 2/", "Week 2 & 3/", 1))
    return alt if os.path.isdir(alt) else None


def archive_mirrors(fname):
    """Archive Presentation-folder copies of a Grammar Slides file."""
    return glob.glob(os.path.join(RAW, "*", "*Presentation", fname))


def main():
    entries = load_entries_by_day()
    pres = load_presentations_by_day()
    extra_path = os.path.join(REPO, "grammar_slide_entries_extra.json")
    extra = json.load(open(extra_path))
    overrides = {}
    deduped_files = 0
    problems = []

    for day in sorted(pres):
        ents, prs = entries.get(day, []), pres[day]
        if len(ents) != len(prs):
            problems.append(f"day {day}: {len(ents)} entries vs {len(prs)} presentations — skipped")
            continue
        extractor_made = day >= 26  # Weeks 6-12 folders were created by the extractor
        for e, c in zip(ents, prs):
            folder = resolve_folder(e["folder"])
            if not folder:
                problems.append(f"{e['id']}: folder missing")
                continue
            items = sorted(fetch_presentation(c["contentable_id"]).get("presentation_items", []),
                           key=lambda it: it.get("position", 0))

            auds = [f for f in os.listdir(folder)
                    if os.path.splitext(f)[1].lower() in AUDIO_PRIORITY]

            # 1) dedupe hash-duplicates (extractor-created folders only)
            if extractor_made or "1b." in e["folder"] or e["id"] == "gs_w08_d37_l04":
                by_logical = {}
                for f in sorted(auds):
                    by_logical.setdefault((logical(f), os.path.getsize(os.path.join(folder, f))), []).append(f)
                for (_, _), copies in by_logical.items():
                    for dupe in copies[1:]:
                        os.remove(os.path.join(folder, dupe))
                        for m in archive_mirrors(dupe):
                            os.remove(m)
                        deduped_files += 1
                auds = [f for f in os.listdir(folder)
                        if os.path.splitext(f)[1].lower() in AUDIO_PRIORITY]

            # 2) importer's audio ordering -> index
            auds.sort(key=lambda n: (AUDIO_PRIORITY.get(os.path.splitext(n)[1].lower(), 9), n.lower()))
            idx_of = {}
            for i, f in enumerate(auds):
                idx_of[f] = i
                idx_of.setdefault(logical(f), i)

            # 3) per-slide map from API positions (-1 = no narration)
            omap = {}
            unmatched = set()
            for pos, it in enumerate(items):
                u = it.get("audio_file_url")
                if not u:
                    omap[pos] = -1
                    continue
                fn = urllib.parse.unquote(u.split("/")[-1])
                i = idx_of.get(fn, idx_of.get(logical(fn)))
                if i is None:
                    unmatched.add(fn)
                    omap[pos] = 0
                else:
                    omap[pos] = i
            if unmatched:
                problems.append(f"{e['id']}: unmatched API audio {sorted(unmatched)[:2]}")
            if len(items) and (len(set(omap.values())) > 1 or -1 in omap.values() or len(auds) > 1):
                overrides[e["id"]] = omap

    extra["overrides"] = overrides
    json.dump(extra, open(extra_path, "w"), ensure_ascii=False, indent=2)
    print(f"overrides written for {len(overrides)} lessons; "
          f"deleted {deduped_files} duplicate audio files (+ archive mirrors)")
    if problems:
        print("problems:")
        for p in problems:
            print("  -", p)


if __name__ == "__main__":
    main()
