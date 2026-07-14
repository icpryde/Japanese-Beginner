#!/usr/bin/env python3
"""
build_vocab_day.py — Build the interactive vocabulary feature for one course day.

For a given day it:
  1. Auto-crops each word's illustration from the vocab page raster(s)
     (illustrations are colourful clip-art; word text is pure black, so the
     bounding box of *coloured* pixels inside each grid cell isolates the art).
  2. Copies that day's native-speaker per-word audio out of the raw archive.
  3. Writes the study deck JSON (word cards + flashcards).
  4. Optionally (--update-map) wires the deck into content/study/lesson_study_map.json.
     Parallel builds should NOT pass --update-map (shared-file race); run
     merge_study_map.py once afterwards instead.

Day specs are JSON files in content/study/vocab_specs/day_NN.json (see
vocab_day_specs.py SPECS for the legacy in-Python format, still supported).

Spec format:
  {"week": 2, "day": 9, "lesson_id": "12645502", "title": "Day 9 Vocabulary",
   "raw_audio_dir": "<path relative to RAW archive>",
   "pages": ["<file in content/images/week_NN/day_NN/>", ...],   # in page order
   "detect": {"min_colored": 400, "min_band_h": 30, "merge_gap": 40},  # optional
   "words": [{"id","japanese","romaji","english","alt","audio","img"}, ...]}
   - words listed in sheet reading order; img=true words must match the
     auto-detected illustration count and order (top->bottom, left col then
     right col, page by page).
   - "audio": exact filename inside raw_audio_dir, or omit/null for no audio.

Usage:
    python3 build_vocab_day.py 9                    # build day 9 from JSON spec
    python3 build_vocab_day.py 9 --dry-run          # validate only
    python3 build_vocab_day.py 9 --contact-sheet    # also render labeled crop sheet
    python3 build_vocab_day.py 9 --update-map       # also update lesson_study_map.json
"""
import sys, os, json, shutil, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(REPO, "content")
SPecs_DIR = os.path.join(CONTENT, "study", "vocab_specs")
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


def render_contact_sheet(items_with_images, img_dir, out_path):
    """Labeled grid of final crops for human/agent verification."""
    cols, cell, pad, lab = 5, 150, 14, 30
    rows = (len(items_with_images) + cols - 1) // cols or 1
    W = cols*(cell+pad)+pad; H = rows*(cell+lab+pad)+pad
    sheet = Image.new("RGB", (W, H), (250, 250, 250)); dr = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    for i, it in enumerate(items_with_images):
        r, c = divmod(i, cols); x = pad+c*(cell+pad); y = pad+r*(cell+lab+pad)
        dr.rectangle([x, y, x+cell, y+cell], outline=(200, 200, 200), width=1)
        p = os.path.join(img_dir, it["id"] + ".png")
        if os.path.exists(p):
            im = Image.open(p).convert("RGB")
            im.thumbnail((cell-8, cell-8))
            sheet.paste(im, (x+(cell-im.width)//2, y+(cell-im.height)//2))
        dr.text((x+2, y+cell+4), it["romaji"][:22], fill=(20, 20, 20), font=font)
        dr.text((x+2, y+cell+18), it["english"][:22], fill=(120, 120, 120), font=font)
    sheet.save(out_path)
    return out_path


def load_spec(day):
    p = os.path.join(SPecs_DIR, f"day_{day:02d}.json")
    if os.path.exists(p):
        return json.load(open(p))
    try:
        from vocab_day_specs import SPECS  # legacy in-Python specs
        if day in SPECS:
            return SPECS[day]
    except ImportError:
        pass
    raise SystemExit(f"no spec found: {p} (and no legacy SPECS entry)")


def build_day(spec, dry_run=False, contact_sheet=False, update_map=False):
    week, day, lid = spec["week"], spec["day"], str(spec["lesson_id"])
    wk, dd = f"week_{week:02d}", f"day_{day:02d}"

    manifest = json.load(open(os.path.join(CONTENT, "manifest.json")))
    if lid not in {str(l["id"]) for l in manifest["lessons"]}:
        raise SystemExit(f"lesson_id {lid} not in manifest — check spec")

    ids = [w["id"] for w in spec["words"]]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"duplicate word ids in spec: {dupes}")

    page_paths = [os.path.join(CONTENT, "images", wk, dd, p) for p in spec["pages"]]
    missing_pages = [p for p in page_paths if not os.path.exists(p)]
    if missing_pages:
        raise SystemExit(f"missing page rasters: {missing_pages}")

    illustrated = [w for w in spec["words"] if w.get("img")]
    det = spec.get("detect", {})
    crops = detect_illustrations(page_paths, **{k: det[k] for k in
                                                ("min_colored", "min_band_h", "merge_gap") if k in det})
    if len(crops) != len(illustrated):
        raise SystemExit(
            f"DETECTION MISMATCH day {day}: found {len(crops)} illustrations "
            f"but spec lists {len(illustrated)} illustrated words. "
            f"Fix img flags / spec order, or tune spec['detect'] "
            f"(min_colored={det.get('min_colored',400)}, min_band_h={det.get('min_band_h',30)}, "
            f"merge_gap={det.get('merge_gap',40)}).")

    raw_audio = os.path.join(RAW, spec["raw_audio_dir"]) if spec.get("raw_audio_dir") else None
    with_audio = [w for w in spec["words"] if w.get("audio")]
    missing = [w["audio"] for w in with_audio
               if not raw_audio or not os.path.exists(os.path.join(raw_audio, w["audio"]))]
    if missing:
        raise SystemExit(f"missing raw audio for day {day}: {missing}")

    print(f"Day {day}: {len(spec['words'])} words "
          f"({len(illustrated)} illustrated, {len(spec['words'])-len(illustrated)} text-only, "
          f"{len(with_audio)} with audio).")
    if dry_run:
        print("dry-run — nothing written.")
        return

    img_dir = os.path.join(CONTENT, "images", "study", wk, dd)
    aud_dir = os.path.join(CONTENT, "audio", "vocabulary", wk, dd)
    os.makedirs(img_dir, exist_ok=True)
    if with_audio:
        os.makedirs(aud_dir, exist_ok=True)

    for w, (_, crop) in zip(illustrated, crops):
        crop.save(os.path.join(img_dir, w["id"] + ".png"))

    items = []
    for w in spec["words"]:
        item = {"id": w["id"], "japanese": w["japanese"], "romaji": w["romaji"],
                "english": w["english"]}
        if w.get("img"):
            item["image"] = f"../images/study/{wk}/{dd}/{w['id']}.png"
        if w.get("audio"):
            ext = os.path.splitext(w["audio"])[1].lower()
            aud_name = w["id"] + ext
            shutil.copy2(os.path.join(raw_audio, w["audio"]), os.path.join(aud_dir, aud_name))
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

    if update_map:
        sm_path = os.path.join(CONTENT, "study", "lesson_study_map.json")
        sm = json.load(open(sm_path))
        deck_id = f"{wk}/{dd}_vocabulary"
        existing = sm.get(lid, [])
        if deck_id not in existing:
            existing = [deck_id] + [d for d in existing if d != deck_id]
        sm[lid] = existing
        with open(sm_path, "w") as f:
            json.dump(sm, f, ensure_ascii=False, indent=2)

    sheet_path = None
    if contact_sheet and illustrated:
        sheet_path = os.path.join(SPecs_DIR, f"day_{day:02d}_contact.png")
        render_contact_sheet(illustrated, img_dir, sheet_path)

    print(f"  wrote {len(illustrated)} images -> {img_dir}")
    print(f"  wrote {len(with_audio)} audio  -> {aud_dir if with_audio else '(none)'}")
    print(f"  wrote deck               -> content/study/decks/{wk}/{dd}_vocabulary.json")
    if sheet_path:
        print(f"  contact sheet            -> {sheet_path}")
    if update_map:
        print(f"  mapped lesson {lid}      -> {wk}/{dd}_vocabulary")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("day", type=int)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--update-map", action="store_true")
    a = ap.parse_args()
    build_day(load_spec(a.day), dry_run=a.dry_run,
              contact_sheet=a.contact_sheet, update_map=a.update_map)
