#!/usr/bin/env python3
"""
extract_quizzes.py — download quiz-review media (listening audio + question images)
and save the full quiz structure (questions, choices, correct answers) for each
Quiz-type lesson, via the Thinkific course-player API + gogonihon-cookies.txt.

Outputs:
  content/audio/tests/<key>/<file>.wav|mp3
  content/images/tests/<key>/<file>.png|jpg
  content/quizzes/<key>.json         (raw quiz JSON: quiz, questions, choices)

Usage: python3 extract_quizzes.py
"""
import os, json, subprocess, urllib.parse, re
from extract_grammar_slides import api, curl  # reuse authed helpers

REPO = os.path.dirname(os.path.abspath(__file__))
CONTENT = os.path.join(REPO, "content")

# key -> contentable_id  (from the curriculum: Quiz-type lessons)
QUIZZES = {
    "week_03": 863670,
    "week_08": 918938,
    "week_09-12": 957922,
}


def dl(url, dest):
    if url.startswith("//"):
        url = "https:" + url
    code = curl(url, out=dest)
    ok = code.startswith("2") and os.path.exists(dest) and os.path.getsize(dest) > 100
    if not ok and os.path.exists(dest):
        os.remove(dest)
    return ok


def urls_in(obj, exts):
    s = json.dumps(obj)
    pat = r'(?://|https?://)[^"\\ ]+\.(?:' + "|".join(exts) + r')'
    return sorted(set(re.findall(pat, s, re.I)))


def extract(key, cid):
    data = api(f"quizzes/{cid}")
    os.makedirs(os.path.join(CONTENT, "quizzes"), exist_ok=True)
    json.dump(data, open(os.path.join(CONTENT, "quizzes", f"{key}.json"), "w"), ensure_ascii=False, indent=1)

    aud_dir = os.path.join(CONTENT, "audio", "tests", key)
    img_dir = os.path.join(CONTENT, "images", "tests", key)
    os.makedirs(aud_dir, exist_ok=True)
    os.makedirs(img_dir, exist_ok=True)

    audios = urls_in(data, ["m4a", "mp3", "wav"])
    images = urls_in(data, ["png", "jpg", "jpeg"])
    na = ni = 0
    for u in audios:
        if dl(u, os.path.join(aud_dir, urllib.parse.unquote(u.split("/")[-1]))):
            na += 1
    for u in images:
        if dl(u, os.path.join(img_dir, urllib.parse.unquote(u.split("/")[-1]))):
            ni += 1
    nq = len(data.get("questions", []))
    print(f"{key}: {nq} questions | {na}/{len(audios)} audio, {ni}/{len(images)} images "
          f"-> content/audio/tests/{key}, content/images/tests/{key}, content/quizzes/{key}.json")
    return na, ni


if __name__ == "__main__":
    ta = ti = 0
    for key, cid in QUIZZES.items():
        a, i = extract(key, cid)
        ta += a; ti += i
    print(f"\nTotal: {ta} audio + {ti} images across {len(QUIZZES)} quizzes.")
