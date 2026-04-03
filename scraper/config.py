"""Configuration for the Akamonkai course scraper."""
import os
from pathlib import Path

# === Paths ===
PROJECT_ROOT = Path(__file__).parent.parent
CONTENT_DIR = PROJECT_ROOT / "content"
LESSONS_DIR = CONTENT_DIR / "lessons"
VIDEOS_DIR = CONTENT_DIR / "videos"
PDFS_DIR = CONTENT_DIR / "pdfs"
IMAGES_DIR = CONTENT_DIR / "images"
AUDIO_DIR = CONTENT_DIR / "audio"
MANIFEST_PATH = CONTENT_DIR / "manifest.json"
SITE_DIR = PROJECT_ROOT / "site"

# === Course URLs ===
BASE_URL = "https://japaneseonline.gogonihon.com"
LOGIN_URL = f"{BASE_URL}/users/sign_in"
COURSE_SLUG = "akamonkai-japanese-12-week-beginner-course"
COURSE_URL = f"{BASE_URL}/courses/take/{COURSE_SLUG}"
COURSE_LANDING = f"{BASE_URL}/courses/{COURSE_SLUG}"

# === Credentials (read from environment or fallback) ===
USERNAME = os.environ.get("AKAMONKAI_USER", "ichoppryde@gmail.com")
PASSWORD = os.environ.get("AKAMONKAI_PASS", "dXXc6EM2mxib3W")

# === Scraper Settings ===
REQUEST_DELAY_MIN = 1.0  # seconds between requests
REQUEST_DELAY_MAX = 3.0  # seconds between requests
MAX_RETRIES = 3
TIMEOUT = 60000  # ms for page loads
HEADLESS = True  # set to False for debugging

# === Content Type Detection (from Teachable URL patterns) ===
CONTENT_TYPES = {
    "texts": "text",
    "multimedia": "video",
    "quizzes": "quiz",
    "downloads": "download",
    "lessons": "mixed",
}
