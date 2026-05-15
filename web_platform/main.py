import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from config import (
    APP_TITLE, APP_VERSION,
    STATIC_DIR, TEMPLATES_DIR,
    CHARACTERS_DIR, QUESTION_IMAGES_DIR, EXTRACTED_IMAGES_DIR,
    SUBJECT_META, TOTAL_QUESTIONS, SECRET_KEY,
)
from database import create_pool, close_pool, db_cursor
from routers import subjects, chapters, questions, analyze, notebooks, auth, progress

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("pyqnova")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("PYQNova starting — creating DB pool...")
    create_pool()
    logger.info("PYQNova ready!")
    yield
    logger.info("PYQNova shutting down...")
    close_pool()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
# Static mounts
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

if os.path.isdir(CHARACTERS_DIR):
    app.mount("/characters", StaticFiles(directory=CHARACTERS_DIR), name="characters")
    logger.info(f"Characters mounted: {CHARACTERS_DIR}")

if os.path.isdir(QUESTION_IMAGES_DIR):
    app.mount("/images/questions", StaticFiles(directory=QUESTION_IMAGES_DIR), name="question_images")
    logger.info(f"Question images mounted: {QUESTION_IMAGES_DIR}")

if os.path.isdir(EXTRACTED_IMAGES_DIR):
    app.mount("/extracted_images", StaticFiles(directory=EXTRACTED_IMAGES_DIR), name="extracted_images")
    logger.info(f"Extracted images mounted: {EXTRACTED_IMAGES_DIR}")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# API routers
app.include_router(subjects.router)
app.include_router(chapters.router)
app.include_router(questions.router)
app.include_router(analyze.router)
app.include_router(notebooks.router)
app.include_router(auth.router)
app.include_router(progress.router)

@app.get("/notebooks")
def notebooks_page(request: Request):
    return templates.TemplateResponse("notebooks.html", {"request": request, "user": request.session.get("user")})

@app.get("/")
def dashboard(request: Request):
    try:
        with db_cursor() as cur:
            cur.execute("SELECT subject, COUNT(*) AS count FROM neet_pyqs GROUP BY subject ORDER BY subject")
            rows = cur.fetchall()
        subject_counts = {r["subject"].lower(): r["count"] for r in rows}
    except Exception:
        subject_counts = {}

    subjects_data = [
        {**meta, "slug": slug, "count": subject_counts.get(slug, 0)}
        for slug, meta in SUBJECT_META.items()
    ]

    return templates.TemplateResponse("dashboard.html", {
        "request":        request,
        "subjects":       subjects_data,
        "total_questions": TOTAL_QUESTIONS,
        "total_in_db":    sum(subject_counts.values()) or TOTAL_QUESTIONS,
        "user":           request.session.get("user"),
    })


@app.get("/subject/{subject}")
def subject_page(request: Request, subject: str):
    subject = subject.lower()
    meta = SUBJECT_META.get(subject, {"name": subject.title(), "icon": "📚", "color": "#94A3B8"})
    return templates.TemplateResponse("chapters.html", {
        "request":       request,
        "subject":       subject,
        "subject_name":  meta["name"],
        "subject_icon":  meta["icon"],
        "subject_color": meta["color"],
        "user":          request.session.get("user"),
    })


@app.get("/practice/{chapter}")
def practice_page(request: Request, chapter: str):
    subject = "biology"  # default fallback
    try:
        with db_cursor() as cur:
            cur.execute("SELECT subject FROM neet_questions WHERE chapter = %s LIMIT 1", (chapter,))
            row = cur.fetchone()
            if row and row["subject"]:
                subject = row["subject"].lower()
    except Exception as e:
        logger.error(f"Error fetching subject for chapter {chapter}: {e}")

    return templates.TemplateResponse("practice.html", {
        "request":      request,
        "chapter":      chapter,
        "chapter_name": chapter.replace("-", " ").title(),
        "subject":      subject,
        "user":         request.session.get("user"),
    })


@app.get("/health")
def health():
    return JSONResponse({"status": "ok", "app": APP_TITLE, "version": APP_VERSION})
