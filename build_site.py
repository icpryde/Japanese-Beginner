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

def normalize_embedded_asset_paths(html: str) -> str:
  """Fix over-deep relative media paths inside lesson HTML snippets."""
  if not html:
    return html

  return re.sub(
    r'(["\'(])\.\./\.\./(images|audio|videos|pdfs|icons|css|js)/',
    r'\1../\2/',
    html,
  )

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
          "html": normalize_embedded_asset_paths(data.get("html", "")),
            "videos": data.get("videos", []),
            "downloads": [
                {**dl, "title": clean_download_title(dl, title)}
                for dl in data.get("downloads", [])
            ],
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


VAGUE_TITLES = {"here", "click here", "download here", "download", "link"}

def clean_download_title(dl: dict, lesson_title: str) -> str:
    """Return a readable title for a download, replacing vague labels."""
    raw = str(dl.get("title", "")).strip()
    cleaned = raw.rstrip(".,;:!? ")
    if cleaned and cleaned.lower() not in VAGUE_TITLES:
        return raw
    filename = str(dl.get("filename", ""))
    stem = Path(filename).stem if filename else ""
    if stem:
        text = re.sub(r"[_-]+", " ", stem)
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            return text
    return f"{lesson_title} PDF"


def collect_all_downloads(structure: dict) -> list:
  """Collect PDF downloads for the worksheets hub."""

  def is_pdf_item(dl: dict) -> bool:
    filename = str(dl.get("filename", "")).lower()
    url = str(dl.get("url", "")).lower()
    dl_type = str(dl.get("type", "")).lower()
    return dl_type == "pdf" or filename.endswith(".pdf") or ".pdf" in url

  downloads = []
  for key, section in structure.items():
    all_lessons = list(section.get("lessons", []))
    for dk, day_data in section.get("days", {}).items():
      all_lessons.extend(day_data["lessons"])
    for l in all_lessons:
      for dl in l.get("downloads", []):
        if not is_pdf_item(dl):
          continue
        downloads.append({
          **dl,
          "display_title": dl.get("title", "PDF"),
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

WEEKLY_TEST_TEMPLATE = r"""
<div class="weekly-test" data-test-id="{{ test_id }}">
  <!-- Test header -->
  <div class="test-header">
    <h1>📝 {{ test_title }}</h1>
    <p class="test-subtitle">{{ test_subtitle }}</p>
    <div class="test-meta-badges">
      <span class="test-meta-badge">Multiple Choice</span>
      <span class="test-meta-badge">True / False</span>
      <span class="test-meta-badge">Fill in the Particle</span>
      <span class="test-meta-badge">Reading Match</span>
    </div>
  </div>

  <!-- Previous attempt banner -->
  <div id="quizPreviousBanner" class="quiz-previous-banner"></div>

  <!-- Sticky progress bar -->
  <div class="test-progress-sticky" id="testProgressSticky">
    <div class="test-progress-inner">
      <div class="test-progress-track">
        <div id="quizProgressFill" class="test-progress-fill"></div>
      </div>
      <div class="test-progress-stats">
        <span id="quizProgressText">Question 1 of 35</span>
      </div>
    </div>
  </div>

  <!-- Questions container (one visible at a time) -->
  <div id="quizContainer">
  {{ questions_html }}
  </div>

  <!-- Per-question navigation -->
  <div class="test-nav" id="testNav">
    <button id="quizBackBtn" class="test-nav-back" disabled>‹ Back</button>
    <button id="quizSubmitBtn" class="test-nav-submit" disabled>Submit Answer</button>
  </div>

  <!-- Results panel (hidden until all done) -->
  <div id="quizResults" class="test-results"></div>
</div>
"""

LAYOUT_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black">
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
    {% if lesson.html %}
    {{ lesson.html | safe }}
    {% else %}
    <div class="course-guide">
      <h2>📖 How to Navigate This Course</h2>
      <p>Welcome to the Akamonkai Japanese Beginner course. Here's how to get the most out of this study app:</p>
      <h3>🧭 Navigation</h3>
      <ul>
        <li><strong>Sidebar</strong> — Browse all weeks, days, and lessons. Tap any lesson to jump straight to it.</li>
        <li><strong>← Previous / Next →</strong> — Use the buttons at the bottom of each lesson to move through the course in order.</li>
        <li><strong>Search</strong> — Use the search box at the top of the sidebar to quickly find any topic or lesson by name.</li>
      </ul>
      <h3>📝 Study Features</h3>
      <ul>
        <li><strong>✅ Complete</strong> — Tick the checkbox on each lesson to track your progress. The sidebar shows your completion count per week.</li>
        <li><strong>☆ Bookmark</strong> — Star lessons you want to revisit later.</li>
        <li><strong>My Notes</strong> — Each lesson has a notes area at the bottom. Your notes save automatically to your device.</li>
        <li><strong>🎧 Audio</strong> — Many lessons include audio. Use the built-in player to listen along with the slides.</li>
      </ul>
      <h3>📄 Downloads</h3>
      <ul>
        <li>Visit the <strong>Downloads</strong> page (in the sidebar) for all PDF worksheets, organised by week.</li>
      </ul>
      <h3>📱 Offline Use</h3>
      <ul>
        <li>This is a <strong>Progressive Web App</strong> — after your first visit, all lessons and resources are cached for offline use on your device.</li>
        <li>On iPad, tap <strong>Share → Add to Home Screen</strong> for a full-screen app experience.</li>
      </ul>
    </div>
    {% endif %}
  </div>

  {% if lesson.downloads %}
  <div class="lesson-downloads">
    <h3>📥 Downloads & Resources</h3>
    {% for dl in lesson.downloads %}
      {% if dl.type in ['audio', 'audio_link'] %}
      {# Audio files are already playable inline — skip download button #}
      {% elif dl.get('local') %}
      <a href="{% if dl.type == 'pdf' %}../pdfs/{{ dl.filename }}{% else %}../pdfs/{{ dl.filename }}{% endif %}" class="download-btn" download="{{ dl.filename }}">
        <span class="download-icon">📄</span>
        <span class="download-text">{{ dl.title or dl.filename }}</span>
        <span class="download-action">Download</span>
      </a>
      {% else %}
      <a href="{{ dl.url }}" class="download-btn" target="_blank" rel="noopener noreferrer">
        <span class="download-icon">{% if dl.type == 'pdf' %}📄{% else %}🔗{% endif %}</span>
        <span class="download-text">{{ dl.title }}</span>
        <span class="download-action">Open</span>
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
  <h1>📄 PDF Worksheets</h1>
  <p class="worksheets-intro">Quick access to downloadable PDF worksheets and answer sheets.</p>

  {% if downloads %}
  {% for week_group in downloads | groupby('week') %}
  <details class="worksheet-week-section" {% if loop.first %}open{% endif %}>
    <summary class="worksheet-week-header">
      <span>{% if week_group.grouper == 0 %}General{% else %}Week {{ week_group.grouper }}{% endif %}</span>
      <span class="worksheet-week-count">{{ week_group.list | length }}</span>
    </summary>
    <div class="worksheet-grid">
      {% for dl in week_group.list %}
      <div class="worksheet-card">
        <div class="worksheet-info">
          <h4>{{ dl.display_title }}</h4>
          <p class="worksheet-lesson">From: {{ dl.lesson_title }}{% if dl.day %} · Day {{ dl.day }}{% endif %}</p>
        </div>
        {% if dl.get('local') %}
        <a href="pdfs/{{ dl.filename }}" class="download-btn-sm" download="{{ dl.filename }}">Download</a>
        {% else %}
        <a href="{{ dl.url }}" class="download-btn-sm" target="_blank" rel="noopener noreferrer">Open</a>
        {% endif %}
      </div>
      {% endfor %}
    </div>
  </details>
  {% endfor %}
  {% else %}
  <p class="no-worksheets">No downloads found.</p>
  {% endif %}
</div>"""


# ─── Generator ────────────────────────────────────────────────

def get_week1_test_questions():
    """Return the 35 quiz question HTML for the Week 1 test."""
    return '''
<!-- ════════ DAY 1: Particles は/も/か, Numbers, Hiragana あ-こ ════════ -->

<div class="quiz-question" data-topic="Particles" data-explanation="は (wa) marks the topic of the sentence." data-qnum="1">
  <div class="q-number">Q1</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">わたし ＿ がくせいです。(I am a student.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">は</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="false">に</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="も (mo) means 'also' or 'too' — it replaces は when indicating something is the same." data-qnum="2">
  <div class="q-number">Q2</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does the particle も mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">but</button>
    <button class="q-option" data-correct="true">also / too</button>
    <button class="q-option" data-correct="false">and</button>
    <button class="q-option" data-correct="false">or</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="か (ka) at the end of a sentence turns it into a question." data-qnum="3">
  <div class="q-number">Q3</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: Adding か at the end of a sentence makes it a question.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="か = ka, き = ki, く = ku, け = ke, こ = ko" data-qnum="4">
  <div class="q-number">Q4</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for く?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ka</button>
    <button class="q-option" data-correct="false">ki</button>
    <button class="q-option" data-correct="true">ku</button>
    <button class="q-option" data-correct="false">ke</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Numbers &amp; Counting" data-explanation="じゅう (juu) = 10. Numbers combine: にじゅう = 20, さんじゅう = 30, etc." data-qnum="5">
  <div class="q-number">Q5</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What number is さんじゅうご (sanjuugo)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">25</button>
    <button class="q-option" data-correct="true">35</button>
    <button class="q-option" data-correct="false">53</button>
    <button class="q-option" data-correct="false">30</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Vocabulary" data-explanation="せんせい (sensei) means teacher/professor. がくせい (gakusei) means student." data-qnum="6">
  <div class="q-number">Q6</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does せんせい (sensei) mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Student</button>
    <button class="q-option" data-correct="true">Teacher</button>
    <button class="q-option" data-correct="false">Friend</button>
    <button class="q-option" data-correct="false">Parent</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="あ = a, い = i, う = u, え = e, お = o — the first five hiragana." data-qnum="7">
  <div class="q-number">Q7</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">Which hiragana represents the sound "e"?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">あ</button>
    <button class="q-option" data-correct="false">い</button>
    <button class="q-option" data-correct="false">う</button>
    <button class="q-option" data-correct="true">え</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 2: この/その/あの, なん/だれ, の (possession), Hiragana さ-と ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="この (kono) = this (near speaker), その (sono) = that (near listener), あの (ano) = that over there." data-qnum="8">
  <div class="q-number">Q8</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does この (kono) mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">this (near me)</button>
    <button class="q-option" data-correct="false">that (near you)</button>
    <button class="q-option" data-correct="false">that over there</button>
    <button class="q-option" data-correct="false">which</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="だれ (dare) = who. なん (nan) = what." data-qnum="9">
  <div class="q-number">Q9</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you say "who" in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">なに</button>
    <button class="q-option" data-correct="false">どこ</button>
    <button class="q-option" data-correct="true">だれ</button>
    <button class="q-option" data-correct="false">いくら</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="の (no) between two nouns shows possession: わたしのほん = my book." data-qnum="10">
  <div class="q-number">Q10</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">わたし ＿ ほん (my book)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="true">の</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">も</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="その (sono) refers to something near the listener — 'that (near you)'." data-qnum="11">
  <div class="q-number">Q11</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">＿ かばんは だれのですか。(Whose bag is that [near you]?)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">この</button>
    <button class="q-option" data-correct="true">その</button>
    <button class="q-option" data-correct="false">あの</button>
    <button class="q-option" data-correct="false">どの</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="さ = sa, し = shi, す = su, せ = se, そ = so" data-qnum="12">
  <div class="q-number">Q12</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for し?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">si</button>
    <button class="q-option" data-correct="true">shi</button>
    <button class="q-option" data-correct="false">chi</button>
    <button class="q-option" data-correct="false">tsu</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Numbers &amp; Counting" data-explanation="ひゃく (hyaku) = 100. にひゃく = 200, さんびゃく = 300 (note: び not ひ)." data-qnum="13">
  <div class="q-number">Q13</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What number is にひゃくごじゅう (nihyaku gojuu)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">150</button>
    <button class="q-option" data-correct="true">250</button>
    <button class="q-option" data-correct="false">205</button>
    <button class="q-option" data-correct="false">500</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Vocabulary" data-explanation="なん (nan) is the question word meaning 'what'. なんですか = What is it?" data-qnum="14">
  <div class="q-number">Q14</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: なん (nan) is used to ask "where".</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">True</button>
    <button class="q-option" data-correct="true">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 3: ここ/そこ/あそこ, どこ/いくら, の (categorization), Hiragana な-ほ ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="ここ = here (near speaker), そこ = there (near listener), あそこ = over there (far from both)." data-qnum="15">
  <div class="q-number">Q15</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does あそこ (asoko) mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">here</button>
    <button class="q-option" data-correct="false">there (near you)</button>
    <button class="q-option" data-correct="true">over there (far from both)</button>
    <button class="q-option" data-correct="false">where</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="どこ (doko) = where. Used to ask about locations." data-qnum="16">
  <div class="q-number">Q16</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you ask "Where is the bank?" — ぎんこうは ＿ ですか。</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">なん</button>
    <button class="q-option" data-correct="false">だれ</button>
    <button class="q-option" data-correct="true">どこ</button>
    <button class="q-option" data-correct="false">いくら</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="いくら (ikura) = how much. Used when asking about price." data-qnum="17">
  <div class="q-number">Q17</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: いくら (ikura) is used to ask "how much" (price).</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="の (no) can also categorize: にほんの くるま = a Japanese car (car of Japan)." data-qnum="18">
  <div class="q-number">Q18</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">In にほんの くるま, what does の indicate?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Possession (Japan's car)</button>
    <button class="q-option" data-correct="true">Categorization (a Japanese car)</button>
    <button class="q-option" data-correct="false">Location (a car in Japan)</button>
    <button class="q-option" data-correct="false">Question marker</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="な = na, に = ni, ぬ = nu, ね = ne, の = no" data-qnum="19">
  <div class="q-number">Q19</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">Which hiragana represents the sound "nu"?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">な</button>
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">ぬ</button>
    <button class="q-option" data-correct="false">ね</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="は = ha (but わ as particle), ひ = hi, ふ = fu, へ = he (but え as particle), ほ = ho" data-qnum="20">
  <div class="q-number">Q20</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for ふ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">hu</button>
    <button class="q-option" data-correct="true">fu</button>
    <button class="q-option" data-correct="false">su</button>
    <button class="q-option" data-correct="false">tsu</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Numbers &amp; Counting" data-explanation="えん (en) = yen. せん (sen) = 1000. さんぜん is the irregular reading for 3000." data-qnum="21">
  <div class="q-number">Q21</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you say "3000 yen" in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">さんひゃくえん</button>
    <button class="q-option" data-correct="true">さんぜんえん</button>
    <button class="q-option" data-correct="false">さんまんえん</button>
    <button class="q-option" data-correct="false">みっつえん</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 4: を, V-ます/V-ません, で/と, なに, Hiragana ま-よ ════════ -->

<div class="quiz-question" data-topic="Particles" data-explanation="を (wo/o) marks the direct object of a verb: コーヒーを のみます = I drink coffee." data-qnum="22">
  <div class="q-number">Q22</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">コーヒー ＿ のみます。(I drink coffee.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">を</button>
    <button class="q-option" data-correct="false">で</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="V-ます (masu) is the polite present/future form. V-ません (masen) is the polite negative." data-qnum="23">
  <div class="q-number">Q23</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What is the polite negative form of たべます (tabemasu — to eat)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">たべました</button>
    <button class="q-option" data-correct="true">たべません</button>
    <button class="q-option" data-correct="false">たべませんでした</button>
    <button class="q-option" data-correct="false">たべる</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="で (de) indicates the means or location where an action takes place." data-qnum="24">
  <div class="q-number">Q24</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">がっこう ＿ べんきょうします。(I study at school.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">で</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">は</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="と (to) means 'with' when used between people: ともだちと = with a friend." data-qnum="25">
  <div class="q-number">Q25</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">ともだち ＿ ひるごはんを たべます。(I eat lunch with a friend.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">の</button>
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="true">と</button>
    <button class="q-option" data-correct="false">も</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="なに (nani) is used to ask 'what' when it appears before を or a verb." data-qnum="26">
  <div class="q-number">Q26</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How would you ask "What do you eat?" — なにを ＿。</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">たべますか</button>
    <button class="q-option" data-correct="false">のみますか</button>
    <button class="q-option" data-correct="false">しますか</button>
    <button class="q-option" data-correct="false">いきますか</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="ま = ma, み = mi, む = mu, め = me, も = mo" data-qnum="27">
  <div class="q-number">Q27</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">Which hiragana represents the sound "mu"?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ま</button>
    <button class="q-option" data-correct="false">み</button>
    <button class="q-option" data-correct="true">む</button>
    <button class="q-option" data-correct="false">め</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Vocabulary" data-explanation="あさごはん = breakfast, ひるごはん = lunch, ばんごはん = dinner." data-qnum="28">
  <div class="q-number">Q28</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does ばんごはん mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Breakfast</button>
    <button class="q-option" data-correct="false">Lunch</button>
    <button class="q-option" data-correct="true">Dinner</button>
    <button class="q-option" data-correct="false">Snack</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 5: に/から/まで/ごろ, V-ました/V-ませんでした, Time, Hiragana ら-ん ════════ -->

<div class="quiz-question" data-topic="Particles" data-explanation="に (ni) marks a specific point in time: 7じに = at 7 o'clock." data-qnum="29">
  <div class="q-number">Q29</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">7じ ＿ おきます。(I wake up at 7 o'clock.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="true">に</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">は</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="から (kara) = from, まで (made) = until/to. Used together: 9じから5じまで = from 9 to 5." data-qnum="30">
  <div class="q-number">Q30</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does 9じから 5じまで mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">At 9 and 5 o'clock</button>
    <button class="q-option" data-correct="true">From 9 o'clock to 5 o'clock</button>
    <button class="q-option" data-correct="false">Around 9 to around 5</button>
    <button class="q-option" data-correct="false">Before 9 and after 5</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="ごろ (goro) means 'around/about' for approximate time: 3じごろ = around 3 o'clock." data-qnum="31">
  <div class="q-number">Q31</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: ごろ (goro) means "around" when talking about approximate time.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="V-ました (mashita) is polite past tense. たべました = ate." data-qnum="32">
  <div class="q-number">Q32</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What is the polite past tense of のみます (nomimasu — to drink)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">のみません</button>
    <button class="q-option" data-correct="true">のみました</button>
    <button class="q-option" data-correct="false">のみませんでした</button>
    <button class="q-option" data-correct="false">のんだ</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="V-ませんでした (masendeshita) is polite past negative. たべませんでした = did not eat." data-qnum="33">
  <div class="q-number">Q33</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: V-ませんでした is the polite past negative form (e.g., "did not eat").</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="ら = ra, り = ri, る = ru, れ = re, ろ = ro" data-qnum="34">
  <div class="q-number">Q34</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for れ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ra</button>
    <button class="q-option" data-correct="false">ri</button>
    <button class="q-option" data-correct="false">ru</button>
    <button class="q-option" data-correct="true">re</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="ん (n) is the only hiragana that is a standalone consonant — it does not pair with a vowel." data-qnum="35">
  <div class="q-number">Q35</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: ん is the only hiragana character that represents a single consonant sound without a vowel.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>
'''


def get_week2_test_questions():
    """Return the 35 quiz question HTML for the Week 2 test."""
    return '''
<!-- ════════ DAY 6: V-masen deshita, iku/kuru/kaeru, へ/で/と/も, Voiced Hiragana ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="V-ませんでした (masen deshita) = polite negative past. たべませんでした = did not eat." data-qnum="1">
  <div class="q-number">Q1</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: V-ませんでした is the negative past tense form meaning "did not do".</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="いく (iku) = to go, くる (kuru) = to come, かえる (kaeru) = to return/go back (to a place)." data-qnum="2">
  <div class="q-number">Q2</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does いきました mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">went</button>
    <button class="q-option" data-correct="false">came</button>
    <button class="q-option" data-correct="false">returned</button>
    <button class="q-option" data-correct="false">am going</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="へ (e/he) marks direction of movement: がっこうへ いきます = I go to school." data-qnum="3">
  <div class="q-number">Q3</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">えきへ ＿ いきました。(I went to the station.) — which particle?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="true">へ</button>
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="false">を</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="で (de) indicates the means/method or location where an action occurs: くるまで いきます = I go by car." data-qnum="4">
  <div class="q-number">Q4</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">バス ＿ がっこうへ いきました。(I went to school by bus.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">で</button>
    <button class="q-option" data-correct="false">へ</button>
    <button class="q-option" data-correct="false">に</button>
    <button class="q-option" data-correct="false">を</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="と (to) means 'with' when between people or things doing an action together." data-qnum="5">
  <div class="q-number">Q5</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">ともだち ＿ えいがへ いきました。(I went to the movie with a friend.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="true">と</button>
    <button class="q-option" data-correct="false">へ</button>
    <button class="q-option" data-correct="false">に</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="も in negative contexts = 'not even', 'either'. Given in V-masen + も context." data-qnum="6">
  <div class="q-number">Q6</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">I didn't go to the party, and my friend didn't either. Which particle expresses this 'either/not even' meaning?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="true">も</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">に</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="が (ga), ぎ (gi), ぐ (gu), げ (ge), ご (go) — voiced versions of か row." data-qnum="7">
  <div class="q-number">Q7</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for ぎ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ki</button>
    <button class="q-option" data-correct="true">gi</button>
    <button class="q-option" data-correct="false">ku</button>
    <button class="q-option" data-correct="false">go</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Vocabulary" data-explanation="かえります = to return/go back. Used for returning home or to a place." data-qnum="8">
  <div class="q-number">Q8</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does うちへ かえりました mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">came to home</button>
    <button class="q-option" data-correct="true">returned home / went back home</button>
    <button class="q-option" data-correct="false">is returning home</button>
    <button class="q-option" data-correct="false">left home</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 7: いつ, Future Form, V-masen ka, Double Consonant ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="いつ (itsu) = when (specifically for actions). どの日 (which day) as a more explicit version." data-qnum="9">
  <div class="q-number">Q9</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How would you ask "When did you go to Japan?" — いつ ＿ にほんへ いきましたか。</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">you put no word (itsu directly before verb)</button>
    <button class="q-option" data-correct="false">どこ</button>
    <button class="q-option" data-correct="false">だれ</button>
    <button class="q-option" data-correct="false">なに</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="Future form: V-ます becomes V-ます (present = future in polite Japanese). More explicit: V-ます for future or add '次の～' (next...)." data-qnum="10">
  <div class="q-number">Q10</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: In Japanese, the polite present tense (V-ます) can also express future planned actions.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="V-ませんか (masen ka) = invitation form 'Would you like to...' or 'Won't you...'" data-qnum="11">
  <div class="q-number">Q11</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does コーヒーを のみませんか mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">You don't drink coffee</button>
    <button class="q-option" data-correct="true">Would you like to drink coffee? / Won't you have coffee?</button>
    <button class="q-option" data-correct="false">I won't drink coffee</button>
    <button class="q-option" data-correct="false">Did you drink coffee?</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="Small っ (tsu) represents a doubled consonant: がっこう (gakkoo = school), さっぽろ (Sapporo), ずっと (zutto = continuously)." data-qnum="12">
  <div class="q-number">Q12</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: The small っ (tsu) doubles the consonant sound that follows it, as in がっこう (school — 'gak-koo').</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Vocabulary" data-explanation="年 (ねん) = year, 月 (がつ) = month, 日 (ひ/にち) = day. 次の年 (next year), 先月 (last month)." data-qnum="13">
  <div class="q-number">Q13</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How do you say "next year" in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">先年</button>
    <button class="q-option" data-correct="true">来年 (らいねん)</button>
    <button class="q-option" data-correct="false">今年</button>
    <button class="q-option" data-correct="false">去年</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 8: Adjectives, そして, が (contrast), Intensifiers, Long Vowels ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="い-adjectives: positive (赤い = akai = red), negative (赤くない = akaku nai = not red). な-adjectives: きれい (kirei = pretty)." data-qnum="14">
  <div class="q-number">Q14</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What is the negative form of 大きい (ookii = big)?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">大きくある</button>
    <button class="q-option" data-correct="true">大きくない</button>
    <button class="q-option" data-correct="false">大きくない</button>
    <button class="q-option" data-correct="false">大きません</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="そして (soshite) = 'and then', 'and', 'furthermore'. Connects sentences." data-qnum="15">
  <div class="q-number">Q15</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: そして is a connector word meaning 'and' or 'and then' between sentences.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="が (ga) as a contrast marker: connects two ideas with implicit contrast. 私は背が高いです (I am tall [in height]). Note: は (wa) for topic, が for subject/focus." data-qnum="16">
  <div class="q-number">Q16</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">In the sentence 兄は背が高いです (My older brother is tall), which particle expresses the focused quality being described?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="true">が</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">に</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="とても (totemo) = very (for positive descriptions). あまり (amari) = not very, not much (used with negatives)." data-qnum="17">
  <div class="q-number">Q17</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">Which intensifier is used with a NEGATIVE verb form? あまり or とても?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">とても</button>
    <button class="q-option" data-correct="true">あまり</button>
    <button class="q-option" data-correct="false">Both work the same</button>
    <button class="q-option" data-correct="false">Neither — use ね instead</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="Long vowels: aa=あー, ii=いい, uu=うう, ee=ええ, oo=おお or おう. Examples: おかあさん (mother), おにいさん (older brother)." data-qnum="18">
  <div class="q-number">Q18</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What sound does the long vowel in おかあさん (mother) represent?</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">aa (long a)</button>
    <button class="q-option" data-correct="false">ah (short a + h)</button>
    <button class="q-option" data-correct="false">ia (i followed by a)</button>
    <button class="q-option" data-correct="false">ai (a then i)</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 9: Adjective+Noun, どんな, どれ, ね, Contracted Sounds ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="Adjective + Noun: い-adjective goes directly (赤い本 = red book). な-adjective needs な (きれいな本 = pretty book)." data-qnum="19">
  <div class="q-number">Q19</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">きれい ＿ 家 (beautiful house) — what's needed between the na-adjective and noun?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">い</button>
    <button class="q-option" data-correct="true">な</button>
    <button class="q-option" data-correct="false">の</button>
    <button class="q-option" data-correct="false">を</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="どんな (donna) = 'what kind of?' — used to ask about qualities/descriptions." data-qnum="20">
  <div class="q-number">Q20</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How would you ask 'What kind of book do you like?' in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">どこの本が好きですか。</button>
    <button class="q-option" data-correct="true">どんな本が好きですか。</button>
    <button class="q-option" data-correct="false">何の本が好きですか。</button>
    <button class="q-option" data-correct="false">どれの本が好きですか。</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="どれ (dore) = 'which one?' when choosing from 3+ objects. どちら (dochira) for 2 objects." data-qnum="21">
  <div class="q-number">Q21</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">You're pointing at three pens and asking 'Which one is yours?' Use どれ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">どれですか。</button>
    <button class="q-option" data-correct="false">どちらですか。</button>
    <button class="q-option" data-correct="false">どうですか。</button>
    <button class="q-option" data-correct="false">なんですか。</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="ね (ne) at the end of a sentence = seeking agreement/empathy, like English 'right?' or 'isn't it?'" data-qnum="22">
  <div class="q-number">Q22</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: ね (ne) at the end of a sentence seeks agreement or empathy from the listener, like saying 'right?' or 'isn't it?'</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="Contracted sounds: きゃ(kya), ぎゃ(gya), しゃ(sha), じゃ(ja), ちゃ(cha), にゃ(nya), ひゃ(hya), びゃ(bya), ぴゃ(pya), みゃ(mya), りゃ(rya)." data-qnum="23">
  <div class="q-number">Q23</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for しゃ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">sia</button>
    <button class="q-option" data-correct="true">sha</button>
    <button class="q-option" data-correct="false">sa</button>
    <button class="q-option" data-correct="false">sya</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 10: ある/いる, に/が (Existence), Emphasis Particles ════════ -->

<div class="quiz-question" data-topic="Grammar" data-explanation="ある (aru) = for non-living things. いる (iru) = for living things. テーブルの上にペンがあります (There's a pen on the table)." data-qnum="24">
  <div class="q-number">Q24</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">Would use ある or いる? ここに ＿ 猫が ___ます。(There's a cat here.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ある</button>
    <button class="q-option" data-correct="true">いる</button>
    <button class="q-option" data-correct="false">Both work</button>
    <button class="q-option" data-correct="false">Neither word fits</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="に marks location for existence (ある/いる). が marks the subject (the thing existing). ペンがここにあります (A pen is here)." data-qnum="25">
  <div class="q-number">Q25</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">ペン ＿ ここに あります。(The pen is here.) — what particle marks the existing thing?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">は</button>
    <button class="q-option" data-correct="true">が</button>
    <button class="q-option" data-correct="false">を</button>
    <button class="q-option" data-correct="false">に</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="Question: 誰がいますか (Who is there/here)? Statement: 田中さんがいます (Tanaka is here). The subject being identified uses が." data-qnum="26">
  <div class="q-number">Q26</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">Which grammar point does 'There are three people in the room' illustrate?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">V-masen deshita</button>
    <button class="q-option" data-correct="false">へ as direction marker</button>
    <button class="q-option" data-correct="true">ある/いる existence verbs with location particles</button>
    <button class="q-option" data-correct="false">Adjective + noun conjugation</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="や (ya) = 'and (others)', 'etc.' (lists non-exhaustive items). りんご や みかん や いろいろ ... (apples and oranges and various things)." data-qnum="27">
  <div class="q-number">Q27</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: The particle や lists some examples but implies there are other unlisted items (unlike と which lists all).</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="よ (yo) = emphasis/assertion. Adds emphasis/certainty: 大丈夫よ (Don't worry! / It's fine!). Often used at end of sentence." data-qnum="28">
  <div class="q-number">Q28</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">大丈夫 ＿ (Don't worry / It's fine!) — which particle adds emphasis/certainty?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">ね</button>
    <button class="q-option" data-correct="true">よ</button>
    <button class="q-option" data-correct="false">か</button>
    <button class="q-option" data-correct="false">を</button>
  </div>
  <div class="q-feedback"></div>
</div>

<!-- ════════ DAY 6-10 Vocab & Mixed Grammar ════════ -->

<div class="quiz-question" data-topic="Vocabulary" data-explanation="時間 (じかん) = time/duration, 分 (ぶん/ふん) = minutes, 秒 (びょう) = seconds." data-qnum="29">
  <div class="q-number">Q29</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">What does ３０分 mean?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">30 hours</button>
    <button class="q-option" data-correct="true">30 minutes</button>
    <button class="q-option" data-correct="false">30 seconds</button>
    <button class="q-option" data-correct="false">30 days</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="Asking age: (お)年はいくつですか (How old are you?). Answering: ２５才です (I'm 25 years old)." data-qnum="30">
  <div class="q-number">Q30</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How would you ask 'How old is he?' in Japanese?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">彼はいつですか。</button>
    <button class="q-option" data-correct="true">彼はいくつですか。 or 彼はお年はいくつですか。</button>
    <button class="q-option" data-correct="false">彼はどこですか。</button>
    <button class="q-option" data-correct="false">彼は何ですか。</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="に (ni) for destination with iki/ki/kaeru, and for specific time points (7じに = at 7 o'clock)." data-qnum="31">
  <div class="q-number">Q31</div>
  <span class="q-type-badge type-fill">Fill in the Particle</span>
  <div class="q-text">８月 ＿ 日本へ いきます。(I will go to Japan in August.) — which particle?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">へ</button>
    <button class="q-option" data-correct="true">に</button>
    <button class="q-option" data-correct="false">で</button>
    <button class="q-option" data-correct="false">を</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="Review: V-masen ka for invitations. Answering: いいですね (That sounds good!) or ちょっと... (I'm a bit busy...)." data-qnum="32">
  <div class="q-number">Q32</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">If someone says 映画へ いきませんか, what are they asking?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">Where did you go?</button>
    <button class="q-option" data-correct="true">Would you like to go to a movie? / Won't you go to a movie?</button>
    <button class="q-option" data-correct="false">Are you going to a movie?</button>
    <button class="q-option" data-correct="false">Did you go to a movie?</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Hiragana" data-explanation="ざ (za), ぎ (gi), ぐ (gu), ぜ (ze), ぞ (zo) — voiced versions of さ/す/せ/そ row." data-qnum="33">
  <div class="q-number">Q33</div>
  <span class="q-type-badge type-match">Match the Reading</span>
  <div class="q-text">What is the romaji reading for ぜ?</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">se</button>
    <button class="q-option" data-correct="true">ze</button>
    <button class="q-option" data-correct="false">su</button>
    <button class="q-option" data-correct="false">zo</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Grammar" data-explanation="だ/である = plain form of です (is). です is polite form." data-qnum="34">
  <div class="q-number">Q34</div>
  <span class="q-type-badge type-tf">True / False</span>
  <div class="q-text">True or False: です and だ are both copulas that mean 'is', with です being the polite form.</div>
  <div class="q-options">
    <button class="q-option" data-correct="true">True</button>
    <button class="q-option" data-correct="false">False</button>
  </div>
  <div class="q-feedback"></div>
</div>

<div class="quiz-question" data-topic="Particles" data-explanation="Combined: へ marks direction, に marks time/location, で marks means. ７時に車で学校へいきます (At 7 o'clock, I go to school by car)." data-qnum="35">
  <div class="q-number">Q35</div>
  <span class="q-type-badge type-mc">Multiple Choice</span>
  <div class="q-text">How many different particles (へ, に, で) are in this sentence? 朝７時に駅で友達と会いました。(I met my friend at the station at 7 AM.)</div>
  <div class="q-options">
    <button class="q-option" data-correct="false">1 particle</button>
    <button class="q-option" data-correct="false">2 particles</button>
    <button class="q-option" data-correct="true">This sentence has に and で (2 of the three)</button>
    <button class="q-option" data-correct="false">All 3 particles</button>
  </div>
  <div class="q-feedback"></div>
</div>
'''


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

    # Generate precache manifest (all local assets for offline iPad use)
    precache_urls = []
    for subdir in ["lessons", "images", "pdfs", "audio", "videos", "weeks"]:
        asset_dir = SITE_DIR / subdir
        if asset_dir.exists():
            for f in sorted(asset_dir.iterdir()):
                if f.is_file():
                    precache_urls.append(f"./{subdir}/{f.name}")
    precache_manifest = {
        "build_id": build_id,
        "profile": "full_offline",
        "urls": precache_urls,
    }
    (SITE_DIR / "precache-manifest.json").write_text(
        json.dumps(precache_manifest, ensure_ascii=False, indent=2)
    )
    print(f"  Precache manifest: {len(precache_urls)} assets")

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

    # Weekly test pages
    print("  Generating weekly test pages...")
    weeks_out = SITE_DIR / "weeks"
    weeks_out.mkdir(exist_ok=True)
    test_tpl = env.from_string(WEEKLY_TEST_TEMPLATE)
    
    # Week 1 test
    week1_questions = get_week1_test_questions()
    test_html = test_tpl.render(
        test_id="week1-test",
        test_title="Week 1 Test",
        test_subtitle="35 questions covering Days 1–5",
        questions_html=week1_questions
    )
    breadcrumb = '<a href="../index.html">Dashboard</a> → Week 1 → <a href="../lessons/12645437.html">Week 1 Review</a> → Week 1 Test'
    page_html = layout_tpl.render(
        title="Week 1 Test", root="../", breadcrumb=breadcrumb,
        content=test_html, structure=structure,
    )
    (weeks_out / "week1-test.html").write_text(page_html)
    
    # Week 2 test
    week2_questions = get_week2_test_questions()
    test_html = test_tpl.render(
        test_id="week2-test",
        test_title="Week 2 Test",
        test_subtitle="35 questions covering Days 6–10",
        questions_html=week2_questions
    )
    breadcrumb = '<a href="../index.html">Dashboard</a> → Week 2 → <a href="../lessons/12645547.html">Week 2 Review</a> → Week 2 Test'
    page_html = layout_tpl.render(
        title="Week 2 Test", root="../", breadcrumb=breadcrumb,
        content=test_html, structure=structure,
    )
    (weeks_out / "week2-test.html").write_text(page_html)
    
    print("  Weekly test pages generated")

    print(f"Site built at: {SITE_DIR}/")
    print("Done!")


if __name__ == "__main__":
    generate_site()
