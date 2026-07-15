#!/usr/bin/env python3
"""
extract_grammar_slides.py — Download grammar-slide presentations (images + audio)
for given course days straight from the Thinkific course-player API, into the
Grammar Slides/ folder in the exact layout import_grammar_slides.py expects.

Auth: uses gogonihon-cookies.txt (Netscape jar) in the repo root.

Usage:
    python3 extract_grammar_slides.py 26              # one day
    python3 extract_grammar_slides.py 26 27 28        # several
    python3 extract_grammar_slides.py 26-60           # a range
    python3 extract_grammar_slides.py 26 --dry-run    # list what would download
"""
import os, sys, re, json, subprocess, urllib.parse, argparse

REPO = os.path.dirname(os.path.abspath(__file__))
COOKIES = os.path.join(REPO, "gogonihon-cookies.txt")
GRAMMAR_ROOT = "/Users/kurisu/Documents/AI Apps/Akamonkai/Grammar Slides"
BASE = "https://japaneseonline.gogonihon.com"
SLUG = "akamonkai-japanese-12-week-beginner-course"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def curl(url, out=None):
    cmd = ["curl", "-s", "--max-time", "60", "-b", COOKIES, "-A", UA,
           "-H", "Accept: application/json", "-H", "X-Requested-With: XMLHttpRequest", url]
    if out:
        cmd += ["-o", out, "-w", "%{http_code}"]
        code = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        return code
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def api(path):
    return json.loads(curl(f"{BASE}/api/course_player/v2/{path}"))


def fetch_curriculum(cache=os.path.join(REPO, ".grammar_curriculum_cache.json")):
    if os.path.exists(cache):
        return json.load(open(cache))
    data = api(f"courses/{SLUG}")
    json.dump(data, open(cache, "w"), ensure_ascii=False)
    return data


def dayof(name):
    m = re.search(r"Day\s*(\d+)", name or "")
    return int(m.group(1)) if m else None


def lessonof(name):
    m = re.search(r"Lesson\s*(\d+)", name or "")
    return int(m.group(1)) if m else 1


def download(url, dest, dry=False):
    if url.startswith("//"):
        url = "https:" + url
    if dry:
        print("      would GET", url.split("/")[-1][:60])
        return True
    code = curl(url, out=dest)
    ok = code.startswith("2") and os.path.getsize(dest) > 100
    if not ok and os.path.exists(dest):
        os.remove(dest)
    return ok


def extract_day(contents, day, dry=False):
    week = (day - 1) // 5 + 1
    lessons = sorted(
        [c for c in contents
         if dayof(c.get("name", "")) == day
         and c.get("contentable_type") == "Presentation"
         and re.search(r"gramma\w*\s*slide", c.get("name", ""), re.I)],
        key=lambda c: c.get("position", 0))
    if not lessons:
        print(f"Day {day}: no grammar-slide presentations found on site.")
        return 0
    print(f"Day {day} (Week {week}): {len(lessons)} grammar-slide lesson(s)")
    n_files = 0
    for idx, c in enumerate(lessons, 1):
        L = lessonof(c["name"])
        cid = c["contentable_id"]
        pres = api(f"presentations/{cid}")
        items = sorted(pres.get("presentation_items", []), key=lambda it: it.get("position", 0))
        folder = os.path.join(GRAMMAR_ROOT, f"Week {week}", f"Day {day}", f"{idx}. Day {day} Lesson {L}")
        print(f"  Lesson {L}: {len(items)} slide(s)  ->  Week {week}/Day {day}/{idx}. Day {day} Lesson {L}")
        if not dry:
            os.makedirs(folder, exist_ok=True)
        seen = set()
        seen_logical = set()   # the course re-uploads the same audio per slide
        for it in items:
            for key in ("image_file_url", "audio_file_url"):
                u = it.get(key)
                if not u or u in seen:
                    continue
                seen.add(u)
                fname = urllib.parse.unquote(u.split("/")[-1])
                if key == "audio_file_url":
                    logical = re.sub(r"^[A-Za-z0-9]{18,22}_", "", fname)
                    if logical in seen_logical:
                        continue
                    seen_logical.add(logical)
                dest = os.path.join(folder, fname)
                if download(u, dest, dry):
                    n_files += 1
    return n_files


def parse_days(tokens):
    days = []
    for t in tokens:
        if "-" in t:
            a, b = t.split("-"); days += list(range(int(a), int(b) + 1))
        else:
            days.append(int(t))
    return sorted(set(days))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("days", nargs="+", help="day numbers or ranges, e.g. 26 or 26-60")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="re-fetch curriculum")
    a = ap.parse_args()
    if a.refresh:
        c = os.path.join(REPO, ".grammar_curriculum_cache.json")
        if os.path.exists(c): os.remove(c)
    cur = fetch_curriculum()
    contents = cur["contents"]
    total = 0
    for day in parse_days(a.days):
        total += extract_day(contents, day, dry=a.dry_run)
    print(f"\n{'[dry] ' if a.dry_run else ''}downloaded {total} files.")
