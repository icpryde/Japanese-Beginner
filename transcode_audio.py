#!/usr/bin/env python3
"""
transcode_audio.py — convert every uncompressed .wav under content/audio to
AAC .m4a (~20x smaller) so playback starts instantly, and rewrite every
reference (lesson JSON html/downloads, study decks). Originals remain in the
raw archive / Grammar Slides folders; content/ keeps only the compact copies.

Quiz test pages resolve renamed clips via the extension fallback in
build_site.py's _localize_quiz_fragment.

Usage: python3 transcode_audio.py [--dry-run]
"""
import os, sys, json, glob, subprocess

REPO = os.path.dirname(os.path.abspath(__file__))
AUDIO = os.path.join(REPO, "content", "audio")
BITRATE = "96000"


def transcode(src):
    dst = os.path.splitext(src)[0] + ".m4a"
    if os.path.exists(dst):
        os.remove(dst)
    r = subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", BITRATE, src, dst],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) < 200:
        if os.path.exists(dst):
            os.remove(dst)
        return None
    return dst


def main(dry=False):
    wavs = sorted(glob.glob(os.path.join(AUDIO, "**", "*.wav"), recursive=True))
    print(f"{len(wavs)} wav files under content/audio")
    if dry:
        total = sum(os.path.getsize(w) for w in wavs)
        print(f"dry-run: {total/1e6:.0f} MB of wav would be transcoded")
        return

    renamed = {}   # old basename -> new basename
    before = after = 0
    failed = []
    for w in wavs:
        b = os.path.getsize(w)
        dst = transcode(w)
        if not dst:
            failed.append(w)
            continue
        before += b
        after += os.path.getsize(dst)
        renamed[os.path.basename(w)] = os.path.basename(dst)
        os.remove(w)
    print(f"transcoded {len(renamed)}: {before/1e6:.0f} MB -> {after/1e6:.0f} MB "
          f"({(1 - after/max(before,1))*100:.0f}% smaller); failed: {len(failed)}")
    for f in failed:
        print("  FAILED:", f)

    # rewrite references in lesson JSONs and study decks
    n_lessons = n_decks = 0
    for p in glob.glob(os.path.join(REPO, "content", "lessons", "*.json")):
        raw = open(p, encoding="utf-8").read()
        out = raw
        for old, new in renamed.items():
            if old in out:
                out = out.replace(old, new)
        if out != raw:
            open(p, "w", encoding="utf-8").write(out)
            n_lessons += 1
    for p in glob.glob(os.path.join(REPO, "content", "study", "decks", "**", "*.json"), recursive=True):
        raw = open(p, encoding="utf-8").read()
        out = raw
        for old, new in renamed.items():
            if old in out:
                out = out.replace(old, new)
        if out != raw:
            open(p, "w", encoding="utf-8").write(out)
            n_decks += 1
    print(f"rewrote references in {n_lessons} lesson JSONs, {n_decks} decks")

    # sanity: no dangling .wav references left in content
    dangle = 0
    for p in glob.glob(os.path.join(REPO, "content", "lessons", "*.json")) + \
             glob.glob(os.path.join(REPO, "content", "study", "decks", "**", "*.json"), recursive=True):
        t = open(p, encoding="utf-8").read()
        for old in renamed:
            if old in t:
                print("  DANGLING:", p, "->", old)
                dangle += 1
    print("dangling refs:", dangle)


if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
