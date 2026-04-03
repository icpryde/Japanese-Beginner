#!/usr/bin/env python3
import json
import re
import shutil
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent
CONTENT_DIR = PROJECT_ROOT / "content"
LESSONS_DIR = CONTENT_DIR / "lessons"
MANIFEST_PATH = CONTENT_DIR / "manifest.json"
IMAGES_DIR = CONTENT_DIR / "images"
AUDIO_DIR = CONTENT_DIR / "audio"

GRAMMAR_ROOT = Path("/Users/kurisu/Documents/AI Apps/Grammar Slides")


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
]


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", name.strip())


def page_key(path: Path):
    match = re.search(r"page__([0-9]+)", path.name)
    if match:
        return int(match.group(1))
    return 99999


def make_slide_html(lesson_id: str, title: str, image_files: list[str], audio_file: str | None) -> str:
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

    if audio_file:
        lines.append('<div style="margin-top:14px; text-align:center;">')
        lines.append(f'<audio controls preload="metadata" src="../../audio/{audio_file}"></audio>')
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


def write_lesson_json(entry_id: str, title: str, week: int, day: int, section: str, html: str,
                      image_files: list[str], audio_file: str | None, placeholder: bool):
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
            "filename": audio_file,
            "title": "Lesson audio",
            "local": True,
        }] if audio_file else []),
        "images": ([{"local": fn} for fn in image_files] if image_files else []),
        "has_video": False,
        "has_images": bool(image_files),
        "has_downloads": bool(audio_file),
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

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    for entry in REAL_SLIDE_ENTRIES:
        if entry["id"] in existing_ids:
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
        if len(audio) != 1:
            raise ValueError(f"Expected exactly one audio file in {folder}, found {len(audio)}")

        copied_images = []
        for i, img in enumerate(images, start=1):
            img_name = f"{entry['id']}_p{i:02d}{img.suffix.lower()}"
            shutil.copy2(img, IMAGES_DIR / img_name)
            copied_images.append(img_name)

        audio_src = audio[0]
        audio_name = f"{entry['id']}{audio_src.suffix.lower()}"
        shutil.copy2(audio_src, AUDIO_DIR / audio_name)

        html = make_slide_html(entry["id"], entry["title"], copied_images, audio_name)
        write_lesson_json(
            entry_id=entry["id"],
            title=entry["title"],
            week=week,
            day=entry["day"],
            section=section,
            html=html,
            image_files=copied_images,
            audio_file=audio_name,
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


def import_placeholders(manifest: dict, existing_ids: set[str]) -> tuple[list[dict], dict[str, list[dict]], dict[int, int]]:
    lessons = manifest["lessons"]
    placeholders = []
    anchor_insertions: dict[str, list[dict]] = {}
    day_add_counts: dict[int, int] = {}

    all_days = sorted({int(l.get("day", 0)) for l in lessons if l.get("day", 0) > 0})
    for day in all_days:
        if day <= 5:
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
            audio_file=None,
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
    existing_ids = {str(l["id"]) for l in lessons}

    _, real_insertions, real_counts = import_real_slides(manifest)
    placeholders, ph_insertions, ph_counts = import_placeholders(manifest, existing_ids)

    merged_insertions = {}
    for src in (real_insertions, ph_insertions):
        for k, v in src.items():
            merged_insertions.setdefault(k, []).extend(v)

    new_lessons = insert_after_anchors(lessons, merged_insertions)
    manifest["lessons"] = new_lessons

    merged_counts = dict(real_counts)
    for day, c in ph_counts.items():
        merged_counts[day] = merged_counts.get(day, 0) + c
    update_section_counts(manifest, merged_counts)
    manifest["total_lessons"] = int(manifest.get("total_lessons", len(lessons))) + sum(merged_counts.values())

    save_manifest(manifest)

    print(f"Inserted real grammar slide lessons: {sum(real_counts.values())}")
    print(f"Inserted placeholders: {len(placeholders)}")
    print(f"Manifest total lessons is now: {manifest['total_lessons']}")


if __name__ == "__main__":
    main()
