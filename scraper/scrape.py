#!/usr/bin/env python3
"""
Akamonkai Japanese Course Scraper — Production version.

Uses persistent browser context to handle Cloudflare challenges.
Downloads all content: text, embedded videos, PDFs, images, audio, quizzes.
Supports resume — skips already-downloaded lessons.
"""
import asyncio
import argparse
import json
import hashlib
import logging
import mimetypes
import random
import re
import subprocess
import tempfile
import time
import urllib.parse
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page

# === Paths ===
PROJECT_ROOT = Path(__file__).parent.parent
CONTENT_DIR = PROJECT_ROOT / "content"
LESSONS_DIR = CONTENT_DIR / "lessons"
VIDEOS_DIR = CONTENT_DIR / "videos"
PDFS_DIR = CONTENT_DIR / "pdfs"
IMAGES_DIR = CONTENT_DIR / "images"
AUDIO_DIR = CONTENT_DIR / "audio"
MANIFEST_PATH = CONTENT_DIR / "manifest.json"
BROWSER_DATA = PROJECT_ROOT / ".browser_data"
SCRAPE_REPORT_PATH = CONTENT_DIR / "scrape-report.json"

# === Course config ===
BASE_URL = "https://japaneseonline.gogonihon.com"
COURSE_SLUG = "akamonkai-japanese-12-week-beginner-course"
USERNAME = "ichoppryde@gmail.com"
PASSWORD = "dXXc6EM2mxib3W"

# === Settings ===
DELAY_MIN = 1.5
DELAY_MAX = 3.5
BATCH_SAVE_INTERVAL = 25

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "scraper.log"),
    ],
)
log = logging.getLogger("scraper")


# --- Utilities ---

def delay():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

def safe_filename(name: str, max_len: int = 80) -> str:
    name = re.sub(r'[^\w\s\-\.]', '', name)
    name = re.sub(r'\s+', '-', name.strip())
    return name[:max_len]

def url_hash(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:10]

def lesson_id_from_url(url: str) -> str:
    m = re.search(r'/(\d+)-', url)
    return m.group(1) if m else url_hash(url)

def is_downloaded(lid: str) -> bool:
    return (LESSONS_DIR / f"{lid}.json").exists()


def absolute_url(url: str) -> str:
    if not url:
        return ""
    return urllib.parse.urljoin(BASE_URL + "/", url)


def infer_ext_from_type(content_type: str, default: str = ".bin") -> str:
    if not content_type:
        return default
    ctype = content_type.split(";")[0].strip().lower()
    if ctype == "audio/mpeg":
        return ".mp3"
    if ctype == "audio/mp4":
        return ".m4a"
    if ctype == "application/pdf":
        return ".pdf"
    if ctype == "video/mp4":
        return ".mp4"
    ext = mimetypes.guess_extension(ctype)
    return ext or default


def infer_download_kind(url: str, text_hint: str, content_type: str = "") -> str:
    u = (url or "").lower()
    t = (text_hint or "").lower()
    c = (content_type or "").lower()
    if any(x in u for x in [".mp3", ".wav", ".m4a", ".ogg"]) or any(
        x in t for x in ["audio", "listen", "mp3", "pronunciation"]
    ) or c.startswith("audio/"):
        return "audio"
    return "pdf"


# --- Cloudflare wait ---

async def wait_for_cf(page, timeout=120):
    for i in range(timeout // 3):
        title = await page.title()
        if 'just a moment' not in title.lower():
            return True
        await page.wait_for_timeout(3000)
        if i % 10 == 0:
            log.info(f"  CF wait... ({i*3}s)")
    return False


# --- Login ---

async def ensure_logged_in(page):
    url = page.url
    if 'sign_in' not in url and 'login' not in url:
        return True

    log.info("Login required...")
    for sel in ['input[name="user[email]"]', 'input[type="email"]']:
        try:
            el = await page.wait_for_selector(sel, timeout=5000)
            if el:
                await el.fill(USERNAME)
                break
        except Exception:
            continue

    for sel in ['input[name="user[password]"]', 'input[type="password"]']:
        try:
            el = await page.wait_for_selector(sel, timeout=5000)
            if el:
                await el.fill(PASSWORD)
                break
        except Exception:
            continue

    for sel in ['button:has-text("Sign in")', 'button:has-text("Log In")',
                'input[type="submit"]', 'button[type="submit"]']:
        try:
            btn = await page.wait_for_selector(sel, timeout=3000)
            if btn:
                await btn.click()
                log.info("Login submitted")
                break
        except Exception:
            continue

    await page.wait_for_timeout(5000)
    await wait_for_cf(page)
    log.info(f"Post-login: {page.url}")
    return 'sign_in' not in page.url


# --- Navigation with CF handling ---

async def goto(page, url, retries=3):
    for attempt in range(retries):
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await wait_for_cf(page)
            if 'sign_in' in page.url:
                await ensure_logged_in(page)
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await wait_for_cf(page)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            await page.wait_for_timeout(2000)
            return True
        except Exception as e:
            log.warning(f"Navigation attempt {attempt+1} failed: {e}")
            if attempt < retries - 1:
                await page.wait_for_timeout(5000)
    return False


# --- Download helpers ---

async def download_binary(page, url: str, dest: Path) -> tuple[bool, str]:
    if dest.exists() and dest.stat().st_size > 0:
        return True, "already_exists"
    try:
        resp = await page.context.request.get(url, timeout=60000)
        if resp.ok:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(await resp.body())
            return True, "downloaded"
        else:
            log.warning(f"HTTP {resp.status} for {url}")
            return False, f"http_{resp.status}"
    except Exception as e:
        log.warning(f"Download failed {url}: {e}")
        return False, f"exception:{type(e).__name__}"


async def wait_for_lesson_content(page, lesson_id: str):
    """Wait for dynamic course player content to finish rendering."""
    try:
        await page.wait_for_selector("#content-inner, .fr-view, .lesson-content", timeout=15000)
    except Exception:
        pass

    # Spinner may linger in shell snapshots; wait for it to disappear when present.
    try:
        await page.wait_for_selector(".course-player__loading-spinner", state="hidden", timeout=12000)
    except Exception:
        pass

    for _ in range(10):
        html = await page.content()
        if lesson_id in html:
            return html
        if any(x in html for x in ["videoproxy_embed", "wvideo=", "<audio", "<img", ".pdf", ".mp3"]):
            return html
        await page.wait_for_timeout(1200)

    return await page.content()


def extract_primary_content_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for sel in [
        ".lecture-content",
        ".lesson-content",
        ".fr-view",
        ".text-content",
        "#content-inner",
        '[role="main"] .container',
    ]:
        el = soup.select_one(sel)
        if el:
            return str(el)
    main = soup.select_one("main")
    if main:
        return str(main)
    return str(soup.select_one("body") or "")


async def extract_and_download_images(page, html: str, lesson_id: str) -> tuple:
    soup = BeautifulSoup(html, "html.parser")
    images = []

    urls = set()

    for img in soup.select("img[src]"):
        src = img.get("src", "")
        if src and not src.startswith("data:"):
            urls.add(absolute_url(src))

    # Some slide decks use CSS background-image URLs.
    for node in soup.select("[style]"):
        style = node.get("style", "")
        for m in re.finditer(r"url\((['\"]?)([^'\")]+)\1\)", style):
            src = m.group(2).strip()
            if src and not src.startswith("data:"):
                urls.add(absolute_url(src))

    for src in sorted(urls):
        if not src:
            continue

        ext = Path(urllib.parse.urlparse(src).path).suffix or ".png"
        ext = ext.split("?")[0]
        if len(ext) > 6:
            ext = ".png"

        local_name = f"{url_hash(src)}{ext}"
        local_path = IMAGES_DIR / local_name

        ok, reason = await download_binary(page, src, local_path)
        if ok:
            images.append({"url": src, "local": local_name})
        else:
            images.append({"url": src, "local": "", "error": reason})

    for img in soup.select("img[src]"):
        src = absolute_url(img.get("src", ""))
        match = next((i for i in images if i["url"] == src and i.get("local")), None)
        if match:
            img["src"] = f"../../images/{match['local']}"

    return str(soup), images


async def extract_videos_from_html(html: str) -> list:
    videos = []

    # Wistia
    for m in re.finditer(r'wistia\.com/medias/(\w+)|wistia_async_(\w+)', html):
        wid = m.group(1) or m.group(2)
        videos.append({"type": "wistia", "id": wid,
                        "url": f"https://fast.wistia.com/medias/{wid}"})

    # Vimeo
    for m in re.finditer(r'player\.vimeo\.com/video/(\d+)', html):
        videos.append({"type": "vimeo", "id": m.group(1),
                        "url": f"https://vimeo.com/{m.group(1)}"})

    # YouTube
    for m in re.finditer(r'youtube\.com/embed/([\w-]+)', html):
        videos.append({"type": "youtube", "id": m.group(1),
                        "url": f"https://www.youtube.com/watch?v={m.group(1)}"})

    # Teachable native video URL
    for m in re.finditer(r'"videoUrl"\s*:\s*"([^"]+)"', html):
        url = m.group(1).replace("\\u0026", "&")
        videos.append({"type": "teachable", "id": url_hash(url), "url": url})

    # Teachable course player embeds
    for m in re.finditer(r'https://[^"\']+/api/course_player/v2/contents/\d+/play/\d+[^"\'\s<]*', html):
        url = m.group(0).replace("&amp;", "&")
        videos.append({"type": "course_player", "id": url_hash(url), "url": url})

    # Direct <video> source
    soup = BeautifulSoup(html, "html.parser")
    for src in soup.select("video source[src]"):
        url = src["src"]
        url = absolute_url(url)
        videos.append({"type": "direct", "id": url_hash(url), "url": url})

    for iframe in soup.select("iframe[src]"):
        src = absolute_url(iframe.get("src", ""))
        if "/api/course_player/v2/" in src or "wvideo=" in src:
            videos.append({"type": "teachable_embed", "id": url_hash(src), "url": src})

    for a in soup.select("a[href]"):
        href = absolute_url(a.get("href", ""))
        txt = a.get_text(" ", strip=True)
        if "wvideo=" in href or txt.lower().endswith(".mp4"):
            videos.append({"type": "teachable_link", "id": url_hash(href), "url": href})

    # Deduplicate
    seen = set()
    unique = []
    for v in videos:
        if v["url"] not in seen:
            seen.add(v["url"])
            unique.append(v)
    return unique


async def download_video(page, lesson_id: str, title: str, video_info: dict) -> tuple[str | None, str]:
    safe_t = safe_filename(title)
    prefix = f"{lesson_id}_{safe_t}"

    existing = list(VIDEOS_DIR.glob(f"{lesson_id}_*"))
    if existing:
        return existing[0].name, "already_exists"

    # First try authenticated direct fetch for protected platform URLs.
    video_url = video_info["url"]
    if "gogonihon.com" in urllib.parse.urlparse(video_url).netloc:
        try:
            resp = await page.context.request.get(video_url, timeout=60000)
            if resp.ok:
                ctype = (resp.headers.get("content-type") or "").lower()
                if "video/" in ctype or "application/octet-stream" in ctype:
                    ext = infer_ext_from_type(ctype, ".mp4")
                    out = VIDEOS_DIR / f"{prefix}{ext}"
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(await resp.body())
                    log.info(f"    Video saved (direct): {out.name}")
                    return out.name, "downloaded_direct"
        except Exception as e:
            log.warning(f"    Direct video fetch failed: {e}")

    output_tpl = str(VIDEOS_DIR / f"{prefix}.%(ext)s")
    try:
        cookie_file = PROJECT_ROOT / ".yt-dlp-cookies.txt"
        cookies = await page.context.cookies()
        lines = ["# Netscape HTTP Cookie File"]
        for c in cookies:
            domain = c.get("domain", "")
            include_sub = "TRUE" if domain.startswith(".") else "FALSE"
            path = c.get("path", "/")
            secure = "TRUE" if c.get("secure") else "FALSE"
            exp = int(c.get("expires", 0) or 0)
            lines.append(
                f"{domain}\t{include_sub}\t{path}\t{secure}\t{exp}\t{c.get('name','')}\t{c.get('value','')}"
            )
        cookie_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        cmd = [
            "yt-dlp", "--no-check-certificates", "--no-playlist",
            "--cookies", str(cookie_file),
            "-o", output_tpl, video_url,
        ]
        log.info(f"    yt-dlp: {video_info['type']} {video_info['id']}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            dl = list(VIDEOS_DIR.glob(f"{prefix}.*"))
            if dl:
                log.info(f"    Video saved: {dl[0].name}")
                return dl[0].name, "downloaded"
        else:
            log.warning(f"    yt-dlp error: {result.stderr[:200]}")
            return None, "yt_dlp_error"
    except subprocess.TimeoutExpired:
        log.warning(f"    yt-dlp timeout for {video_info['url']}")
        return None, "yt_dlp_timeout"
    except Exception as e:
        log.warning(f"    Video download error: {e}")
        return None, f"exception:{type(e).__name__}"
    return None, "download_not_found"


async def extract_downloads(page, html: str, lesson_id: str, title: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    downloads = []

    selectors = [
        'a[href$=".pdf"]', 'a[href*=".pdf?"]',
        'a[href$=".mp3"]', 'a[href*=".mp3?"]',
        'a[href$=".wav"]', 'a[href$=".m4a"]',
        'audio[src]', 'audio source[src]',
        'a[download]', 'a[href*="download"]',
        'a[href*="attachment"]', 'a[href*="resource"]',
    ]

    links = set()
    day_match = re.search(r"Day\s*(\d+)", title or "", re.I)
    lesson_day = int(day_match.group(1)) if day_match else None
    for sel in selectors:
        for a in soup.select(sel):
            href = a.get("href", "") or a.get("src", "")
            if href:
                href = absolute_url(href)
                links.add((href, a.get_text(strip=True)))

    # Catch media-labeled links with opaque signed URLs.
    for a in soup.select("a[href]"):
        href = absolute_url(a.get("href", ""))
        txt = a.get_text(" ", strip=True)
        marker = (href + " " + txt).lower()
        if any(k in marker for k in ["audio", "mp3", "pdf", "worksheet", "slides"]):
            links.add((href, txt))

    # Keep links likely belonging to this lesson and avoid whole-course document dumps.
    filtered_links = []
    for href, txt in sorted(links):
        text_norm = (txt or "").lower()
        href_norm = (href or "").lower()

        # If a link explicitly mentions a different day, skip it.
        if lesson_day is not None:
            m = re.search(r"day\s*[- ]?(\d+)", text_norm, re.I)
            if m and int(m.group(1)) != lesson_day:
                continue

        # Skip obvious navigation/section links.
        if any(k in href_norm for k in ["/communities/", "/courses/take/", "/sign_in", "/enroll"]):
            if "download" not in href_norm and "attachment" not in href_norm:
                continue

        filtered_links.append((href, txt))

    # Safety cap: a single lesson should not produce hundreds of downloads.
    links = filtered_links[:20]

    for href, link_text in links:
        path = urllib.parse.urlparse(href).path
        ext = Path(path).suffix.lower().split("?")[0]
        if len(ext) > 6:
            ext = ""

        kind = infer_download_kind(href, link_text)
        dest_dir = AUDIO_DIR if kind == "audio" else PDFS_DIR
        if not ext:
            ext = ".mp3" if kind == "audio" else ".pdf"

        fname = f"{lesson_id}_{safe_filename(link_text or title)}{ext}"
        dest = dest_dir / fname

        ok, reason = await download_binary(page, href, dest)
        if ok:
            ftype = kind
            downloads.append({
                "url": href, "filename": fname,
                "type": ftype, "title": link_text,
            })
            log.info(f"    Downloaded {ftype}: {fname}")
        else:
            ftype = kind
            downloads.append({
                "url": href,
                "filename": "",
                "type": ftype,
                "title": link_text,
                "error": reason,
            })

    return downloads


async def extract_quiz(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    questions = []

    for i, block in enumerate(soup.select(
        '.quiz-question, [class*="question"], .question-content'
    )):
        q_el = block.select_one('.question-text, h3, h4, p')
        if not q_el:
            continue
        options = []
        for opt in block.select('label, .answer-option, [class*="option"]'):
            text = opt.get_text(strip=True)
            if text:
                correct = 'correct' in ' '.join(opt.get('class', []))
                options.append({"text": text, "correct": correct})
        questions.append({
            "index": i + 1,
            "question": q_el.get_text(strip=True),
            "options": options,
        })

    if not questions:
        for m in re.finditer(r'"questions"\s*:\s*(\[.*?\])', html, re.DOTALL):
            try:
                questions = json.loads(m.group(1))
                break
            except json.JSONDecodeError:
                pass

    return questions


# --- Main lesson downloader ---

async def download_lesson(page, lesson: dict) -> dict:
    lid = lesson["id"]
    title = lesson["title"]

    if is_downloaded(lid):
        log.info(f"  [skip] {title}")
        return {"skipped": True}

    log.info(f"  Downloading: {title}")

    ok = await goto(page, lesson["url"])
    if not ok:
        log.error(f"  Failed to navigate to {title}")
        return {"error": "navigation_failed"}

    html = await wait_for_lesson_content(page, lid)
    content_html = extract_primary_content_html(html)

    # Detect what's on this page
    videos = await extract_videos_from_html(html)
    downloads = await extract_downloads(page, content_html, lid, title)
    quiz_questions = await extract_quiz(html) if 'quiz' in lesson.get('type', '') else []

    # Download images and rewrite URLs
    content_html, images = await extract_and_download_images(page, content_html, lid)

    # Download videos
    video_files = []
    media_failures = []
    for v in videos:
        fname, status = await download_video(page, lid, title, v)
        video_files.append({**v, "filename": fname, "download_status": status})
        if not fname:
            media_failures.append({
                "kind": "video",
                "source_url": v.get("url", ""),
                "source_type": v.get("type", ""),
                "reason": status,
            })

    for d in downloads:
        if not d.get("filename"):
            media_failures.append({
                "kind": d.get("type", "download"),
                "source_url": d.get("url", ""),
                "source_type": "download",
                "reason": d.get("error", "download_failed"),
            })

    for img in images:
        if not img.get("local"):
            media_failures.append({
                "kind": "image",
                "source_url": img.get("url", ""),
                "source_type": "image",
                "reason": img.get("error", "download_failed"),
            })

    # Determine primary content type
    if quiz_questions:
        primary_type = "quiz"
    elif video_files:
        primary_type = "video"
    elif downloads:
        primary_type = "download"
    else:
        primary_type = "text"

    # Save lesson data
    lesson_data = {
        "id": lid,
        "title": title,
        "url": lesson["url"],
        "section": lesson.get("section", ""),
        "primary_type": primary_type,
        "html": content_html,
        "images": images,
        "videos": video_files,
        "downloads": downloads,
        "quiz_questions": quiz_questions,
        "media_failures": media_failures,
        "offline_compatible": len(media_failures) == 0,
        "downloaded_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    out_path = LESSONS_DIR / f"{lid}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(lesson_data, f, indent=2, ensure_ascii=False)

    log.info(f"    Saved: type={primary_type} imgs={len(images)} "
             f"vids={len(video_files)} dl={len(downloads)} quiz={len(quiz_questions)} "
             f"media_failures={len(media_failures)}")
    return lesson_data


# --- Main ---

async def main(args: argparse.Namespace):
    log.info("=" * 60)
    log.info("Akamonkai Course Scraper - Starting")
    log.info("=" * 60)

    for d in [CONTENT_DIR, LESSONS_DIR, VIDEOS_DIR, PDFS_DIR, IMAGES_DIR, AUDIO_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not MANIFEST_PATH.exists():
        log.error("No manifest.json found! Run enumerate_course.py first.")
        return
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    lessons = manifest["lessons"]
    if args.lesson_id:
        lessons = [l for l in lessons if str(l.get("id")) == str(args.lesson_id)]
        if not lessons:
            log.error(f"No lesson found for id={args.lesson_id}")
            return
    total = len(lessons)
    log.info(f"Manifest loaded: {total} lessons")

    already = sum(1 for l in lessons if is_downloaded(l["id"]))
    log.info(f"Already downloaded: {already}/{total}")

    if already == total:
        log.info("All lessons already downloaded!")
        return

    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            str(BROWSER_DATA),
            headless=args.headless,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        log.info("Navigating to course...")
        await goto(page, f"{BASE_URL}/courses/take/{COURSE_SLUG}")

        stats = {
            "downloaded": 0,
            "skipped": already,
            "failed": 0,
            "media_failures": 0,
            "offline_compatible": 0,
        }

        for i, lesson in enumerate(lessons):
            lid = lesson["id"]
            if is_downloaded(lid):
                continue

            log.info(f"[{i+1}/{total}] ({stats['downloaded']+stats['skipped']}/{total} done)")
            try:
                result = await download_lesson(page, lesson)
                if result.get("skipped"):
                    stats["skipped"] += 1
                elif result.get("error"):
                    stats["failed"] += 1
                else:
                    stats["downloaded"] += 1
                    stats["media_failures"] += len(result.get("media_failures", []))
                    if result.get("offline_compatible"):
                        stats["offline_compatible"] += 1
            except Exception as e:
                log.error(f"  FAILED: {e}")
                stats["failed"] += 1
                err_path = LESSONS_DIR / f"{lid}_error.txt"
                err_path.write_text(f"URL: {lesson['url']}\nError: {e}")

            delay()

            if (stats["downloaded"] + stats["failed"]) % BATCH_SAVE_INTERVAL == 0:
                log.info(f"  Progress: {stats}")

        await ctx.close()

    log.info("=" * 60)
    log.info(f"Scraping complete! {stats}")
    log.info("=" * 60)

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "stats": stats,
        "total_lessons": total,
    }
    SCRAPE_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    log.info(f"Scrape report written: {SCRAPE_REPORT_PATH}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Akamonkai course content")
    parser.add_argument("--lesson-id", help="Scrape only one lesson id (debug mode)")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_args()
    asyncio.run(main(cli_args))
