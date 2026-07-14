#!/usr/bin/env python3
"""
extract_vocab_sheets.py — download each day's vocabulary sheet image(s) from the
source (Thinkific html_item API) into content/images/week_NN/day_NN/, so the
interactive-vocab pipeline (build_vocab_day.py) has rasters to crop for every day.

Usage: python3 extract_vocab_sheets.py 9-60
"""
import os, re, json, sys, urllib.parse
from extract_grammar_slides import api, curl, fetch_curriculum, parse_days

REPO = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(REPO, "content")


def dl(url, dest):
    if url.startswith("//"):
        url = "https:" + url
    code = curl(url, out=dest)
    ok = code.startswith("2") and os.path.exists(dest) and os.path.getsize(dest) > 100
    if not ok and os.path.exists(dest):
        os.remove(dest)
    return ok


def vocab_lessons(contents):
    out = {}
    for c in contents:
        m = re.match(r"Day\s*(\d+)\s*-\s*Vocabulary\s*$", c.get("name", ""), re.I)
        if m and c.get("contentable_type") == "HtmlItem":
            out[int(m.group(1))] = c["contentable_id"]
    return out


def run(days):
    cur = fetch_curriculum()
    vl = vocab_lessons(cur["contents"])
    total = 0
    for day in days:
        week = (day - 1) // 5 + 1
        cid = vl.get(day)
        if not cid:
            print(f"Day {day}: no vocabulary lesson found"); continue
        d = api(f"html_items/{cid}")
        s = json.dumps(d)
        # vocab sheet images are named Vocabulary_Day_<n>*.png/jpg on the CDN
        imgs = sorted(set(re.findall(r'https?://[^"\\ ]+Vocabulary_Day_%d[^"\\ ]*\.(?:png|jpg|jpeg)' % day, s, re.I)))
        if not imgs:  # fallback: any image in the lesson
            imgs = sorted(set(re.findall(r'https?://[^"\\ ]+\.(?:png|jpg|jpeg)', s)))
        out_dir = os.path.join(CONTENT, "images", f"week_{week:02d}", f"day_{day:02d}")
        os.makedirs(out_dir, exist_ok=True)
        got = []
        for u in imgs:
            name = urllib.parse.unquote(u.split("/")[-1])
            if dl(u, os.path.join(out_dir, name)):
                got.append(name); total += 1
        print(f"Day {day} (Wk{week}): {len(got)} sheet image(s) -> images/week_{week:02d}/day_{day:02d}/  {got}")
    print(f"\ndownloaded {total} vocab-sheet images.")


if __name__ == "__main__":
    run(parse_days(sys.argv[1:]) if len(sys.argv) > 1 else list(range(9, 61)))
