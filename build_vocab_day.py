#!/usr/bin/env python3
"""
build_vocab_day.py — Build the interactive vocabulary feature for one course day.

For a given day it:
  1. Auto-crops each word's illustration from the vocab page raster(s)
     (illustrations are colourful clip-art; word text is pure black, so the
     bounding box of *coloured* pixels inside each grid cell isolates the art).
  2. Copies that day's native-speaker per-word audio out of the raw archive.
  3. Writes the study deck JSON (word cards + flashcards) and wires it into
     content/study/lesson_study_map.json.

Then run `python3 build_site.py` to render it into site/.

Day specs live in vocab_day_specs.py (one dict per day). Usage:
    python3 build_vocab_day.py 8            # build day 8
    python3 build_vocab_day.py 8 --dry-run  # report only, write nothing
"""
import sys, os, json, shutil, argparse
import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(REPO, "content")
RAW = "/Users/kurisu/Documents/AI Apps/Akamonkai/Akamonkai Japanese 12 Week Beginner Course - content"


def detect_illustrations(page_paths, min_colored=400, min_band_h=30, merge_gap=40):
    """Yield (page_index, PIL.Image crop) for every illustration, in reading
    order (top->bottom, left col then right col) across the given page rasters."""
    out = []
    for pi, path in enumerate(page_paths):
        if not os.path.exists(path):
            continue
        im = Image.open(path).convert("RGB")
        arr = np.asarray(im).astype(np.int16)
        H, W, _ = arr.shape
        mx = arr.max(axis=2); mn = arr.min(axis=2); gray = arr.mean(axis=2)
        colored = ((mx - mn) > 22) & (gray < 250)   # colourful illustration pixels
        nonwhite = (mx < 245)                         # any ink (text or art)

        row_has = nonwhite.sum(axis=1) > 4
        bands, y = [], 0
        while y < H:
            if row_has[y]:
                y0 = y
                while y < H and row_has[y]:
                    y += 1
                if y - y0 > min_band_h:
                    bands.append((y0, y))
            else:
                y += 1
        merged = []
        for b in bands:
            if merged and b[0] - merged[-1][1] < merge_gap:
                merged[-1] = (merged[-1][0], b[1])
            else:
                merged.append(list(b))
        bands = [tuple(b) for b in merged]

        midx = W // 2
        for (y0, y1) in bands:
            for (x0, x1) in [(0, midx), (midx, W)]:
                sub = colored[y0:y1, x0:x1]
                if int(sub.sum()) < min_colored:
                    continue
                ys, xs = np.where(sub)
                pad = 8
                ex0, ey0 = max(0, xs.min()+x0-pad), max(0, ys.min()+y0-pad)
                ex1, ey1 = min(W, xs.max()+x0+pad), min(H, ys.max()+y0+pad)
                out.append((pi, im.crop((ex0, ey0, ex1, ey1))))
    return out


def build_day(spec, dry_run=False):
    week, day, lid = spec["week"], spec["day"], spec["lesson_id"]
    wk, dd = f"week_{week:02d}", f"day_{day:02d}"

    # sanity: lesson id must exist in manifest
    manifest = json.load(open(os.path.join(CONTENT, "manifest.json")))
    mlessons = {str(l["id"]) for l in manifest["lessons"]}
    if str(lid) not in mlessons:
        raise SystemExit(f"lesson_id {lid} not in manifest — check spec")

    page_paths = [os.path.join(CONTENT, "images", wk, dd, p) for p in spec["pages"]]
    illustrated = [w for w in spec["words"] if w.get("img")]
    crops = detect_illustrations(page_paths)
    if len(crops) != len(illustrated):
        raise SystemExit(
            f"DETECTION MISMATCH day {day}: found {len(crops)} illustrations "
            f"but spec lists {len(illustrated)} illustrated words. "
            f"Adjust spec order/flags or detector thresholds before writing.")

    raw_audio = os.path.join(RAW, spec["raw_audio_dir"])
    missing = [w["audio"] for w in spec["words"]
               if not os.path.exists(os.path.join(raw_audio, w["audio"]))]
    if missing:
        raise SystemExit(f"missing raw audio for day {day}: {missing}")

    print(f"Day {day}: {len(spec['words'])} words "
          f"({len(illustrated)} illustrated, {len(spec['words'])-len(illustrated)} text-only); "
          f"audio all present.")
    if dry_run:
        print("dry-run — nothing written.")
        return

    img_dir = os.path.join(CONTENT, "images", "study", wk, dd)
    aud_dir = os.path.join(CONTENT, "audio", "vocabulary", wk, dd)
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(aud_dir, exist_ok=True)

    for w, (_, crop) in zip(illustrated, crops):
        crop.save(os.path.join(img_dir, w["id"] + ".png"))

    items = []
    for w in spec["words"]:
        ext = os.path.splitext(w["audio"])[1].lower()
        aud_name = w["id"] + ext
        shutil.copy2(os.path.join(raw_audio, w["audio"]), os.path.join(aud_dir, aud_name))
        item = {"id": w["id"], "japanese": w["japanese"], "romaji": w["romaji"],
                "english": w["english"]}
        if w.get("img"):
            item["image"] = f"../images/study/{wk}/{dd}/{w['id']}.png"
        item["audio"] = f"../audio/vocabulary/{wk}/{dd}/{aud_name}"
        item["alt"] = w.get("alt", w["english"])
        items.append(item)

    deck = {
        "id": f"{wk}/{dd}_vocabulary", "kind": "image", "title": spec["title"],
        "context_blocks": spec.get("context_blocks",
            [{"japanese": "おぼえましょう", "romaji": "oboemashou", "english": "Let's remember"}]),
        "description": "Image-based vocabulary cards with native-speaker audio. "
                       "The original PDF and Google Drive resources remain below.",
        "flashcards_title": f"{spec['title']} Flashcards", "items": items,
    }
    deck_dir = os.path.join(CONTENT, "study", "decks", wk)
    os.makedirs(deck_dir, exist_ok=True)
    with open(os.path.join(deck_dir, f"{dd}_vocabulary.json"), "w") as f:
        json.dump(deck, f, ensure_ascii=False, indent=2)

    sm_path = os.path.join(CONTENT, "study", "lesson_study_map.json")
    sm = json.load(open(sm_path))
    deck_id = f"{wk}/{dd}_vocabulary"
    existing = sm.get(str(lid), [])
    if deck_id not in existing:
        existing = [deck_id] + [d for d in existing if d != deck_id]
    sm[str(lid)] = existing
    with open(sm_path, "w") as f:
        json.dump(sm, f, ensure_ascii=False, indent=2)

    print(f"  wrote {len(illustrated)} images -> {img_dir}")
    print(f"  wrote {len(items)} audio     -> {aud_dir}")
    print(f"  wrote deck                 -> content/study/decks/{wk}/{dd}_vocabulary.json")
    print(f"  mapped lesson {lid}        -> {deck_id}")
    print("  next: python3 build_site.py")


if __name__ == "__main__":
    from vocab_day_specs import SPECS
    ap = argparse.ArgumentParser()
    ap.add_argument("day", type=int)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.day not in SPECS:
        raise SystemExit(f"no spec for day {a.day}; add it to vocab_day_specs.py")
    build_day(SPECS[a.day], dry_run=a.dry_run)
