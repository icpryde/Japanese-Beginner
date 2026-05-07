#!/usr/bin/env python3
import json
import os
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
CONTENT_DIR = PROJECT_ROOT / "content"
LESSONS_DIR = CONTENT_DIR / "lessons"
MANIFEST_PATH = CONTENT_DIR / "manifest.json"
IMAGES_DIR = CONTENT_DIR / "images"
GRAMMAR_IMAGES_DIR = IMAGES_DIR / "grammar"
AUDIO_DIR = CONTENT_DIR / "audio"

GRAMMAR_ROOT_CANDIDATES = [
    Path("/Users/kurisu/Documents/AI Apps/Akamonkai/Grammar Slides"),
    Path("/Users/kurisu/Documents/AI Apps/Grammar Slides"),
]
GRAMMAR_ROOT = next((p for p in GRAMMAR_ROOT_CANDIDATES if p.exists()), GRAMMAR_ROOT_CANDIDATES[0])

# Comma-separated IDs to force-reimport even if they already exist in manifest.
REIMPORT_IDS = {
    i.strip()
    for i in os.getenv("GS_REIMPORT_IDS", "").split(",")
    if i.strip()
}


REAL_SLIDE_ENTRIES = [
    # Day 1
    {"id": "gs_w01_d01_l01", "day": 1, "title": "Day 1 Lesson 1 - Grammar Slides", "folder": "Week 1/Day 1/1. Day 1 Lesson 1", "anchor_id": "12645339"},
    {"id": "gs_w01_d01_l02", "day": 1, "title": "Day 1 Lesson 2 - Grammar Slides", "folder": "Week 1/Day 1/2. Day 1 Lesson 2", "anchor_id": "12645342"},
    {"id": "gs_w01_d01_l03", "day": 1, "title": "Day 1 Lesson 3 - Grammar Slides", "folder": "Week 1/Day 1/3. Day 1 Lesson 3", "anchor_id": "12645346"},
    {"id": "gs_w01_d01_l04", "day": 1, "title": "Day 1 Lesson 4 - Grammar Slides", "folder": "Week 1/Day 1/4. Day 1 Lesson 4", "anchor_id": "12645350"},
    # Day 2
    {"id": "gs_w01_d02_l01", "day": 2, "title": "Day 2 Lesson 1 - Grammar Slides", "folder": "Week 1/Day 2/1. Day 2 Lesson 1", "anchor_id": "12645358"},
    {"id": "gs_w01_d02_l02", "day": 2, "title": "Day 2 Lesson 2 - Grammar Slides", "folder": "Week 1/Day 2/2. Day 2 Lesson 2", "anchor_id": "12645362"},
    {"id": "gs_w01_d02_l03", "day": 2, "title": "Day 2 Lesson 3 - Grammar Slides", "folder": "Week 1/Day 2/3. Day 2 Lesson 3", "anchor_id": "12645367"},
    {"id": "gs_w01_d02_l04", "day": 2, "title": "Day 2 Lesson 4 - Grammar Slides", "folder": "Week 1/Day 2/4. Day 2 Lesson 4", "anchor_id": "12645371"},
    # Day 3
    {"id": "gs_w01_d03_l01", "day": 3, "title": "Day 3 Lesson 1 - Grammar Slides", "folder": "Week 1/Day 3/1. Day 3 Lesson 1", "anchor_id": "12645379"},
    {"id": "gs_w01_d03_l02", "day": 3, "title": "Day 3 Lesson 2 - Grammar Slides", "folder": "Week 1/Day 3/2. Day 3 Lesson 2", "anchor_id": "12645382"},
    {"id": "gs_w01_d03_l03_p1", "day": 3, "title": "Day 3 Lesson 3 - Grammar Slides Part 1", "folder": "Week 1/Day 3/3. Day 3 Lesson 3 - Part 1", "anchor_id": "12645386"},
    {"id": "gs_w01_d03_l03_p2", "day": 3, "title": "Day 3 Lesson 3 - Grammar Slides Part 2", "folder": "Week 1/Day 3/4. Day 3 Lesson 3 - Part 2", "anchor_id": "12645388"},
    {"id": "gs_w01_d03_l04", "day": 3, "title": "Day 3 Lesson 4 - Grammar Slides", "folder": "Week 1/Day 3/5. Day 3 Lesson 4", "anchor_id": "12645393"},
    # Day 4
    {"id": "gs_w01_d04_l01_p1", "day": 4, "title": "Day 4 Lesson 1 - Grammar Slides Part 1", "folder": "Week 1/Day 4/1. Day 4 Lesson 1 - Part 1", "anchor_id": "12645401"},
    {"id": "gs_w01_d04_l01_p2", "day": 4, "title": "Day 4 Lesson 1 - Grammar Slides Part 2", "folder": "Week 1/Day 4/2. Day 4 Lesson 1 - Part 2", "anchor_id": "12645403"},
    {"id": "gs_w01_d04_l02", "day": 4, "title": "Day 4 Lesson 2 - Grammar Slides", "folder": "Week 1/Day 4/3. Day 4 Lesson 2", "anchor_id": "12645408"},
    {"id": "gs_w01_d04_l03", "day": 4, "title": "Day 4 Lesson 3 - Grammar Slides", "folder": "Week 1/Day 4/4. Day 4 Lesson 3", "anchor_id": "12645412"},
    # Day 5
    {"id": "gs_w01_d05_l01", "day": 5, "title": "Day 5 Lesson 1 - Grammar Slides", "folder": "Week 1/Day 5/1. Day 5 Lesson 1", "anchor_id": "12645420"},
    {"id": "gs_w01_d05_l02", "day": 5, "title": "Day 5 Lesson 2 - Grammar Slides", "folder": "Week 1/Day 5/2. Day 5 Lesson 2", "anchor_id": "12645424"},
    {"id": "gs_w01_d05_l03", "day": 5, "title": "Day 5 Lesson 3 - Grammar Slides", "folder": "Week 1/Day 5/3. Day 5 Lesson 3", "anchor_id": "12645428"},
    {"id": "gs_w01_d05_l04", "day": 5, "title": "Day 5 Lesson 4 - Grammar Slides", "folder": "Week 1/Day 5/4. Day 5 Lesson 4", "anchor_id": "12645432"},
    # Day 6
    {"id": "gs_w02_d06_l01", "day": 6, "title": "Day 6 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 6/1. Day 6 Lesson 1", "anchor_id": "12645442"},
    {"id": "gs_w02_d06_l02", "day": 6, "title": "Day 6 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 6/2. Day 6 Lesson 2", "anchor_id": "12645447"},
    {"id": "gs_w02_d06_l03", "day": 6, "title": "Day 6 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 6/3. Day 6 Lesson 3", "anchor_id": "12645451"},
    # Day 7
    {"id": "gs_w02_d07_l01", "day": 7, "title": "Day 7 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 7/1. Day 7 Lesson 1", "anchor_id": "12645459"},
    {"id": "gs_w02_d07_l02_p1", "day": 7, "title": "Day 7 Lesson 2 - Grammar Slides Part 1", "folder": "Week 2/Day 7/2. Day 7 Lesson 2 - Part 1", "anchor_id": "12645464"},
    {"id": "gs_w02_d07_l02_p2", "day": 7, "title": "Day 7 Lesson 2 - Grammar Slides Part 2", "folder": "Week 2/Day 7/3. Day 7 Lesson 2 - Part 2", "anchor_id": "12645467"},
    {"id": "gs_w02_d07_l03", "day": 7, "title": "Day 7 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 7/4. Day 7 Lesson 3", "anchor_id": "12645471"},
    # Day 8
    {"id": "gs_w02_d08_l01_p1", "day": 8, "title": "Day 8 Lesson 1 - Grammar Slides Part 1", "folder": "Week 2/Day 8/1. Day 8 Lesson 1 - Part 1", "anchor_id": "12645481"},
    {"id": "gs_w02_d08_l01_p2", "day": 8, "title": "Day 8 Lesson 1 - Grammar Slides Part 2", "folder": "Week 2/Day 8/2. Day 8 Lesson 1 - Part 2", "anchor_id": "12645484"},
    {"id": "gs_w02_d08_l02", "day": 8, "title": "Day 8 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 8/3. Day 8 Lesson 2", "anchor_id": "12645485"},
    {"id": "gs_w02_d08_l03_p1", "day": 8, "title": "Day 8 Lesson 3 - Grammar Slides Part 1", "folder": "Week 2/Day 8/4. Day 8 Lesson 3 - Part 1", "anchor_id": "12645491"},
    {"id": "gs_w02_d08_l03_p2", "day": 8, "title": "Day 8 Lesson 3 - Grammar Slides Part 2", "folder": "Week 2/Day 8/5. Day 8 Lesson 3 - Part 2", "anchor_id": "12645493"},
    # Day 9
    {"id": "gs_w02_d09_l01", "day": 9, "title": "Day 9 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 9/1. Day 9 Lesson 1", "anchor_id": "12645503"},
    {"id": "gs_w02_d09_l02", "day": 9, "title": "Day 9 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 9/2. Day 9 Lesson 2", "anchor_id": "12645508"},
    {"id": "gs_w02_d09_l03", "day": 9, "title": "Day 9 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 9/3. Day 9 Lesson 3", "anchor_id": "12645512"},
    # Day 10
    {"id": "gs_w02_d10_l01", "day": 10, "title": "Day 10 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 10/1. Day 10 Lesson 1", "anchor_id": "12645521"},
    {"id": "gs_w02_d10_l02_p1", "day": 10, "title": "Day 10 Lesson 2 - Grammar Slides Part 1", "folder": "Week 2/Day 10/2. Day 10 Lesson 2 - Part 1", "anchor_id": "12645530"},
    {"id": "gs_w02_d10_l02_p2", "day": 10, "title": "Day 10 Lesson 2 - Grammar Slides Part 2", "folder": "Week 2/Day 10/3. Day 10 Lesson 2 - Part 2", "anchor_id": "12645532"},
    {"id": "gs_w02_d10_l03", "day": 10, "title": "Day 10 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 10/4. Day 10 Lesson 3", "anchor_id": "12645537"},
    {"id": "gs_w02_d10_l04", "day": 10, "title": "Day 10 Lesson 4 - Grammar Slides", "folder": "Week 2/Day 10/5. Day 10 Lesson 4", "anchor_id": "12645542"},
    # Day 11
    {"id": "gs_w02_d11_l01", "day": 11, "title": "Day 11 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 11/1. Day 11 Lesson 1", "anchor_id": "12645553"},
    {"id": "gs_w02_d11_l02", "day": 11, "title": "Day 11 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 11/2. Day 11 Lesson 2", "anchor_id": "12645558"},
    {"id": "gs_w02_d11_l03", "day": 11, "title": "Day 11 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 11/3. Day 11 Lesson 3", "anchor_id": "12645564"},
    {"id": "gs_w02_d11_l04", "day": 11, "title": "Day 11 Lesson 4 - Grammar Slides", "folder": "Week 2/Day 11/4. Day 11 Lesson 4", "anchor_id": "12645569"},
    # Day 12
    {"id": "gs_w02_d12_l01", "day": 12, "title": "Day 12 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 12/1. Day 12 Lesson 1", "anchor_id": "12645578"},
    {"id": "gs_w02_d12_l02", "day": 12, "title": "Day 12 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 12/2. Day 12 Lesson 2", "anchor_id": "12645582"},
    {"id": "gs_w02_d12_l03", "day": 12, "title": "Day 12 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 12/3. Day 12 Lesson 3", "anchor_id": "12645587"},
    {"id": "gs_w02_d12_l04", "day": 12, "title": "Day 12 Lesson 4 - Grammar Slides", "folder": "Week 2/Day 12/4. Day 12 Lesson 4", "anchor_id": "12645593"},
    # Day 13
    {"id": "gs_w02_d13_l01", "day": 13, "title": "Day 13 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 13/1. Day 13 Lesson 1", "anchor_id": "12645602"},
    {"id": "gs_w02_d13_l02", "day": 13, "title": "Day 13 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 13/2. Day 13 Lesson 2", "anchor_id": "12645607"},
    {"id": "gs_w02_d13_l03", "day": 13, "title": "Day 13 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 13/3. Day 13 Lesson 3", "anchor_id": "12645612"},
    # Day 14
    {"id": "gs_w02_d14_l01", "day": 14, "title": "Day 14 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 14/1. Day 14 Lesson 1", "anchor_id": "12645622"},
    {"id": "gs_w02_d14_l02", "day": 14, "title": "Day 14 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 14/2. Day 14 Lesson 2", "anchor_id": "12645626"},
    {"id": "gs_w02_d14_l03_p1", "day": 14, "title": "Day 14 Lesson 3 - Grammar Slides Part 1", "folder": "Week 2/Day 14/3. Day 14 Lesson 3 - Part 1", "anchor_id": "12645630"},
    {"id": "gs_w02_d14_l03_p2", "day": 14, "title": "Day 14 Lesson 3 - Grammar Slides Part 2", "folder": "Week 2/Day 14/4. Day 14 Lesson 3 - Part 2", "anchor_id": "12645632"},
    {"id": "gs_w02_d14_l04", "day": 14, "title": "Day 14 Lesson 4 - Grammar Slides", "folder": "Week 2/Day 14/5. Day 14 Lesson 4", "anchor_id": "12645638"},
    # Day 15
    {"id": "gs_w02_d15_l01", "day": 15, "title": "Day 15 Lesson 1 - Grammar Slides", "folder": "Week 2/Day 15/1. Day 15 Lesson 1", "anchor_id": "12645646"},
    {"id": "gs_w02_d15_l02", "day": 15, "title": "Day 15 Lesson 2 - Grammar Slides", "folder": "Week 2/Day 15/2. Day 15 Lesson 2", "anchor_id": "12645651"},
    {"id": "gs_w02_d15_l03", "day": 15, "title": "Day 15 Lesson 3 - Grammar Slides", "folder": "Week 2/Day 15/3. Day 15 Lesson 3", "anchor_id": "12645655"},
    # Day 16
    {"id": "gs_w03_d16_l01_p1", "day": 16, "title": "Day 16 Lesson 1 - Grammar Slides Part 1", "folder": "Week 4/Day 16/1. Day 16 Lesson 1 pt 1", "anchor_id": "13242740"},
    {"id": "gs_w03_d16_l01_p2", "day": 16, "title": "Day 16 Lesson 1 - Grammar Slides Part 2", "folder": "Week 4/Day 16/2. Day 16 Lesson 1 pt 2", "anchor_id": "13242740"},
    {"id": "gs_w03_d16_l02", "day": 16, "title": "Day 16 Lesson 2 - Grammar Slides", "folder": "Week 4/Day 16/3. Day 16 lesson 2", "anchor_id": "13242882"},
    # Day 17
    {"id": "gs_w03_d17_l01", "day": 17, "title": "Day 17 Lesson 1 - Grammar Slides", "folder": "Week 4/Day 17/1. Day 17 Lesson 1", "anchor_id": "13244720"},
    {"id": "gs_w03_d17_l02", "day": 17, "title": "Day 17 Lesson 2 - Grammar Slides", "folder": "Week 4/Day 17/2. Day 17 Lesson 2", "anchor_id": "13244877"},
    {"id": "gs_w03_d17_l03", "day": 17, "title": "Day 17 Lesson 3 - Grammar Slides", "folder": "Week 4/Day 17/3. Day 17 Lesson 3", "anchor_id": "13245130"},
    {"id": "gs_w03_d17_l04", "day": 17, "title": "Day 17 Lesson 4 - Grammar Slides", "folder": "Week 4/Day 17/4. Day 17 Lesson 4", "anchor_id": "13245190"},
    # Day 18
    {"id": "gs_w03_d18_l01", "day": 18, "title": "Day 18 Lesson 1 - Grammar Slides", "folder": "Week 4/Day 18/1. Day 18 Lesson 1", "anchor_id": "13245805"},
    {"id": "gs_w03_d18_l02", "day": 18, "title": "Day 18 Lesson 2 - Grammar Slides", "folder": "Week 4/Day 18/2. Day 18 Lesson 2", "anchor_id": "13245996"},
    # Day 19
    {"id": "gs_w03_d19_l01", "day": 19, "title": "Day 19 Lesson 1 - Grammar Slides", "folder": "Week 4/Day 19/1. Day 19 Lesson 1", "anchor_id": "13246171"},
    {"id": "gs_w03_d19_l02", "day": 19, "title": "Day 19 Lesson 2 - Grammar Slides", "folder": "Week 4/Day 19/2. Day 19 Lesson 2", "anchor_id": "13246211"},
    {"id": "gs_w03_d19_l03", "day": 19, "title": "Day 19 Lesson 3 - Grammar Slides", "folder": "Week 4/Day 19/3. Day 19 Lesson 3", "anchor_id": "13246439"},
    # Day 20
    {"id": "gs_w03_d20_l01", "day": 20, "title": "Day 20 Lesson 1 - Grammar Slides", "folder": "Week 4/Day 20/1. Day 20 Lesson 1", "anchor_id": "13246563"},
    {"id": "gs_w03_d20_l02", "day": 20, "title": "Day 20 Lesson 2 - Grammar Slides", "folder": "Week 4/Day 20/2. Day 20 Lesson 2", "anchor_id": "13246603"},
    # Day 21
    {"id": "gs_w04_d21_l01", "day": 21, "title": "Day 21 Lesson 1 - Grammar Slides", "folder": "Week 5/Day 21/1. Day 21 Lesson 1", "anchor_id": "13432933"},
    {"id": "gs_w04_d21_l02", "day": 21, "title": "Day 21 Lesson 2 - Grammar Slides", "folder": "Week 5/Day 21/2. Day 21 Lesson 2", "anchor_id": "13433238"},
    {"id": "gs_w04_d21_l03", "day": 21, "title": "Day 21 Lesson 3 - Grammar Slides", "folder": "Week 5/Day 21/3. Day 21 Lesson 3", "anchor_id": "13433315"},
    # Day 22
    {"id": "gs_w04_d22_l01", "day": 22, "title": "Day 22 Lesson 1 - Grammar Slides", "folder": "Week 5/Day 22/1. Day 22 Lesson 1", "anchor_id": "13433424"},
    {"id": "gs_w04_d22_l02", "day": 22, "title": "Day 22 Lesson 2 - Grammar Slides", "folder": "Week 5/Day 22/2. Day 22 Lesson 2", "anchor_id": "13433445"},
    # Day 23
    {"id": "gs_w04_d23_l01", "day": 23, "title": "Day 23 Lesson 1 - Grammar Slides", "folder": "Week 5/Day 23/1. Day 23 Lesson 1", "anchor_id": "13433601"},
    {"id": "gs_w04_d23_l02", "day": 23, "title": "Day 23 Lesson 2 - Grammar Slides", "folder": "Week 5/Day 23/2. Day 23 Lesson 2", "anchor_id": "13433784"},
    {"id": "gs_w04_d23_l03", "day": 23, "title": "Day 23 Lesson 3 - Grammar Slides", "folder": "Week 5/Day 23/3. Day 23 Lesson 3", "anchor_id": "13433806"},
    # Day 24
    {"id": "gs_w04_d24_l01", "day": 24, "title": "Day 24 Lesson 1 - Grammar Slides", "folder": "Week 5/Day 24/1. Day 24 Lesson 1", "anchor_id": "13433881"},
    {"id": "gs_w04_d24_l02", "day": 24, "title": "Day 24 Lesson 2 - Grammar Slides", "folder": "Week 5/Day 24/2. Lesson 24 Lesson 2", "anchor_id": "13433919"},
    {"id": "gs_w04_d24_l03", "day": 24, "title": "Day 24 Lesson 3 - Grammar Slides", "folder": "Week 5/Day 24/3. Day 24 Lesson 3", "anchor_id": "13433965"},
    # Day 25
    {"id": "gs_w04_d25_l01", "day": 25, "title": "Day 25 Lesson 1 - Grammar Slides", "folder": "Week 5/Day 25/1. Day 25 Lesson 1", "anchor_id": "13434207"},
    {"id": "gs_w04_d25_l02", "day": 25, "title": "Day 25 Lesson 2 - Grammar Slides", "folder": "Week 5/Day 25/2. Day 25 lesson 2", "anchor_id": "13434242"},
]

# Explicit per-lesson page-index to audio-index mapping for multi-audio lessons.
# This takes precedence over filename-based parsing for mapped pages.
PAGE_AUDIO_MAP_OVERRIDES: dict[str, dict[int, int]] = {
    "gs_w03_d17_l03": {0: 0, 1: 0, 2: 1},
    "gs_w03_d18_l01": {0: 0, 1: 0, 2: 1, 3: 1},
    "gs_w03_d18_l02": {0: 0, 1: 0, 2: 1, 3: 1},
    "gs_w04_d22_l01": {0: 0, 1: 0, 2: 1, 3: 1},
}


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name.strip())


def grammar_day_from_real_id(lesson_id: str) -> int | None:
    m = re.match(r"^gs_w\d+_d(\d+)_", lesson_id)
    if not m:
        return None
    return int(m.group(1))


def page_key(path: Path):
    match = re.search(r"page__([0-9]+)", path.name)
    if match:
        return int(match.group(1))
    return 99999


def extract_page_numbers(name: str) -> list[int]:
    return [int(n) for n in re.findall(r"page__([0-9]+)", name)]


def build_page_audio_map(
    lesson_id: str,
    image_pages: list[int],
    audio_files: list[Path],
) -> dict[int, int]:
    page_audio_map: dict[int, int] = {}

    # Fallback mapping for older lessons inferred from filenames.
    image_page_set = set(image_pages)
    page_number_to_audio_idx: dict[int, int] = {}
    for audio_idx, audio_src in enumerate(audio_files):
        nums = extract_page_numbers(audio_src.name)
        for n in nums:
            if n in image_page_set:
                page_number_to_audio_idx[n] = audio_idx
            elif (n - 1) in image_page_set:
                # Handles folders where audio names are 1-based but image pages are 0-based.
                page_number_to_audio_idx[n - 1] = audio_idx

    for idx, page_num in enumerate(image_pages):
        if page_num in page_number_to_audio_idx:
            page_audio_map[idx] = page_number_to_audio_idx[page_num]

    # Explicit override takes priority when configured for a lesson.
    override = PAGE_AUDIO_MAP_OVERRIDES.get(lesson_id)
    if override:
        for page_idx, audio_idx in override.items():
            page_i = int(page_idx)
            audio_i = int(audio_idx)
            if page_i < 0 or page_i >= len(image_pages):
                raise ValueError(
                    f"Invalid page index override {page_i} for lesson {lesson_id}; "
                    f"expected 0..{max(len(image_pages) - 1, 0)}"
                )
            if audio_i < 0 or audio_i >= len(audio_files):
                raise ValueError(
                    f"Invalid audio index override {audio_i} for lesson {lesson_id}; "
                    f"expected 0..{max(len(audio_files) - 1, 0)}"
                )
            page_audio_map[page_i] = audio_i

    return page_audio_map


def make_slide_html(
    lesson_id: str,
    title: str,
    image_files: list[str],
    audio_files: list[str],
    page_audio_map: dict[int, int] | None = None,
) -> str:
    viewer_id = f"viewer-{lesson_id}"
    lines = [
        '<div class="fr-view">',
        f"<h3>{title}</h3>",
        f'<div id="{viewer_id}" class="grammar-slide-viewer">',
    ]
    for idx, img in enumerate(image_files):
        display = "block" if idx == 0 else "none"
        lines.append(
            f'<img src="../../images/{img}" class="gs-page" data-page="{idx + 1}" style="display:{display}; max-width:100%; margin:0 auto;" />'
        )
    lines.append(
        '<div style="display:flex; gap:10px; align-items:center; justify-content:center; margin-top:12px;">'
    )
    lines.append('<button type="button" class="gs-prev">Prev</button>')
    lines.append('<span class="gs-counter">1 / {}</span>'.format(max(len(image_files), 1)))
    lines.append('<button type="button" class="gs-next">Next</button>')
    lines.append('</div>')
    lines.append('</div>')

    if audio_files:
        lines.append('<div style="margin-top:14px; text-align:center;">')

        if len(audio_files) == 1:
            lines.append(f'<audio controls preload="metadata" src="../audio/{audio_files[0]}"></audio>')
        else:
            total_pages = max(len(image_files), 1)
            page_to_audio = [0] * total_pages
            for i in range(total_pages):
                mapped = (page_audio_map or {}).get(i)
                if mapped is None:
                    mapped = (page_audio_map or {}).get(str(i), 0)
                page_to_audio[i] = int(mapped)

            for audio_idx, audio_name in enumerate(audio_files):
                pages = [i + 1 for i, mapped_idx in enumerate(page_to_audio) if mapped_idx == audio_idx]
                if pages:
                    if len(pages) == 1:
                        label = f"Slide {pages[0]}/{total_pages}"
                    else:
                        label = f"Slides {pages[0]}-{pages[-1]}/{total_pages}"
                else:
                    label = f"Audio {audio_idx + 1}"

                lines.append('<div style="margin:10px 0;">')
                lines.append(f'<div style="font-size:12px; color:#94a3b8; margin-bottom:4px;">{label}</div>')
                lines.append(f'<audio controls preload="metadata" src="../audio/{audio_name}"></audio>')
                lines.append('</div>')

        lines.append("</div>")

    lines.append("<script>")
    lines.append("(function(){")
    lines.append(f"  const root=document.getElementById('{viewer_id}');")
    lines.append("  if(!root){return;}")
    lines.append("  const pages=Array.from(root.querySelectorAll('.gs-page'));")
    lines.append("  if(!pages.length){return;}")
    lines.append("  const prev=root.querySelector('.gs-prev');")
    lines.append("  const next=root.querySelector('.gs-next');")
    lines.append("  const counter=root.querySelector('.gs-counter');")
    lines.append("  let idx=0;")
    lines.append("  function render(){")
    lines.append("    pages.forEach((p,i)=>{p.style.display = i===idx ? 'block' : 'none';});")
    lines.append("    counter.textContent = `${idx+1} / ${pages.length}`;")
    lines.append("    prev.disabled = idx===0;")
    lines.append("    next.disabled = idx===pages.length-1;")
    lines.append("  }")
    lines.append("  prev.addEventListener('click', ()=>{if(idx>0){idx-=1; render();}});")
    lines.append("  next.addEventListener('click', ()=>{if(idx<pages.length-1){idx+=1; render();}});")
    if audio_files and len(audio_files) == 1:
        lines.append("  const audio=root.querySelector('audio');")
        lines.append(f"  const audioFiles={json.dumps(audio_files, ensure_ascii=False)};")
        lines.append(f"  const pageToAudio={json.dumps(page_audio_map or {}, ensure_ascii=False)};")
        lines.append("  function updateAudio(){")
        lines.append("    if(!audio || !audioFiles.length){return;}")
        lines.append("    const key = String(idx);")
        lines.append("    const targetIdx = Object.prototype.hasOwnProperty.call(pageToAudio, key) ? pageToAudio[key] : 0;")
        lines.append("    const target = audioFiles[targetIdx] || audioFiles[0];")
        lines.append("    const expectedSrc = `../audio/${target}`;")
        lines.append("    if(!audio.getAttribute('src') || !audio.getAttribute('src').endsWith(target)){")
        lines.append("      audio.setAttribute('src', expectedSrc);")
        lines.append("      audio.load();")
        lines.append("    }")
        lines.append("  }")
        lines.append("  const _render = render;")
        lines.append("  render = function(){ _render(); updateAudio(); };")

    lines.append("  render();")
    lines.append("})();")
    lines.append("</script>")
    lines.append("</div>")
    return "".join(lines)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def save_manifest(manifest: dict):
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def get_day_context(lessons: list[dict], day: int) -> tuple[int, str, int]:
    for lesson in lessons:
        if lesson.get("day") == day and lesson.get("week", 0) > 0:
            return int(lesson["week"]), lesson.get("section", f"Week ? - Day {day}"), lesson.get("section_type", "day")
    raise ValueError(f"Unable to resolve week/section for day {day}")


def write_lesson_json(
    entry_id: str,
    title: str,
    week: int,
    day: int,
    section: str,
    html: str,
    image_files: list[str],
    audio_files: list[str],
    placeholder: bool,
):
    lesson_json = {
        "id": entry_id,
        "title": title,
        "primary_type": "reference",
        "section": section,
        "section_type": "day",
        "week": week,
        "day": day,
        "html": html,
        "videos": [],
        "downloads": ([{
            "type": "audio",
            "filename": fn,
            "title": "Lesson audio" if len(audio_files) == 1 else f"Lesson audio {idx + 1}",
            "local": True,
        } for idx, fn in enumerate(audio_files)] if audio_files else []),
        "images": ([{"local": fn} for fn in image_files] if image_files else []),
        "has_video": False,
        "has_images": bool(image_files),
        "has_downloads": bool(audio_files),
        "placeholder": placeholder,
    }
    (LESSONS_DIR / f"{entry_id}.json").write_text(
        json.dumps(lesson_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def import_real_slides(manifest: dict) -> tuple[list[dict], dict[str, list[dict]], dict[int, int]]:
    lessons = manifest["lessons"]
    existing_ids = {str(l["id"]) for l in lessons}
    created_manifest_items = []
    anchor_insertions: dict[str, list[dict]] = {}
    day_add_counts: dict[int, int] = {}

    GRAMMAR_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for entry in REAL_SLIDE_ENTRIES:
        if entry["id"] in existing_ids and entry["id"] not in REIMPORT_IDS:
            continue

        week, section, section_type = get_day_context(lessons, entry["day"])

        folder = GRAMMAR_ROOT / entry["folder"]
        if not folder.exists():
            raise FileNotFoundError(f"Missing grammar folder: {folder}")

        files = [p for p in folder.iterdir() if p.is_file() and p.name != ".DS_Store"]
        images = sorted([p for p in files if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}], key=page_key)
        audio = [p for p in files if p.suffix.lower() in {".wav", ".m4a", ".mp3"}]

        if not images:
            raise ValueError(f"No images found in {folder}")
        if not audio:
            raise ValueError(f"No audio file found in {folder}")

        # Prefer m4a over mp3 over wav, then pick by filename for deterministic imports.
        audio_priority = {".m4a": 0, ".mp3": 1, ".wav": 2}
        audio = sorted(audio, key=lambda p: (audio_priority.get(p.suffix.lower(), 9), p.name.lower()))
        if len(audio) > 1:
            print(f"Info: multiple audio files in {folder}; keeping all {len(audio)} files")

        copied_images = []
        image_pages = []
        for i, img in enumerate(images, start=1):
            img_name = f"{entry['id']}_p{i:02d}{img.suffix.lower()}"
            shutil.copy2(img, GRAMMAR_IMAGES_DIR / img_name)
            copied_images.append(img_name)
            image_pages.append(page_key(img))

        copied_audio = []
        for idx, audio_src in enumerate(audio, start=1):
            if len(audio) == 1:
                audio_name = f"{entry['id']}{audio_src.suffix.lower()}"
            else:
                audio_name = f"{entry['id']}_a{idx:02d}{audio_src.suffix.lower()}"
            shutil.copy2(audio_src, AUDIO_DIR / audio_name)
            copied_audio.append(audio_name)

        page_audio_map = build_page_audio_map(entry["id"], image_pages, audio)

        html = make_slide_html(entry["id"], entry["title"], copied_images, copied_audio, page_audio_map)
        write_lesson_json(
            entry_id=entry["id"],
            title=entry["title"],
            week=week,
            day=entry["day"],
            section=section,
            html=html,
            image_files=copied_images,
            audio_files=copied_audio,
            placeholder=False,
        )

        item = {
            "id": entry["id"],
            "title": entry["title"],
            "type": "reference",
            "section": section,
            "section_type": section_type,
            "week": week,
            "day": entry["day"],
        }
        created_manifest_items.append(item)
        anchor_insertions.setdefault(entry["anchor_id"], []).append(item)
        day_add_counts[entry["day"]] = day_add_counts.get(entry["day"], 0) + 1
        existing_ids.add(entry["id"])

    return created_manifest_items, anchor_insertions, day_add_counts


def import_placeholders(
    manifest: dict,
    existing_ids: set[str],
    days_with_real_slides: set[int],
) -> tuple[list[dict], dict[str, list[dict]], dict[int, int]]:
    lessons = manifest["lessons"]
    placeholders = []
    anchor_insertions: dict[str, list[dict]] = {}
    day_add_counts: dict[int, int] = {}

    all_days = sorted({int(l.get("day", 0)) for l in lessons if l.get("day", 0) > 0})
    for day in all_days:
        if day <= 5:
            continue
        if day in days_with_real_slides:
            continue

        placeholder_id = f"gs_placeholder_d{day:02d}"
        if placeholder_id in existing_ids:
            continue

        week, section, section_type = get_day_context(lessons, day)
        title = f"Day {day} - Grammar Slides (Placeholder)"
        html = (
            '<div class="fr-view">'
            f"<h3>{title}</h3>"
            "<p>Placeholder for local grammar slide assets. Replace this lesson when Day files are available.</p>"
            "</div>"
        )

        write_lesson_json(
            entry_id=placeholder_id,
            title=title,
            week=week,
            day=day,
            section=section,
            html=html,
            image_files=[],
            audio_files=[],
            placeholder=True,
        )

        item = {
            "id": placeholder_id,
            "title": title,
            "type": "reference",
            "section": section,
            "section_type": section_type,
            "week": week,
            "day": day,
        }

        # Insert after Day X Lesson 1 main video where possible; fallback before Grammar Homework.
        day_lessons = [l for l in lessons if int(l.get("day", 0)) == day]
        anchor_id = None
        for l in day_lessons:
            t = str(l.get("title", ""))
            if re.search(rf"^Day\s+{day}\s+Lesson\s+1\b.*\(\s*Video", t, flags=re.IGNORECASE):
                anchor_id = str(l["id"])
                break
        if anchor_id is None:
            for l in day_lessons:
                if "grammar homework" in str(l.get("title", "")).lower():
                    anchor_id = str(l["id"])
                    break
        if anchor_id is None and day_lessons:
            anchor_id = str(day_lessons[-1]["id"])
        if anchor_id is None:
            continue

        placeholders.append(item)
        anchor_insertions.setdefault(anchor_id, []).append(item)
        day_add_counts[day] = day_add_counts.get(day, 0) + 1
        existing_ids.add(placeholder_id)

    return placeholders, anchor_insertions, day_add_counts


def insert_after_anchors(lessons: list[dict], insertions: dict[str, list[dict]]) -> list[dict]:
    out = []
    for lesson in lessons:
        out.append(lesson)
        lid = str(lesson["id"])
        if lid in insertions:
            out.extend(insertions[lid])
    return out


def update_section_counts(manifest: dict, day_add_counts: dict[int, int]):
    for section in manifest.get("sections", []):
        day = int(section.get("day", 0))
        if day in day_add_counts:
            section["lesson_count"] = int(section.get("lesson_count", 0)) + day_add_counts[day]


def main():
    manifest = load_manifest()
    lessons = manifest["lessons"]

    removed_reimport_by_day: dict[int, int] = {}
    if REIMPORT_IDS:
        filtered = []
        for lesson in lessons:
            lid = str(lesson.get("id", ""))
            if lid in REIMPORT_IDS:
                day = int(lesson.get("day", 0))
                removed_reimport_by_day[day] = removed_reimport_by_day.get(day, 0) + 1
                continue
            filtered.append(lesson)
        lessons = filtered
        manifest["lessons"] = lessons

    existing_ids = {str(l["id"]) for l in lessons}

    _, real_insertions, real_counts = import_real_slides(manifest)
    days_with_real = set(real_counts.keys())

    for lesson in lessons:
        real_day = grammar_day_from_real_id(str(lesson.get("id", "")))
        if real_day is not None:
            days_with_real.add(real_day)

    for day in sorted(days_with_real):
        placeholder_lesson_json = LESSONS_DIR / f"gs_placeholder_d{day:02d}.json"
        if placeholder_lesson_json.exists():
            placeholder_lesson_json.unlink()

    # Replace placeholders with real entries for days that now have imported slide assets.
    removed_by_day: dict[int, int] = {}
    base_lessons = []
    for lesson in lessons:
        lesson_id = str(lesson.get("id", ""))
        day = int(lesson.get("day", 0))
        if lesson_id.startswith("gs_placeholder_d") and day in days_with_real:
            removed_by_day[day] = removed_by_day.get(day, 0) + 1
            placeholder_lesson_json = LESSONS_DIR / f"{lesson_id}.json"
            if placeholder_lesson_json.exists():
                placeholder_lesson_json.unlink()
            continue
        base_lessons.append(lesson)

    manifest["lessons"] = base_lessons
    placeholders, ph_insertions, ph_counts = import_placeholders(manifest, existing_ids, days_with_real)

    merged_insertions = {}
    for src in (real_insertions, ph_insertions):
        for k, v in src.items():
            merged_insertions.setdefault(k, []).extend(v)

    new_lessons = insert_after_anchors(base_lessons, merged_insertions)
    manifest["lessons"] = new_lessons

    merged_counts = dict(real_counts)
    for day, c in ph_counts.items():
        merged_counts[day] = merged_counts.get(day, 0) + c
    for day, c in removed_by_day.items():
        merged_counts[day] = merged_counts.get(day, 0) - c
    for day, c in removed_reimport_by_day.items():
        merged_counts[day] = merged_counts.get(day, 0) - c
    update_section_counts(manifest, merged_counts)
    manifest["total_lessons"] = int(manifest.get("total_lessons", len(base_lessons))) + sum(merged_counts.values())

    save_manifest(manifest)

    print(f"Inserted real grammar slide lessons: {sum(real_counts.values())}")
    print(f"Inserted placeholders: {len(placeholders)}")
    print(f"Manifest total lessons is now: {manifest['total_lessons']}")


if __name__ == "__main__":
    main()
