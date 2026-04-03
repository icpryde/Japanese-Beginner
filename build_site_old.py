#!/usr/bin/env python3
"""
Akamonkai Japanese Course — Static Site Generator

Reads content/manifest.json + content/lessons/*.json and generates
a modern offline PWA site in the site/ directory.
"""
import json
import argparse
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
SCRAPE_REPORT_PATH = CONTENT_DIR / "scrape-report.json"
SITE_DIR = PROJECT_ROOT / "site"

MEDIA_DIRS = {
  "video": "videos",
  "pdf": "pdfs",
  "audio": "audio",
  "image": "images",
}

RELEASE_PROFILES = {"full_offline", "hybrid", "content_only"}


# ─── Helpers ──────────────────────────────────────────────────

def clean_title(raw: str) -> str:
    """Remove Teachable suffixes like 'Text·Free preview' from titles."""
    raw = re.sub(r'(Text|Video|Quiz|Download|Lesson)(·Free preview)?$', '', raw).strip()
    return raw


def parse_week_day(title: str) -> tuple:
    """Extract (week, day) from a lesson title. Returns (0, 0) for intro content."""
    week = 0
    day = 0
    wm = re.search(r'Week\s*(\d+)', title, re.I)
    dm = re.search(r'Day\s*(\d+)', title, re.I)
    if wm:
        week = int(wm.group(1))
    if dm:
        day = int(dm.group(1))
    return week, day


def infer_week_from_day(day: int) -> int:
    """Map day number to week number (5 days per week)."""
    if day == 0:
        return 0
    return ((day - 1) // 5) + 1


def build_course_structure(manifest: dict) -> dict:
    """Organize flat lesson list into a hierarchical structure."""
    structure = OrderedDict()
    # Special section for intro/general content
    structure["intro"] = {
        "title": "Course Introduction",
        "week": 0,
        "lessons": [],
    }

    current_week = 0

    for lesson in manifest["lessons"]:
        raw_title = lesson["title"]
        title = clean_title(raw_title)
        lid = lesson["id"]
        ltype = lesson["type"]

        week, day = parse_week_day(raw_title)

        # If we detect a "Week X Overview", update current week
        if re.search(r'Week\s*\d+\s*Overview', raw_title, re.I) and week > 0:
            current_week = week

        # If no week found but day found, infer week
        if week == 0 and day > 0:
            week = infer_week_from_day(day)
            current_week = week
        elif week == 0 and day == 0:
            week = current_week

        # Try to load downloaded lesson data
        lesson_json = LESSONS_DIR / f"{lid}.json"
        has_content = lesson_json.exists()

        lesson_entry = {
            "id": lid,
            "title": title,
            "raw_title": raw_title,
            "type": ltype,
            "url": lesson["url"],
            "week": week,
            "day": day,
            "has_content": has_content,
        }

        if has_content:
            with open(lesson_json) as f:
                data = json.load(f)
            lesson_entry["primary_type"] = data.get("primary_type", "text")
            lesson_entry["videos"] = data.get("videos", [])
            lesson_entry["downloads"] = data.get("downloads", [])
            lesson_entry["images"] = data.get("images", [])
            lesson_entry["quiz_questions"] = data.get("quiz_questions", [])
            lesson_entry["media_failures"] = data.get("media_failures", [])
            lesson_entry["offline_compatible"] = data.get("offline_compatible", True)
            lesson_entry["html"] = data.get("html", "")
        else:
            lesson_entry["primary_type"] = "text"
            lesson_entry["html"] = f'<p class="placeholder">Content not yet downloaded for: {title}</p>'
            lesson_entry["videos"] = []
            lesson_entry["downloads"] = []
            lesson_entry["images"] = []
            lesson_entry["quiz_questions"] = []
            lesson_entry["media_failures"] = []
            lesson_entry["offline_compatible"] = False

        if week == 0:
            structure["intro"]["lessons"].append(lesson_entry)
        else:
            week_key = f"week-{week}"
            if week_key not in structure:
                structure[week_key] = {
                    "title": f"Week {week}",
                    "week": week,
                    "days": OrderedDict(),
                    "lessons": [],  # week-level lessons (overviews, etc)
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

    return structure


def collect_all_pdfs(structure: dict) -> list:
    """Collect all downloadable PDFs across the course for the worksheet hub."""
    pdfs = []
    for key, section in structure.items():
        if key == "intro":
            for l in section["lessons"]:
                for dl in l.get("downloads", []):
                    if dl.get("type") == "pdf":
                        pdfs.append({**dl, "lesson_title": l["title"],
                                     "week": 0, "day": 0})
        else:
            for l in section.get("lessons", []):
                for dl in l.get("downloads", []):
                    if dl.get("type") == "pdf":
                        pdfs.append({**dl, "lesson_title": l["title"],
                                     "week": section["week"], "day": 0})
            for dk, day_data in section.get("days", {}).items():
                for l in day_data["lessons"]:
                    for dl in l.get("downloads", []):
                        if dl.get("type") == "pdf":
                            pdfs.append({**dl, "lesson_title": l["title"],
                                         "week": section["week"],
                                         "day": day_data["day"]})
    return pdfs


def _extract_filename(value: str) -> str:
    """Extract filename from a path/url-like value."""
    if not value:
        return ""
    value = value.split("?")[0].split("#")[0]
    return Path(value).name


def _iter_media_refs_in_html(html: str):
    """Yield (kind, filename) from lesson HTML for locally hosted media links."""
    if not html:
        return

    patterns = {
        "image": r"(?:src|href)=['\"](?:\.\./)?images/([^'\"?#]+)",
        "audio": r"(?:src|href)=['\"](?:\.\./)?audio/([^'\"?#]+)",
        "video": r"(?:src|href)=['\"](?:\.\./)?videos/([^'\"?#]+)",
        "pdf": r"(?:src|href)=['\"](?:\.\./)?pdfs/([^'\"?#]+)",
    }

    for kind, pattern in patterns.items():
        for match in re.findall(pattern, html, flags=re.I):
            if match:
                yield kind, _extract_filename(match)


def _profile_requires_ref(profile: str, kind: str, has_filename: bool) -> bool:
    """Return whether a media reference is required for the selected release profile."""
    if profile == "content_only":
        return False
    if profile == "hybrid":
        return has_filename
    # full_offline
    return True


def build_asset_audit(ordered_lessons: list, profile: str) -> dict:
    """Build media reference inventory and validate offline completeness."""
    references = []
    failure_reason_counts = {}

    def note_reason(reason: str):
        if not reason:
            return
        failure_reason_counts[reason] = failure_reason_counts.get(reason, 0) + 1

    for lesson in ordered_lessons:
        lesson_id = lesson["id"]

        for v in lesson.get("videos", []):
            filename = _extract_filename(v.get("filename", ""))
            reason = ""
            if not filename:
                reason = v.get("download_status") or "metadata_only_video"
                note_reason(reason)
            references.append({
                "lesson_id": lesson_id,
                "kind": "video",
                "filename": filename,
                "source": "videos[]",
                "required": _profile_requires_ref(profile, "video", bool(filename)),
                "reason": reason,
            })

        for dl in lesson.get("downloads", []):
            dl_kind = "pdf" if dl.get("type") == "pdf" else "audio"
            filename = _extract_filename(dl.get("filename", ""))
            reason = ""
            if not filename:
                reason = dl.get("error") or "missing_download_filename"
                note_reason(reason)
            references.append({
                "lesson_id": lesson_id,
                "kind": dl_kind,
                "filename": filename,
                "source": "downloads[]",
                "required": _profile_requires_ref(profile, dl_kind, bool(filename)),
                "reason": reason,
            })

        for img in lesson.get("images", []):
            filename = _extract_filename(img.get("local", "") or img.get("url", ""))
            reason = ""
            if not filename:
                reason = img.get("error") or "missing_image_filename"
                note_reason(reason)
            references.append({
                "lesson_id": lesson_id,
                "kind": "image",
                "filename": filename,
                "source": "images[]",
                "required": _profile_requires_ref(profile, "image", bool(filename)),
                "reason": reason,
            })

        for kind, filename in _iter_media_refs_in_html(lesson.get("html", "")):
            reason = ""
            if not filename:
                reason = "missing_html_media_filename"
                note_reason(reason)
            references.append({
                "lesson_id": lesson_id,
                "kind": kind,
                "filename": filename,
                "source": "html",
                "required": _profile_requires_ref(profile, kind, bool(filename)),
                "reason": reason,
            })

    for ref in references:
        if not ref["filename"]:
            ref["path"] = ""
            ref["exists"] = False
            if not ref["reason"]:
                ref["reason"] = "missing_filename"
            continue

        media_dir = MEDIA_DIRS.get(ref["kind"])
        ref["path"] = f"{media_dir}/{ref['filename']}"
        ref["exists"] = (CONTENT_DIR / media_dir / ref["filename"]).exists()
        if ref["required"] and not ref["exists"] and not ref["reason"]:
            ref["reason"] = "missing_file"
            note_reason(ref["reason"])

    required_refs = [r for r in references if r["required"]]
    missing_required = [r for r in required_refs if not r["exists"]]

    missing_by_kind = {}
    missing_by_lesson = {}
    for item in missing_required:
      kind = item.get("kind", "unknown")
      lesson_id = item.get("lesson_id", "unknown")
      missing_by_kind[kind] = missing_by_kind.get(kind, 0) + 1
      missing_by_lesson[lesson_id] = missing_by_lesson.get(lesson_id, 0) + 1

    unique_required_paths = sorted({r["path"] for r in required_refs if r["path"]})
    unique_available_required_paths = sorted(
        {r["path"] for r in required_refs if r["path"] and r["exists"]}
    )

    unique_missing_required = sorted(
        {f"{r['lesson_id']}:{r['kind']}:{r['filename'] or '<none>'}:{r['reason']}" for r in missing_required}
    )

    # Per-kind unique path coverage (for threshold enforcement)
    required_by_kind: dict[str, set] = {}
    available_by_kind: dict[str, set] = {}
    for r in required_refs:
        if not r["path"]:
            continue
        k = r["kind"]
        required_by_kind.setdefault(k, set()).add(r["path"])
        if r["exists"]:
            available_by_kind.setdefault(k, set()).add(r["path"])

    coverage_by_kind = {}
    for k, req_paths in required_by_kind.items():
        avail = len(available_by_kind.get(k, set()))
        total = len(req_paths)
        coverage_by_kind[k] = round((avail / total) * 100, 2) if total else 100.0

    summary = {
        "profile": profile,
        "total_references": len(references),
        "required_references": len(required_refs),
        "missing_required_references": len(missing_required),
        "required_unique_paths": len(unique_required_paths),
        "available_required_unique_paths": len(unique_available_required_paths),
        "offline_readiness_percent": (
            round((len(unique_available_required_paths) / len(unique_required_paths)) * 100, 2)
            if unique_required_paths else 100.0
        ),
        "coverage_by_kind": dict(sorted(coverage_by_kind.items())),
        "required_by_kind": {k: len(v) for k, v in sorted(required_by_kind.items())},
        "available_by_kind": {k: len(v) for k, v in sorted(available_by_kind.items())},
        "missing_reason_counts": dict(sorted(failure_reason_counts.items())),
        "missing_by_kind": dict(sorted(missing_by_kind.items())),
        "lessons_with_missing_required": len(missing_by_lesson),
    }

    return {
        "summary": summary,
        "references": references,
        "missing_required": missing_required,
        "missing_by_lesson": dict(sorted(missing_by_lesson.items())),
        "unique_required_paths": unique_required_paths,
        "unique_available_required_paths": unique_available_required_paths,
        "unique_missing_required": unique_missing_required,
    }


def build_text_summary(audit_payload: dict, audit: dict) -> str:
    summary = audit_payload["summary"]
    lines = []
    lines.append("Akamonkai Offline Asset Summary")
    lines.append("=" * 32)
    lines.append(f"Build ID: {audit_payload['build_id']}")
    lines.append(f"Generated At: {audit_payload['generated_at']}")
    lines.append(f"Profile: {audit_payload['profile']}")
    lines.append(f"Allow Missing Media: {audit_payload['allow_missing_media']}")
    lines.append("")
    lines.append("Coverage")
    lines.append(f"- Offline readiness: {summary['offline_readiness_percent']}%")
    lines.append(
        f"- Required assets: {summary['available_required_unique_paths']} / {summary['required_unique_paths']}"
    )
    lines.append(
        f"- Missing required references: {summary['missing_required_references']}"
    )
    lines.append(
        f"- Lessons with missing required references: {summary.get('lessons_with_missing_required', 0)}"
    )
    lines.append("")

    lines.append("Coverage by Kind")
    coverage_by_kind = summary.get("coverage_by_kind", {})
    required_by_kind = summary.get("required_by_kind", {})
    available_by_kind = summary.get("available_by_kind", {})
    if coverage_by_kind:
        for kind in sorted(coverage_by_kind):
            pct = coverage_by_kind[kind]
            avail = available_by_kind.get(kind, 0)
            req = required_by_kind.get(kind, 0)
            flag = "OK" if pct == 100.0 else "MISSING"
            lines.append(f"- {kind}: {pct:.1f}%  ({avail}/{req})  [{flag}]")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("Missing by Kind (reference count)")
    by_kind = summary.get("missing_by_kind", {})
    if by_kind:
        for kind, count in by_kind.items():
            lines.append(f"- {kind}: {count}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("Top Missing Reasons")
    reason_counts = summary.get("missing_reason_counts", {})
    if reason_counts:
        for reason, count in sorted(reason_counts.items(), key=lambda item: item[1], reverse=True)[:10]:
            lines.append(f"- {reason}: {count}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("Most Affected Lessons")
    by_lesson = audit.get("missing_by_lesson", {})
    if by_lesson:
        for lesson_id, count in sorted(by_lesson.items(), key=lambda item: item[1], reverse=True)[:15]:
            lines.append(f"- {lesson_id}: {count} missing required references")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Akamonkai static site")
    parser.add_argument(
        "--profile",
        choices=sorted(RELEASE_PROFILES),
        default="full_offline",
        help="Release profile for offline requirements",
    )
    parser.add_argument(
        "--allow-missing-media",
        action="store_true",
        help="Do not fail the build when required media is missing",
    )
    parser.add_argument(
        "--include-reference-details",
        action="store_true",
        help="Include full reference list in offline-asset-report.json",
    )
    parser.add_argument(
        "--threshold-video",
        type=int,
        default=100,
        metavar="PCT",
        help="Minimum video coverage %% required (default: 100)",
    )
    parser.add_argument(
        "--threshold-pdf",
        type=int,
        default=100,
        metavar="PCT",
        help="Minimum PDF coverage %% required (default: 100)",
    )
    parser.add_argument(
        "--threshold-audio",
        type=int,
        default=100,
        metavar="PCT",
        help="Minimum audio coverage %% required (default: 100)",
    )
    parser.add_argument(
        "--threshold-image",
        type=int,
        default=100,
        metavar="PCT",
        help="Minimum image coverage %% required (default: 100)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Read the existing offline-asset-report.json and exit 0 if "
            "fully ready, 2 if media gaps exist. Does not rebuild the site."
        ),
    )
    return parser.parse_args()


def load_scrape_report() -> dict:
    if not SCRAPE_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(SCRAPE_REPORT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def validate_scrape_report_for_full_offline(scrape_report: dict) -> tuple[bool, str]:
    """Validate scraper diagnostics for strict full_offline release builds."""
    if not scrape_report:
        return False, "missing scrape-report.json"

    stats = scrape_report.get("stats")
    if not isinstance(stats, dict):
        return False, "invalid scrape-report.json stats"

    failed = int(stats.get("failed", 0) or 0)
    media_failures = int(stats.get("media_failures", 0) or 0)

    if failed > 0:
        return False, f"scrape failed lessons={failed}"
    if media_failures > 0:
        return False, f"scrape media_failures={media_failures}"

    return True, "ok"


def check_mode(thresholds: dict) -> int:
    """Read existing offline-asset-report.json and return exit code without rebuilding."""
    report_path = SITE_DIR / "offline-asset-report.json"
    if not report_path.exists():
        print("check: no offline-asset-report.json found — run build first")
        return 2

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"check: failed to read offline-asset-report.json: {exc}")
        return 2

    summary = report.get("summary", {})
    readiness = summary.get("offline_readiness_percent", 0)
    coverage_by_kind = summary.get("coverage_by_kind", {})
    build_id = report.get("build_id", "unknown")
    missing_count = summary.get("missing_required_references", 0)

    print(f"check: build_id={build_id}  readiness={readiness:.1f}%  missing={missing_count}")

    failed = False

    # Per-kind threshold checks
    threshold_breaches = []
    for kind, min_pct in thresholds.items():
        actual = coverage_by_kind.get(kind, 100.0)
        if actual < min_pct:
            threshold_breaches.append(f"{kind}: {actual:.1f}% < {min_pct}%")
    if threshold_breaches:
        print("check: per-kind thresholds not met:")
        for breach in threshold_breaches:
            print(f"  - {breach}")
        failed = True

    if missing_count > 0:
        print(f"check: {missing_count} required references missing")
        failed = True

    if failed:
        return 2

    print("check: OK — all required assets present and thresholds met")
    return 0


# ─── Collect all lesson IDs in order ─────────────────────────

def collect_ordered_lessons(structure: dict) -> list:
    """Return flat list of all lessons in order with navigation metadata."""
    ordered = []
    for key, section in structure.items():
        if key == "intro":
            for l in section["lessons"]:
                ordered.append(l)
        else:
            for l in section.get("lessons", []):
                ordered.append(l)
            for dk, day_data in section.get("days", {}).items():
                for l in day_data["lessons"]:
                    ordered.append(l)

    # Add prev/next IDs
    for i, l in enumerate(ordered):
        l["prev_id"] = ordered[i - 1]["id"] if i > 0 else None
        l["next_id"] = ordered[i + 1]["id"] if i < len(ordered) - 1 else None
        l["lesson_index"] = i

    return ordered


# ─── Templates ────────────────────────────────────────────────

LAYOUT_TEMPLATE = """<!DOCTYPE html>
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
  <link rel="stylesheet" href="{{ root }}css/style.css">
</head>
<body>
  <div class="app">
    <nav class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <h2 class="logo">赤門会<span class="logo-sub">Akamonkai</span></h2>
        <button class="sidebar-close" id="sidebarClose" aria-label="Close sidebar">&times;</button>
      </div>
      <div class="sidebar-search">
        <input type="search" id="searchInput" placeholder="Search lessons..." aria-label="Search">
      </div>
      <div class="sidebar-nav" id="sidebarNav">
        <a href="{{ root }}index.html" class="nav-link nav-home">Dashboard</a>
        <a href="{{ root }}worksheets.html" class="nav-link nav-worksheets">📄 Worksheets</a>
        {% for key, section in structure.items() %}
          {% if key == 'intro' %}
            <div class="nav-section">
              <button class="nav-section-toggle" data-section="intro">Introduction</button>
              <div class="nav-section-items" data-section-content="intro">
                {% for l in section.lessons %}
                <a href="{{ root }}lessons/{{ l.id }}.html" class="nav-link" data-lesson="{{ l.id }}">{{ l.title }}</a>
                {% endfor %}
              </div>
            </div>
          {% else %}
            <div class="nav-section">
              <button class="nav-section-toggle" data-section="{{ key }}">{{ section.title }}</button>
              <div class="nav-section-items" data-section-content="{{ key }}">
                {% for l in section.lessons %}
                <a href="{{ root }}lessons/{{ l.id }}.html" class="nav-link" data-lesson="{{ l.id }}">{{ l.title }}</a>
                {% endfor %}
                {% for dk, day in section.days.items() %}
                <div class="nav-day">
                  <button class="nav-day-toggle" data-day="{{ dk }}">{{ day.title }}</button>
                  <div class="nav-day-items" data-day-content="{{ dk }}">
                    {% for l in day.lessons %}
                    <a href="{{ root }}lessons/{{ l.id }}.html" class="nav-link" data-lesson="{{ l.id }}">{{ l.title }}</a>
                    {% endfor %}
                  </div>
                </div>
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
          <span class="sync-status" id="syncStatus" data-state="idle">Status: Ready</span>
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

DASHBOARD_CONTENT = """
<div class="dashboard">
  <h1>Akamonkai Japanese — 12 Week Beginner Course</h1>
  <div class="progress-overview" id="progressOverview">
    <div class="progress-bar-container">
      <div class="progress-bar" id="progressBar" style="width: 0%"></div>
    </div>
    <p class="progress-text" id="progressText">0 / {{ total_lessons }} lessons completed</p>
  </div>
  <div class="week-grid">
    {% for key, section in structure.items() %}
      {% if key != 'intro' %}
      <a href="lessons/{{ section.lessons[0].id if section.lessons else (section.days.values()|list)[0].lessons[0].id }}.html" class="week-card" data-week="{{ section.week }}">
        <h3>{{ section.title }}</h3>
        <p class="week-days">
          {% set day_nums = [] %}
          {% for dk, day in section.days.items() %}
            {% if day_nums.append(day.day) %}{% endif %}
          {% endfor %}
          {% if day_nums %}Days {{ day_nums|min }}–{{ day_nums|max }}{% endif %}
        </p>
        <p class="week-lesson-count" data-week-num="{{ section.week }}">
          {{ section.lessons|length + section.days.values()|sum(attribute='lessons'|length) if false else '' }}
        </p>
        <div class="week-progress">
          <div class="progress-bar-container small">
            <div class="progress-bar" data-week-progress="{{ section.week }}" style="width: 0%"></div>
          </div>
        </div>
      </a>
      {% endif %}
    {% endfor %}
  </div>
</div>"""

LESSON_CONTENT = """
<article class="lesson" data-lesson-id="{{ lesson.id }}">
  <div class="lesson-header">
    <h1>{{ lesson.title }}</h1>
    <label class="complete-toggle">
      <input type="checkbox" class="lesson-complete-check" data-lesson="{{ lesson.id }}">
      <span>Mark complete</span>
    </label>
  </div>

  {% if lesson.videos %}
  <div class="lesson-videos">
    {% for v in lesson.videos %}
      {% if v.filename %}
      <div class="video-container">
        <video controls preload="metadata" class="lesson-video">
          <source src="../videos/{{ v.filename }}" type="video/mp4">
          Your browser does not support video playback.
        </video>
        <div class="video-controls-custom">
          <select class="playback-speed" aria-label="Playback speed">
            <option value="0.5">0.5×</option>
            <option value="0.75">0.75×</option>
            <option value="1" selected>1×</option>
            <option value="1.25">1.25×</option>
            <option value="1.5">1.5×</option>
            <option value="2">2×</option>
          </select>
        </div>
      </div>
      {% else %}
      <div class="video-placeholder">
        <p>Video not downloaded ({{ v.type }}: {{ v.id }})</p>
        {% if v.url %}<a href="{{ v.url }}" target="_blank" rel="noopener">Watch online</a>{% endif %}
      </div>
      {% endif %}
    {% endfor %}
  </div>
  {% endif %}

  <div class="lesson-body">
    {{ lesson.html | safe }}
  </div>

  {% if lesson.downloads %}
  <div class="lesson-downloads">
    <h3>📄 Downloads</h3>
    {% for dl in lesson.downloads %}
    <a href="../{{ 'pdfs' if dl.type == 'pdf' else 'audio' }}/{{ dl.filename }}"
       class="download-btn" download="{{ dl.filename }}">
      <span class="download-icon">{% if dl.type == 'pdf' %}📄{% else %}🎵{% endif %}</span>
      <span class="download-text">{{ dl.title or dl.filename }}</span>
      <span class="download-action">Download to Device</span>
    </a>
    {% endfor %}
  </div>
  {% endif %}

  {% if lesson.quiz_questions %}
  <div class="lesson-quiz" id="quizContainer" data-lesson="{{ lesson.id }}">
    <h3>Quiz</h3>
    {% for q in lesson.quiz_questions %}
    <div class="quiz-question" data-q-index="{{ loop.index0 }}">
      <p class="q-text">{{ q.question }}</p>
      <div class="q-options">
        {% for opt in q.options %}
        <button class="q-option" data-correct="{{ 'true' if opt.correct else 'false' }}">
          {{ opt.text }}
        </button>
        {% endfor %}
      </div>
      <p class="q-feedback"></p>
    </div>
    {% endfor %}
    <div class="quiz-results" id="quizResults"></div>
  </div>
  {% endif %}

  <div class="lesson-nav">
    {% if lesson.prev_id %}
    <a href="{{ lesson.prev_id }}.html" class="lesson-nav-btn prev" id="prevLesson">← Previous</a>
    {% else %}
    <span class="lesson-nav-btn prev disabled">← Previous</span>
    {% endif %}
    {% if lesson.next_id %}
    <a href="{{ lesson.next_id }}.html" class="lesson-nav-btn next" id="nextLesson">Next →</a>
    {% else %}
    <span class="lesson-nav-btn next disabled">Next →</span>
    {% endif %}
  </div>
</article>"""

WORKSHEETS_CONTENT = """
<div class="worksheets-hub">
  <h1>📄 Worksheets & Downloads</h1>
  <p class="worksheets-intro">All downloadable PDFs and worksheets from the course. Tap "Download to Device" to save to your Files app, GoodNotes, or any other app.</p>

  {% if pdfs %}
  {% set ns = namespace(current_week=-1) %}
  {% for pdf in pdfs %}
    {% if pdf.week != ns.current_week %}
      {% if ns.current_week >= 0 %}</div>{% endif %}
      {% set ns.current_week = pdf.week %}
      <h2 class="worksheet-week-header">{% if pdf.week == 0 %}General{% else %}Week {{ pdf.week }}{% endif %}</h2>
      <div class="worksheet-grid">
    {% endif %}
    <div class="worksheet-card">
      <div class="worksheet-info">
        <h4>{{ pdf.title or pdf.filename }}</h4>
        <p class="worksheet-lesson">From: {{ pdf.lesson_title }}{% if pdf.day %} (Day {{ pdf.day }}){% endif %}</p>
      </div>
      <a href="pdfs/{{ pdf.filename }}" class="download-btn" download="{{ pdf.filename }}">
        <span class="download-action">Download to Device</span>
      </a>
    </div>
  {% endfor %}
  {% if pdfs %}</div>{% endif %}
  {% else %}
  <p class="no-worksheets">No worksheets found. Run the scraper first to download course content.</p>
  {% endif %}
</div>"""


# ─── Generator ────────────────────────────────────────────────

def generate_site(
    profile: str,
    allow_missing_media: bool,
    include_reference_details: bool,
    thresholds: dict | None = None,
):
    print(f"Building site (profile={profile})...")

    # Load manifest
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    # Build structure
    structure = build_course_structure(manifest)
    ordered_lessons = collect_ordered_lessons(structure)
    pdfs = collect_all_pdfs(structure)
    audit = build_asset_audit(ordered_lessons, profile)
    scrape_report = load_scrape_report()

    if profile == "full_offline" and not allow_missing_media:
      report_ok, report_msg = validate_scrape_report_for_full_offline(scrape_report)
      if not report_ok:
        print("  Build blocked: strict full_offline requires a clean scrape report.")
        print(f"    - {report_msg}")
        raise SystemExit(3)

    total_lessons = len(ordered_lessons)
    print(f"  {total_lessons} lessons, {len(pdfs)} PDFs")
    print(
      "  Offline readiness: "
      f"{audit['summary']['offline_readiness_percent']}% "
      f"({audit['summary']['available_required_unique_paths']} / "
      f"{audit['summary']['required_unique_paths']} required assets)"
    )

    if audit["missing_required"]:
      print(
        "  Missing required media references: "
        f"{audit['summary']['missing_required_references']}"
      )
      if profile == "full_offline" and not allow_missing_media:
        print("  Build blocked: strict full_offline profile requires complete media coverage.")
        for item in audit["unique_missing_required"][:15]:
          print(f"    - {item}")
        if len(audit["unique_missing_required"]) > 15:
          remaining = len(audit["unique_missing_required"]) - 15
          print(f"    ... and {remaining} more")
        raise SystemExit(2)

    # Per-kind threshold enforcement (independent of binary missing check)
    if thresholds and not allow_missing_media:
      coverage_by_kind = audit["summary"].get("coverage_by_kind", {})
      threshold_breaches = []
      for kind, min_pct in thresholds.items():
        actual = coverage_by_kind.get(kind, 100.0)
        if actual < min_pct:
          threshold_breaches.append(
            f"{kind}: {actual:.1f}% available < {min_pct}% required"
          )
      if threshold_breaches:
        print("  Build blocked: per-kind coverage thresholds not met.")
        for breach in threshold_breaches:
          print(f"    - {breach}")
        raise SystemExit(2)

    # Setup Jinja2
    env = Environment(loader=BaseLoader())

    # Clean & prepare output
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

    # Copy media content
    for media_type in ["videos", "pdfs", "images", "audio"]:
        src = CONTENT_DIR / media_type
        dst = SITE_DIR / media_type
        if src.exists() and any(src.iterdir()):
            dst.mkdir(exist_ok=True)
            for f in src.iterdir():
                dest_file = dst / f.name
                if not dest_file.exists():
                    shutil.copy2(f, dest_file)

    build_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    # Copy PWA files (inject build id into service worker cache name)
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

    # Generate lesson data JSON for JS
    lesson_data_for_js = []
    for l in ordered_lessons:
        lesson_data_for_js.append({
            "id": l["id"],
            "title": l["title"],
            "week": l["week"],
            "day": l["day"],
            "type": l["primary_type"],
        })
    (SITE_DIR / "lesson-data.json").write_text(
        json.dumps(lesson_data_for_js, ensure_ascii=False)
    )

    # Persist build audit for release checks and diagnostics.
    audit_payload = {
        "build_id": build_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "allow_missing_media": allow_missing_media,
        "summary": audit["summary"],
        "missing_required": audit["missing_required"],
        "missing_by_lesson": audit.get("missing_by_lesson", {}),
        "scrape_report": scrape_report,
    }
    if include_reference_details:
        audit_payload["reference_details"] = audit.get("references", [])
    (SITE_DIR / "offline-asset-report.json").write_text(
        json.dumps(audit_payload, ensure_ascii=False, indent=2)
    )

    summary_text = build_text_summary(audit_payload, audit)
    (SITE_DIR / "offline-asset-summary.txt").write_text(summary_text)

    lesson_urls = [f"/lessons/{l['id']}.html" for l in ordered_lessons]
    media_urls = [f"/{path}" for path in audit["unique_available_required_paths"]]
    precache_payload = {
      "build_id": build_id,
      "profile": profile,
      "urls": sorted(set(lesson_urls + media_urls)),
    }
    (SITE_DIR / "precache-manifest.json").write_text(
      json.dumps(precache_payload, ensure_ascii=False, indent=2)
    )

    layout_tpl = env.from_string(LAYOUT_TEMPLATE)

    # --- Dashboard ---
    print("  Generating dashboard...")
    dashboard_tpl = env.from_string(DASHBOARD_CONTENT)
    dashboard_html = dashboard_tpl.render(
        structure=structure,
        total_lessons=total_lessons,
    )
    page_html = layout_tpl.render(
        title="Dashboard",
        root="",
        breadcrumb="Dashboard",
        content=dashboard_html,
        structure=structure,
    )
    (SITE_DIR / "index.html").write_text(page_html)

    # --- Worksheets ---
    print("  Generating worksheets page...")
    ws_tpl = env.from_string(WORKSHEETS_CONTENT)
    ws_html = ws_tpl.render(pdfs=pdfs)
    page_html = layout_tpl.render(
        title="Worksheets",
        root="",
        breadcrumb='<a href="index.html">Dashboard</a> → Worksheets',
        content=ws_html,
        structure=structure,
    )
    (SITE_DIR / "worksheets.html").write_text(page_html)

    # --- Individual lessons ---
    print("  Generating lesson pages...")
    lesson_tpl = env.from_string(LESSON_CONTENT)

    for i, lesson in enumerate(ordered_lessons):
        # Build breadcrumb
        parts = ['<a href="../index.html">Dashboard</a>']
        if lesson["week"] > 0:
            parts.append(f'Week {lesson["week"]}')
        if lesson["day"] > 0:
            parts.append(f'Day {lesson["day"]}')
        parts.append(lesson["title"][:40])
        breadcrumb = " → ".join(parts)

        lesson_html = lesson_tpl.render(lesson=lesson)
        page_html = layout_tpl.render(
            title=lesson["title"],
            root="../",
            breadcrumb=breadcrumb,
            content=lesson_html,
            structure=structure,
        )
        (lessons_out / f"{lesson['id']}.html").write_text(page_html)

        if (i + 1) % 100 == 0:
            print(f"    {i + 1}/{total_lessons} lessons generated")

    print(f"  All {total_lessons} lesson pages generated")
    print(f"  Wrote: {SITE_DIR / 'offline-asset-report.json'}")
    print(f"  Wrote: {SITE_DIR / 'offline-asset-summary.txt'}")
    print(f"  Wrote: {SITE_DIR / 'precache-manifest.json'}")
    print(f"Site built at: {SITE_DIR}/")
    print("Done!")


if __name__ == "__main__":
    args = parse_args()
    thresholds = {
        "video": args.threshold_video,
        "pdf": args.threshold_pdf,
        "audio": args.threshold_audio,
        "image": args.threshold_image,
    }
    if args.check:
        raise SystemExit(check_mode(thresholds))
    generate_site(
        profile=args.profile,
        allow_missing_media=args.allow_missing_media,
        include_reference_details=args.include_reference_details,
        thresholds=thresholds,
    )
