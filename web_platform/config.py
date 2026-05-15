import os

# ── Database (mirrors neet_scrap/db_config.py — READ-ONLY) ──────────────────
DATABASE_URL = os.getenv("DATABASE_URL")
DB_HOST = "localhost"
DB_NAME = "neet_db"
DB_USER = "postgres"
DB_PASS = "Dream@1234"
DB_PORT = 5432

# ── Path anchors ─────────────────────────────────────────────────────────────
# web_platform/ directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# PYQNova/ root
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# neet_scrap/ sibling directory (scraper output – never modified)
SCRAPER_ROOT = os.path.join(os.path.dirname(PROJECT_ROOT), "neet_scrap")

# Scraped question images (mounted read-only at /images/questions)
QUESTION_IMAGES_DIR = os.path.join(SCRAPER_ROOT, "examside_data", "images")

# Options extracted images (mounted at /extracted_images)
EXTRACTED_IMAGES_DIR = os.path.join(SCRAPER_ROOT, "extracted_images")

# Nova Squad character art (mounted at /static/characters)
CHARACTERS_DIR = os.path.join(PROJECT_ROOT, "characters")

# Static / Templates dirs
STATIC_DIR  = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# ── App metadata ─────────────────────────────────────────────────────────────
APP_TITLE    = "PYQNova"
APP_VERSION  = "1.0.0"
TOTAL_QUESTIONS = 6521

# Subject display metadata
SUBJECT_META = {
    "physics": {
        "name": "Physics",
        "icon": "⚛️",
        "color": "#14B8A6",
        "bg": "rgba(20,184,166,0.08)",
    },
    "chemistry": {
        "name": "Chemistry",
        "icon": "🧪",
        "color": "#818CF8",
        "bg": "rgba(129,140,248,0.08)",
    },
    "biology": {
        "name": "Biology",
        "icon": "🌿",
        "color": "#34D399",
        "bg": "rgba(52,211,153,0.08)",
    },
}

# ── Authentication & Sessions ────────────────────────────────────────────────
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-pyqnova-session-key-for-local")
