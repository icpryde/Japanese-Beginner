#!/usr/bin/env python3
"""
Akamonkai Japanese Course — Static Site Generator (v2)

Reads content/manifest.json + content/lessons/*.json from the local
importer and generates a modern PWA study site in the site/ directory.
"""
import json
import re
import shutil
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timezone

from jinja2 import Environment, BaseLoader

# === Paths ===
PROJECT_ROOT = Path(__file__).parent
CONTENT_DIR = PROJECT_ROOT / "content"
LESSONS_DIR = CONTENT_DIR / "lessons"
MANIFEST_PATH = CONTENT_DIR / "manifest.json"
SITE_DIR = PROJECT_ROOT / "site"


# ─── Helpers ──────────────────────────────────────────────────

def build_course_structure(manifest: dict) -> dict:
    """Organize flat lesson list into a hierarchical structure."""
    structure = OrderedDict()
    structure["intro"] = {
        "title": "Course Introduction",
        "key": "intro",
        "week": 0,
        "lessons": [],
    }

    for lesson_meta in manifest["lessons"]:
        lid = lesson_meta["id"]
        title = lesson_meta["title"]
        ltype = lesson_meta["type"]
        week = lesson_meta.get("week", 0)
        day = lesson_meta.get("day", 0)
        section = lesson_meta.get("section", "")
        section_type = lesson_meta.get("section_type", "intro")

        # Load lesson JSON
        lesson_json = LESSONS_DIR / f"{lid}.json"
        if lesson_json.exists():
            with open(lesson_json) as f:
                data = json.load(f)
        else:
            data = {}

        lesson_entry = {
            "id": lid,
            "title": title,
            "type": ltype,
            "section": section,
            "section_type": section_type,
            "week": week,
            "day": day,
            "html": data.get("html", ""),
            "videos": data.get("videos", []),
            "downloads": data.get("downloads", []),
            "has_video": data.get("has_video", False),
            "has_images": data.get("has_images", False),
            "has_downloads": data.get("has_downloads", False),
        }

        if section_type in ("intro",) and week == 0 and day == 0:
            if "welcome" in section.lower():
                wk = "welcome"
                if wk not in structure:
                    structure[wk] = {
                        "title": "Welcome to the Course",
                        "key": wk,
                        "week": 0,
                        "lessons": [],
                    }
                structure[wk]["lessons"].append(lesson_entry)
            else:
                structure["intro"]["lessons"].append(lesson_entry)
        elif section_type == "review":
            rk = "review"
            if rk not in structure:
                structure[rk] = {
                    "title": "Mid-Course Review",
                    "key": rk,
                    "week": 0,
                    "lessons": [],
                }
            structure[rk]["lessons"].append(lesson_entry)
        elif section_type == "outro":
            ok_ = "outro"
            if ok_ not in structure:
                structure[ok_] = {
                    "title": "Next Steps",
                    "key": ok_,
                    "week": 0,
                    "lessons": [],
                }
            structure[ok_]["lessons"].append(lesson_entry)
        elif week > 0:
            week_key = f"week-{week}"
            if week_key not in structure:
                structure[week_key] = {
                    "title": f"Week {week}",
                    "key": week_key,
                    "week": week,
                    "days": OrderedDict(),
                    "lessons": [],
                }
            if day > 0:
                day_key = f"day-{day}"
                if day_key not in structure[week_key]["days"]:
                    structure[week_key]["days"][day_key] = {
                        "title": f"Day {day}",
                        "day": day,
                        "lessons": [],
                    }
                structure[week_key]["days"][day_key]["lessons"].append(lesson_entry)
            else:
                structure[week_key]["lessons"].append(lesson_entry)
        else:
            structure["intro"]["lessons"].append(lesson_entry)

    return structure


def collect_ordered_lessons(structure: dict) -> list:
    """Return flat list of all lessons in order with navigation metadata."""
    ordered = []
    for key, section in structure.items():
        if "days" not in section:
            for l in section["lessons"]:
                ordered.append(l)
        else:
            for l in section.get("lessons", []):
                ordered.append(l)
            for dk, day_data in section.get("days", {}).items():
                for l in day_data["lessons"]:
                    ordered.append(l)

    for i, l in enumerate(ordered):
        l["prev_id"] = ordered[i - 1]["id"] if i > 0 else None
        l["next_id"] = ordered[i + 1]["id"] if i < len(ordered) - 1 else None
        l["lesson_index"] = i

    return ordered


def collect_all_downloads(structure: dict) -> list:
    """Collect all downloadable items across the course."""
    downloads = []
    for key, section in structure.items():
        all_lessons = list(section.get("lessons", []))
        for dk, day_data in section.get("days", {}).items():
            all_lessons.extend(day_data["lessons"])
        for l in all_lessons:
            for dl in l.get("downloads", []):
                downloads.append({
                    **dl,
                    "lesson_title": l["title"],
                    "lesson_id": l["id"],
                    "week": l.get("week", 0),
                    "day": l.get("day", 0),
                })
    return downloads


def get_section_lesson_ids(section: dict) -> list:
    """Get all lesson IDs in a section."""
    ids = [l["id"] for l in section.get("lessons", [])]
    for dk, day_data in section.get("days", {}).items():
        ids.extend(l["id"] for l in day_data["lessons"])
    return ids


# ─── Templates ────────────────────────────────────────────────

LAYOUT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Akamonkai">
  <meta name="theme-color" content="#1a1a2e">
  <link rel="apple-touch-icon" href="{{ root }}icons/icon-192.png">
  <link rel="manifest" href="{{ root }}manifest.json">
  <title>{{ title }} — Akamonkai Japanese</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{{ root }}css/style.css">
</head>
<body>
  <div class="app">
    <nav class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <h2 class="logo">赤門会<span class="logo-sub">Akamonkai Japanese</span></h2>
        <button class="sidebar-close" id="sidebarClose" aria-label="Close sidebar">&times;</button>
      </div>
      <div class="sidebar-search">
        <input type="search" id="searchInput" placeholder="Search lessons..." aria-label="Search">
      </div>
      <div class="sidebar-nav" id="sidebarNav">
        <a href="{{ root }}index.html" class="nav-link nav-home">📊 Dashboard</a>
        <a href="{{ root }}worksheets.html" class="nav-link nav-worksheets">📄 Downloads</a>
        {% for key, section in structure.items() %}
          {% set section_ids = get_section_ids(section) %}
          {% if section.days is defined %}
            <div class="nav-section">
              <button class="nav-section-toggle" data-section="{{ key }}">
                <span class="nav-section-label">{{ section.title }}</span>
                <span class="nav-section-count" data-section-ids="{{ section_ids | join(',') }}">0/{{ section_ids | length }}</span>
              </button>
              <div class="nav-section-items" data-section-content="{{ key }}">
                {% for l in section.lessons %}
                <a href="{{ root }}lessons/{{ l.id }}.html" class="nav-link" data-lesson="{{ l.id }}">
                  <span class="nav-link-icon">{% if l.type == 'video' %}▶{% elif l.type == 'download' %}📄{% elif l.type == 'reference' %}📖{% else %}📝{% endif %}</span>
                  {{ l.title }}
                </a>
                {% endfor %}
                {% for dk, day in section.days.items() %}
                <div class="nav-day">
                  <button class="nav-day-toggle" data-day="{{ key }}-{{ dk }}">
                    <span>{{ day.title }}</span>
                    <span class="nav-day-count" data-day-ids="{{ day.lessons | map(attribute='id') | join(',') }}">0/{{ day.lessons | length }}</span>
                  </button>
                  <div class="nav-day-items" data-day-content="{{ key }}-{{ dk }}">
                    {% for l in day.lessons %}
                    <a href="{{ root }}lessons/{{ l.id }}.html" class="nav-link" data-lesson="{{ l.id }}">
                      <span class="nav-link-icon">{% if l.type == 'video' %}▶{% elif l.type == 'download' %}📄{% elif l.type == 'reference' %}📖{% else %}📝{% endif %}</span>
                      {{ l.title }}
                    </a>
                    {% endfor %}
                  </div>
                </div>
                {% endfor %}
              </div>
            </div>
          {% else %}
            <div class="nav-section">
              <button class="nav-section-toggle" data-section="{{ key }}">
                <span class="nav-section-label">{{ section.title }}</span>
                <span class="nav-section-count" data-section-ids="{{ section_ids | join(',') }}">0/{{ section_ids | length }}</span>
              </button>
              <div class="nav-section-items" data-section-content="{{ key }}">
                {% for l in section.lessons %}
                <a href="{{ root }}lessons/{{ l.id }}.html" class="nav-link" data-lesson="{{ l.id }}">
                  <span class="nav-link-icon">{% if l.type == 'video' %}▶{% elif l.type == 'download' %}📄{% elif l.type == 'reference' %}📖{% else %}📝{% endif %}</span>
                  {{ l.title }}
                </a>
                {% endfor %}
              </div>
            </div>
          {% endif %}
        {% endfor %}
      </div>
    </nav>
    <main class="main-content">
      <header class="topbar">
        <button class="hamburger" id="hamburger" aria-label="Open sidebar">☰</button>
        <div class="breadcrumb">{{ breadcrumb }}</div>
        <div class="topbar-actions">
          <span class="sync-status" id="syncStatus" data-state="idle">Ready</span>
          <button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">🌙</button>
        </div>
      </header>
      <div class="content-wrapper">
        {{ content }}
      </div>
    </main>
  </div>
  <script src="{{ root }}js/app.js"></script>
</body>
</html>"""

DASHBOARD_CONTENT = r"""
<div class="dashboard">
  <div class="dashboard-hero" id="resumeHero">
    <h1>赤門会 Akamonkai Japanese</h1>
    <p class="dashboard-subtitle">12 Week Beginner Course</p>
    <div class="progress-overview" id="progressOverview">
      <div class="progress-bar-container">
        <div class="progress-bar" id="progressBar" style="width: 0%"></div>
      </div>
      <p class="progress-text" id="progressText">Loading...</p>
    </div>
    <div class="resume-section" id="resumeSection" style="display:none">
      <a href="#" id="resumeLink" class="resume-btn">▶ Continue where you left off</a>
    </div>
  </div>

  <div class="bookmarks-section" id="bookmarksSection" style="display:none">
    <h2>⭐ Bookmarked Lessons</h2>
    <div class="bookmarks-list" id="bookmarksList"></div>
  </div>

  <h2 class="section-heading">Course Overview</h2>
  <div class="week-grid">
    {% for key, section in structure.items() %}
      {% set lesson_ids = get_section_ids(section) %}
      {% set lesson_count = lesson_ids | length %}
      {% if lesson_count > 0 %}
      <div class="week-card" data-card-ids="{{ lesson_ids | join(',') }}">
        <div class="week-card-header">
          <h3>{{ section.title }}</h3>
          <span class="week-count-badge">{{ lesson_count }}</span>
        </div>
        {% if section.days is defined %}
        <p class="week-days">
          {% set day_nums = [] %}
          {% for dk, day in section.days.items() %}
            {% if day_nums.append(day.day) %}{% endif %}
          {% endfor %}
          {% if day_nums %}Days {{ day_nums|min }}–{{ day_nums|max }}{% endif %}
        </p>
        {% endif %}
        <div class="week-progress">
          <div class="progress-bar-container small">
            <div class="progress-bar" data-card-progress="{{ lesson_ids | join(',') }}" style="width: 0%"></div>
          </div>
          <span class="week-progress-text" data-card-ptext="{{ lesson_ids | join(',') }}"></span>
        </div>
        {% set first_id = lesson_ids[0] if lesson_ids else '' %}
        <a href="lessons/{{ first_id }}.html" class="week-start-btn">Start →</a>
      </div>
      {% endif %}
    {% endfor %}
  </div>
</div>"""

LESSON_CONTENT = r"""
<article class="lesson" data-lesson-id="{{ lesson.id }}">
  <div class="lesson-header">
    <div class="lesson-badges">
      {% if lesson.week > 0 %}
      <span class="lesson-badge week-badge">Week {{ lesson.week }}</span>
      {% endif %}
      {% if lesson.day > 0 %}
      <span class="lesson-badge day-badge">Day {{ lesson.day }}</span>
      {% endif %}
      <span class="lesson-badge type-badge type-{{ lesson.type }}">{{ lesson.type | capitalize }}</span>
    </div>
    <h1>{{ lesson.title }}</h1>
    <div class="lesson-actions">
      <label class="complete-toggle" title="Mark as complete">
        <input type="checkbox" class="lesson-complete-check" data-lesson="{{ lesson.id }}">
        <span class="check-label">Complete</span>
      </label>
      <button class="bookmark-toggle" data-lesson="{{ lesson.id }}" title="Bookmark this lesson">☆</button>
    </div>
  </div>

  <div class="lesson-body">
    {{ lesson.html | safe }}
  </div>

  {% if lesson.downloads %}
  <div class="lesson-downloads">
    <h3>📥 Downloads & Resources</h3>
    {% for dl in lesson.downloads %}
      {% if dl.get('local') %}
      <a href="{% if dl.type in ['audio', 'audio_link'] %}../audio/{{ dl.filename }}{% elif dl.type == 'pdf' %}../pdfs/{{ dl.filename }}{% else %}../pdfs/{{ dl.filename }}{% endif %}" class="download-btn" download="{{ dl.filename }}">
        <span class="download-icon">📄</span>
        <span class="download-text">{{ dl.title or dl.filename }}</span>
        <span class="download-action">Download</span>
      </a>
      {% else %}
      <a href="{{ dl.url }}" class="download-btn" target="_blank" rel="noopener noreferrer">
        <span class="download-icon">{% if dl.type == 'pdf' %}📄{% elif dl.type == 'audio_link' %}🎵{% else %}🔗{% endif %}</span>
        <span class="download-text">{{ dl.title }}</span>
        <span class="download-action">{% if dl.type == 'audio_link' %}Listen{% else %}Open{% endif %}</span>
      </a>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  <div class="lesson-notes">
    <h3>📝 My Notes</h3>
    <textarea class="notes-textarea" data-lesson="{{ lesson.id }}" placeholder="Type your notes for this lesson here..."></textarea>
    <p class="notes-saved-msg" id="notesSaved" style="display:none">Saved ✓</p>
  </div>

  <div class="lesson-nav">
    {% if lesson.prev_id %}
    <a href="{{ lesson.prev_id }}.html" class="lesson-nav-btn prev" id="prevLesson">← Previous</a>
    {% else %}
    <span class="lesson-nav-btn prev disabled">← Previous</span>
    {% endif %}
    <span class="lesson-nav-counter">{{ lesson.lesson_index + 1 }} / {{ total_lessons }}</span>
    {% if lesson.next_id %}
    <a href="{{ lesson.next_id }}.html" class="lesson-nav-btn next" id="nextLesson">Next →</a>
    {% else %}
    <span class="lesson-nav-btn next disabled">Next →</span>
    {% endif %}
  </div>
</article>"""

WORKSHEETS_CONTENT = r"""
<div class="worksheets-hub">
  <h1>📄 Downloads & Resources</h1>
  <p class="worksheets-intro">All downloadable PDFs, worksheets, and resource links from the course.</p>

  {% if downloads %}
  {% set ns = namespace(current_week=-1) %}
  {% for dl in downloads %}
    {% if dl.week != ns.current_week %}
      {% if ns.current_week >= 0 %}</div>{% endif %}
      {% set ns.current_week = dl.week %}
      <h2 class="worksheet-week-header">{% if dl.week == 0 %}General{% else %}Week {{ dl.week }}{% endif %}</h2>
      <div class="worksheet-grid">
    {% endif %}
    <div class="worksheet-card">
      <div class="worksheet-info">
        <h4>{{ dl.title or dl.get('filename', 'Download') }}</h4>
        <p class="worksheet-lesson">From: {{ dl.lesson_title }}{% if dl.day %} · Day {{ dl.day }}{% endif %}</p>
      </div>
      {% if dl.get('local') %}
      <a href="{% if dl.type in ['audio', 'audio_link'] %}audio/{{ dl.filename }}{% elif dl.type == 'pdf' %}pdfs/{{ dl.filename }}{% else %}pdfs/{{ dl.filename }}{% endif %}" class="download-btn-sm" download="{{ dl.filename }}">Download</a>
      {% else %}
      <a href="{{ dl.url }}" class="download-btn-sm" target="_blank" rel="noopener noreferrer">
        {% if dl.type == 'audio_link' %}Listen{% else %}Open{% endif %}
      </a>
      {% endif %}
    </div>
  {% endfor %}
  {% if downloads %}</div>{% endif %}
  {% else %}
  <p class="no-worksheets">No downloads found.</p>
  {% endif %}
</div>"""


# ─── Generator ────────────────────────────────────────────────

def generate_site():
    print("Building site...")

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    structure = build_course_structure(manifest)
    ordered_lessons = collect_ordered_lessons(structure)
    downloads = collect_all_downloads(structure)
    total_lessons = len(ordered_lessons)

    print(f"  {total_lessons} lessons, {len(downloads)} downloads")

    env = Environment(loader=BaseLoader())
    env.globals["get_section_ids"] = get_section_lesson_ids

    SITE_DIR.mkdir(parents=True, exist_ok=True)
    lessons_out = SITE_DIR / "lessons"
    lessons_out.mkdir(exist_ok=True)

    # Copy static assets
    print("  Copying static assets...")
    for subdir in ["css", "js", "icons"]:
        src = PROJECT_ROOT / "site_src" / subdir
        dst = SITE_DIR / subdir
        if src.exists():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)

    # Copy local PDFs
    pdfs_src = CONTENT_DIR / "pdfs"
    pdfs_dst = SITE_DIR / "pdfs"
    if pdfs_src.exists() and any(pdfs_src.iterdir()):
        pdfs_dst.mkdir(exist_ok=True)
        for f in pdfs_src.iterdir():
            if f.is_file():
                shutil.copy2(f, pdfs_dst / f.name)

    # Copy local videos
    videos_src = CONTENT_DIR / "videos"
    videos_dst = SITE_DIR / "videos"
    if videos_src.exists() and any(videos_src.iterdir()):
        videos_dst.mkdir(exist_ok=True)
        for f in videos_src.iterdir():
            if f.is_file():
                shutil.copy2(f, videos_dst / f.name)

    # Copy local images
    images_src = CONTENT_DIR / "images"
    images_dst = SITE_DIR / "images"
    if images_src.exists() and any(images_src.iterdir()):
      images_dst.mkdir(exist_ok=True)
      for f in images_src.iterdir():
        if f.is_file():
          shutil.copy2(f, images_dst / f.name)

    # Copy local audio
    audio_src = CONTENT_DIR / "audio"
    audio_dst = SITE_DIR / "audio"
    if audio_src.exists() and any(audio_src.iterdir()):
      audio_dst.mkdir(exist_ok=True)
      for f in audio_src.iterdir():
        if f.is_file():
          shutil.copy2(f, audio_dst / f.name)

    build_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    # PWA files
    for pwa_file in ["manifest.json", "sw.js"]:
        src = PROJECT_ROOT / "site_src" / pwa_file
        if not src.exists():
            continue
        dst = SITE_DIR / pwa_file
        if pwa_file == "sw.js":
            sw_content = src.read_text(encoding="utf-8")
            sw_content = sw_content.replace("__BUILD_ID__", build_id)
            dst.write_text(sw_content, encoding="utf-8")
        else:
            shutil.copy2(src, dst)

    # lesson-data.json for JS
    lesson_data = [
        {"id": l["id"], "title": l["title"], "week": l["week"],
         "day": l["day"], "type": l["type"], "section": l.get("section", "")}
        for l in ordered_lessons
    ]
    (SITE_DIR / "lesson-data.json").write_text(json.dumps(lesson_data, ensure_ascii=False))

    layout_tpl = env.from_string(LAYOUT_TEMPLATE)

    # Dashboard
    print("  Generating dashboard...")
    dashboard_tpl = env.from_string(DASHBOARD_CONTENT)
    dashboard_html = dashboard_tpl.render(structure=structure, total_lessons=total_lessons)
    page_html = layout_tpl.render(
        title="Dashboard", root="", breadcrumb="Dashboard",
        content=dashboard_html, structure=structure,
    )
    (SITE_DIR / "index.html").write_text(page_html)

    # Downloads page
    print("  Generating downloads page...")
    ws_tpl = env.from_string(WORKSHEETS_CONTENT)
    ws_html = ws_tpl.render(downloads=downloads)
    page_html = layout_tpl.render(
        title="Downloads", root="",
        breadcrumb='<a href="index.html">Dashboard</a> → Downloads',
        content=ws_html, structure=structure,
    )
    (SITE_DIR / "worksheets.html").write_text(page_html)

    # Lesson pages
    print("  Generating lesson pages...")
    lesson_tpl = env.from_string(LESSON_CONTENT)
    for i, lesson in enumerate(ordered_lessons):
        parts = ['<a href="../index.html">Dashboard</a>']
        if lesson["week"] > 0:
            parts.append(f'Week {lesson["week"]}')
        if lesson["day"] > 0:
            parts.append(f'Day {lesson["day"]}')
        parts.append(lesson["title"][:50])
        breadcrumb = " → ".join(parts)

        lesson_html = lesson_tpl.render(lesson=lesson, total_lessons=total_lessons)
        page_html = layout_tpl.render(
            title=lesson["title"], root="../", breadcrumb=breadcrumb,
            content=lesson_html, structure=structure,
        )
        (lessons_out / f"{lesson['id']}.html").write_text(page_html)
        if (i + 1) % 200 == 0:
            print(f"    {i + 1}/{total_lessons}")

    print(f"  All {total_lessons} lesson pages generated")
    print(f"Site built at: {SITE_DIR}/")
    print("Done!")


if __name__ == "__main__":
    generate_site()
