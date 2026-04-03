#!/usr/bin/env python3
"""
Akamonkai Japanese Course — Local Content Importer

Reads the local course export folder and generates:
  - content/manifest.json (ordered course structure)
  - content/lessons/{id}.json (normalized lesson data)
  - content/pdfs/ (local PDF copies)
  - content/import-report.json (stats and warnings)

Replaces the old Teachable scraper pipeline entirely.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path
from datetime import datetime, timezone

# === Paths ===
PROJECT_ROOT = Path(__file__).parent
CONTENT_DIR = PROJECT_ROOT / "content"
LESSONS_DIR = CONTENT_DIR / "lessons"
PDFS_DIR = CONTENT_DIR / "pdfs"
MANIFEST_PATH = CONTENT_DIR / "manifest.json"

# Default source — can be overridden via CLI
DEFAULT_SOURCE = Path.home() / "Documents" / "AI Apps" / "Akamonkai Japanese 12 Week Beginner Course - content"


# ─── Folder name parsing ─────────────────────────────────────

def parse_section_folder(name: str) -> dict:
    """Parse a top-level section folder name like '3. Week 1 - Day 1' or '33. Mid course review'."""
    m = re.match(r'^(\d+)\.\s*(.+)$', name.strip())
    if not m:
        return {"order": 999, "raw": name, "week": 0, "day": 0, "section_type": "unknown", "label": name}

    order = int(m.group(1))
    label = m.group(2).strip().rstrip('-').strip()

    week = 0
    day = 0
    section_type = "intro"

    wm = re.search(r'Week\s*(\d+)', label, re.I)
    dm = re.search(r'Day\s*(\d+)', label, re.I)
    if wm:
        week = int(wm.group(1))
    if dm:
        day = int(dm.group(1))

    if week > 0 and day > 0:
        section_type = "day"
    elif week > 0:
        section_type = "week"
    elif "mid course" in label.lower() or "review" in label.lower():
        section_type = "review"
    elif "next step" in label.lower():
        section_type = "outro"
    elif "welcome" in label.lower():
        section_type = "intro"
    elif "introduction" in label.lower() or "course intro" in label.lower():
        section_type = "intro"

    return {
        "order": order,
        "raw": label,
        "week": week,
        "day": day,
        "section_type": section_type,
        "label": label,
    }


def parse_item_folder(name: str) -> dict:
    """Parse a sub-folder name like '5.Day 1 Lesson 1 - Video -Introducing a new student-Text'."""
    m = re.match(r'^(\d+)\.?\s*(.*)$', name.strip())
    if not m:
        return {"order": 999, "raw_title": name, "folder_type_hint": ""}

    order = int(m.group(1))
    rest = m.group(2).strip()

    # Detect type hints from suffix
    folder_type_hint = ""
    if rest.endswith("Text"):
        folder_type_hint = "text"
        rest = rest[:-4].strip()
    elif rest.endswith("Video"):
        folder_type_hint = "video"
        rest = rest[:-5].strip()

    # Clean up title: remove trailing dashes, extra whitespace
    rest = rest.rstrip('-').strip()
    # Replace hyphens used as parens: -Introducing a new student- → (Introducing a new student)
    rest = re.sub(r'-([^-]+)-', r'(\1)', rest)

    return {
        "order": order,
        "raw_title": rest,
        "folder_type_hint": folder_type_hint,
    }


# ─── HTML processing ─────────────────────────────────────────

def sanitize_html(html: str) -> str:
    """Clean Froala editor artifacts from exported HTML while preserving content."""
    if not html:
        return ""

    # Remove contenteditable and draggable attributes
    html = re.sub(r'\s+contenteditable="[^"]*"', '', html)
    html = re.sub(r'\s+draggable="[^"]*"', '', html)

    # Remove fr-active and fr-draggable classes but keep other classes
    html = re.sub(r'\bfr-active\b', '', html)
    html = re.sub(r'\bfr-draggable\b', '', html)

    # Clean up double spaces in class attributes
    html = re.sub(r'class="([^"]*?)\s{2,}([^"]*?)"', r'class="\1 \2"', html)
    html = re.sub(r'class="\s+', 'class="', html)
    html = re.sub(r'\s+"', '"', html)

    # Remove data-stringify-* attributes (from Sheets copy-paste)
    html = re.sub(r'\s+data-stringify-[a-z-]+="[^"]*"', '', html)

    # Remove data-sheets-* attributes
    html = re.sub(r'\s+data-sheets-[a-z-]+="[^"]*"', '', html)

    return html.strip()


def classify_html(html: str) -> str:
    """Determine content type from HTML contents."""
    if not html:
        return "text"

    if 'videoproxy_embed' in html or '<iframe' in html:
        return "video"
    if '<img' in html:
        return "reference"
    return "text"


def extract_id_from_filename(filename: str) -> str:
    """Extract numeric lesson ID from HTML filename like '12645339-day-1-lesson-1-..html'."""
    m = re.match(r'^(\d+)-', filename)
    if m:
        return m.group(1)
    # Fallback: just the stem without extension
    return Path(filename).stem


def extract_downloads_from_html(html: str) -> list:
    """Extract downloadable links (PDFs, audio folders) from HTML content."""
    downloads = []

    # S3/Thinkific PDF links
    for m in re.finditer(r'<a[^>]*href="(https?://[^"]*\.pdf)"[^>]*>([^<]*)</a>', html, re.I):
        url = m.group(1)
        title = m.group(2).strip() or Path(url).name
        downloads.append({
            "type": "pdf",
            "url": url,
            "title": title,
            "local": False,
        })

    # Google Drive audio links
    for m in re.finditer(r'<a[^>]*href="(https?://drive\.google\.com/[^"]+)"[^>]*>([^<]*)</a>', html, re.I):
        url = m.group(1)
        title = m.group(2).strip() or "Audio files"
        downloads.append({
            "type": "audio_link",
            "url": url,
            "title": title,
            "local": False,
        })

    return downloads


def extract_video_info(html: str) -> list:
    """Extract video embed info from HTML iframes."""
    videos = []
    for m in re.finditer(r'<iframe[^>]*src="([^"]+)"[^>]*title="([^"]*)"[^>]*>', html, re.I):
        src = m.group(1)
        title = m.group(2).strip()
        videos.append({
            "src": src,
            "title": title,
        })
    # Also catch iframes where title comes before src
    for m in re.finditer(r'<iframe[^>]*title="([^"]*)"[^>]*src="([^"]+)"[^>]*>', html, re.I):
        src = m.group(2)
        title = m.group(1).strip()
        # Avoid duplicates
        if not any(v["src"] == src for v in videos):
            videos.append({
                "src": src,
                "title": title,
            })
    return videos


# ─── Main import logic ────────────────────────────────────────

def import_course(source_dir: Path) -> dict:
    """Import the full course from the local export folder."""
    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}")
        sys.exit(1)

    print(f"Importing from: {source_dir}")

    # Prepare output directories
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)

    # Collect all top-level section folders
    section_folders = []
    for entry in source_dir.iterdir():
        if entry.is_dir() and not entry.name.startswith('.'):
            section_folders.append(entry)

    # Sort by numeric prefix
    def section_sort_key(p):
        m = re.match(r'^(\d+)', p.name)
        return int(m.group(1)) if m else 999
    section_folders.sort(key=section_sort_key)

    print(f"  Found {len(section_folders)} sections")

    # Process each section
    all_lessons = []
    sections_meta = []
    stats = {
        "total_sections": len(section_folders),
        "total_items": 0,
        "html_items": 0,
        "pdf_items": 0,
        "mp4_items": 0,
        "skipped_empty": 0,
        "skipped_gaps": 0,
        "warnings": [],
    }

    for section_path in section_folders:
        section_info = parse_section_folder(section_path.name)
        section_lessons = []

        # Collect sub-item folders
        item_folders = []
        for item in section_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                item_folders.append(item)

        # Sort by numeric prefix
        def item_sort_key(p):
            m = re.match(r'^(\d+)', p.name)
            return int(m.group(1)) if m else 999
        item_folders.sort(key=item_sort_key)

        for item_path in item_folders:
            item_info = parse_item_folder(item_path.name)

            # Find the actual content file
            files = [f for f in item_path.iterdir() if f.is_file() and not f.name.startswith('.')]
            if not files:
                stats["skipped_empty"] += 1
                continue

            stats["total_items"] += 1

            # Determine file type
            html_files = [f for f in files if f.suffix.lower() == '.html']
            pdf_files = [f for f in files if f.suffix.lower() == '.pdf']
            mp4_files = [f for f in files if f.suffix.lower() == '.mp4']

            if html_files:
                stats["html_items"] += 1
                html_file = html_files[0]
                lesson_id = extract_id_from_filename(html_file.name)

                # Read and process HTML
                raw_html = html_file.read_text(encoding='utf-8', errors='replace')
                clean_html = sanitize_html(raw_html)
                content_type = classify_html(clean_html)
                downloads = extract_downloads_from_html(clean_html)
                videos = extract_video_info(clean_html)

                lesson = {
                    "id": lesson_id,
                    "title": item_info["raw_title"],
                    "primary_type": content_type,
                    "section": section_info["label"],
                    "section_type": section_info["section_type"],
                    "section_order": section_info["order"],
                    "item_order": item_info["order"],
                    "week": section_info["week"],
                    "day": section_info["day"],
                    "html": clean_html,
                    "videos": videos,
                    "downloads": downloads,
                    "has_video": len(videos) > 0,
                    "has_images": '<img' in clean_html,
                    "has_downloads": len(downloads) > 0,
                }

                section_lessons.append(lesson)
                all_lessons.append(lesson)

            elif pdf_files:
                stats["pdf_items"] += 1
                pdf_file = pdf_files[0]

                # Copy PDF to content/pdfs/
                dest = PDFS_DIR / pdf_file.name
                if not dest.exists():
                    shutil.copy2(pdf_file, dest)

                # Generate synthetic lesson entry wrapping the PDF
                # Use a deterministic ID from section_order + item_order
                synthetic_id = f"pdf_{section_info['order']}_{item_info['order']}"

                lesson = {
                    "id": synthetic_id,
                    "title": item_info["raw_title"],
                    "primary_type": "download",
                    "section": section_info["label"],
                    "section_type": section_info["section_type"],
                    "section_order": section_info["order"],
                    "item_order": item_info["order"],
                    "week": section_info["week"],
                    "day": section_info["day"],
                    "html": f'<p>Download: <a href="../pdfs/{pdf_file.name}" download="{pdf_file.name}">{item_info["raw_title"]}</a></p>',
                    "videos": [],
                    "downloads": [{
                        "type": "pdf",
                        "filename": pdf_file.name,
                        "title": item_info["raw_title"],
                        "local": True,
                    }],
                    "has_video": False,
                    "has_images": False,
                    "has_downloads": True,
                }

                section_lessons.append(lesson)
                all_lessons.append(lesson)

            elif mp4_files:
                stats["mp4_items"] += 1
                mp4_file = mp4_files[0]

                # Copy video to content/videos/ (just the one intro video)
                videos_dir = CONTENT_DIR / "videos"
                videos_dir.mkdir(exist_ok=True)
                dest = videos_dir / mp4_file.name
                if not dest.exists():
                    shutil.copy2(mp4_file, dest)

                synthetic_id = f"mp4_{section_info['order']}_{item_info['order']}"
                lesson = {
                    "id": synthetic_id,
                    "title": item_info["raw_title"],
                    "primary_type": "video",
                    "section": section_info["label"],
                    "section_type": section_info["section_type"],
                    "section_order": section_info["order"],
                    "item_order": item_info["order"],
                    "week": section_info["week"],
                    "day": section_info["day"],
                    "html": "",
                    "videos": [{"src": f"../videos/{mp4_file.name}", "title": item_info["raw_title"], "local": True}],
                    "downloads": [],
                    "has_video": True,
                    "has_images": False,
                    "has_downloads": False,
                }
                section_lessons.append(lesson)
                all_lessons.append(lesson)

            else:
                stats["skipped_gaps"] += 1
                stats["warnings"].append(f"Unknown file types in: {item_path}")

        sections_meta.append({
            "order": section_info["order"],
            "label": section_info["label"],
            "section_type": section_info["section_type"],
            "week": section_info["week"],
            "day": section_info["day"],
            "lesson_count": len(section_lessons),
        })

    # Write lesson JSON files
    print(f"  Writing {len(all_lessons)} lesson JSON files...")
    for lesson in all_lessons:
        lesson_path = LESSONS_DIR / f"{lesson['id']}.json"
        lesson_path.write_text(json.dumps(lesson, ensure_ascii=False, indent=2))

    # Build manifest
    manifest = {
        "course_name": "Akamonkai 12-Week Beginner Course",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source_dir),
        "total_lessons": len(all_lessons),
        "sections": sections_meta,
        "lessons": [
            {
                "id": l["id"],
                "title": l["title"],
                "type": l["primary_type"],
                "section": l["section"],
                "section_type": l["section_type"],
                "week": l["week"],
                "day": l["day"],
            }
            for l in all_lessons
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(f"  Wrote manifest: {MANIFEST_PATH}")

    # Write import report
    report = {
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source_dir),
        "stats": stats,
        "sections_summary": sections_meta,
    }
    report_path = CONTENT_DIR / "import-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"  Wrote report: {report_path}")

    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Import Akamonkai course from local export folder")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="Path to the local course export folder")
    parser.add_argument("--clean", action="store_true",
                        help="Remove existing content/lessons/ before import")
    args = parser.parse_args()

    if args.clean:
        if LESSONS_DIR.exists():
            print("Cleaning existing lessons...")
            shutil.rmtree(LESSONS_DIR)
        # Also clean old videos dir
        old_videos = CONTENT_DIR / "videos"
        if old_videos.exists():
            print("Cleaning old videos...")
            shutil.rmtree(old_videos)
        # Clean PDFs
        if PDFS_DIR.exists():
            print("Cleaning existing PDFs...")
            shutil.rmtree(PDFS_DIR)

    stats = import_course(args.source)

    print()
    print("=" * 50)
    print("  Import Complete")
    print("=" * 50)
    print(f"  Sections:     {stats['total_sections']}")
    print(f"  Total items:  {stats['total_items']}")
    print(f"  HTML lessons: {stats['html_items']}")
    print(f"  PDF items:    {stats['pdf_items']}")
    print(f"  MP4 items:    {stats['mp4_items']}")
    print(f"  Skipped empty: {stats['skipped_empty']}")
    if stats['warnings']:
        print(f"  Warnings:     {len(stats['warnings'])}")
        for w in stats['warnings'][:10]:
            print(f"    - {w}")


if __name__ == "__main__":
    main()
