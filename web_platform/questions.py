"""
PYQNova ▸ routers/questions.py
──────────────────────────────────────────────────────────────────────────────
Drop-in replacement.  Matches your existing stack:
  • psycopg2 ThreadedConnectionPool  (database.py / db_cursor)
  • RealDictCursor  → rows are plain dicts, not ORM objects
  • Route: GET /api/questions/{chapter}   (what practice.html fetches)
  • Route: GET /api/questions/{chapter}/{index}  (single question by index)

Three bugs fixed
────────────────
BUG 1 — LaTeX artefact "} D \text { will be of the form:"
  Your test_regex.py converts $$ … $$ → $ … $ and leaves ALL the \text{}
  blocks inside for MathJax to render as inline math.  MathJax then shows
  "} D \text { will be of the form:" because the inter-\text tokens
  (like "} D") are outside the \text{} braces and render as raw LaTeX.

  Fix: Pass A detects a fully-$$-wrapped string, strips the outer delimiters,
  then flattens EVERY \text{} in one non-greedy pass, then collapses spaces.
  Result: plain English that MathJax never sees → no artefacts possible.

BUG 2 — "N/A" in all option cards
  db_opts.py uses a plain cursor so r[1] is a raw Python dict (psycopg2
  auto-parses JSONB).  But the API serialises it to JSON and the JS reads
  question.options.A — which works IF options is a dict with keys "A".."D".
  The failure is that your current router sends options as-is without
  checking for null / empty / array formats, AND the template JS tries to
  read question.options["A"] when options might be a list or None.

  Fix: parse_options() normalises every storage format to
  {"A":…,"B":…,"C":…,"D":…, "__type__":"text"|"image"}.

BUG 3 — Second image swallowed into question body
  The scraper stores option images as filenames in the options JSONB column,
  but the current router copies options straight through.  The JS in
  practice.html renders options with a single text path, so image filenames
  appear as plain strings ("N/A" after stripping) or nothing at all.

  Fix: __type__ flag + the updated practice.html render branch.

BUG 4 — Images not loading on Render (Supabase fix)
  Images were served from local filesystem (neet_scrap/examside_data/images)
  which does not exist on Render. Now all image paths are converted to full
  Supabase Storage URLs automatically.
──────────────────────────────────────────────────────────────────────────────
"""

import os
import re
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import db_cursor   # ← your existing pool-backed context manager
from match_list_parser import parse_match_list

router = APIRouter(prefix="/api/questions", tags=["questions"])
logger = logging.getLogger("pyqnova.questions")


# ══════════════════════════════════════════════════════════════════════════════
# §0  Supabase Image URL helper
# ══════════════════════════════════════════════════════════════════════════════

SUPABASE_IMAGE_BASE = os.getenv(
    "SUPABASE_IMAGE_BASE",
    "https://dmfvojxpcxqndfudwhmy.supabase.co/storage/v1/object/public/question-images"
)


def make_image_url(path: str | None) -> str | None:
    """
    Convert any image path to a full Supabase URL.
      • None / empty          → None
      • Already http(s) URL   → return as-is
      • 'examside_data/images/abc.png' or just 'abc.png' → Supabase URL
    """
    if not path:
        return None
    path = path.strip()
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path  # Already a full URL
    # Extract just the filename (handles any prefix path)
    filename = os.path.basename(path)
    return f"{SUPABASE_IMAGE_BASE}/{filename}"


# ══════════════════════════════════════════════════════════════════════════════
# §1  LaTeX Sanitization  — 3-pass pipeline (proven by test_regex.py analysis)
# ══════════════════════════════════════════════════════════════════════════════

_OUTER_DD    = re.compile(r'^\$\$\s*(.*?)\s*\$\$$', re.DOTALL)
_OUTER_SD    = re.compile(r'^\$\s*(.*?)\s*\$$',    re.DOTALL)   # single-$ wrap
_ALL_TEXT_RE = re.compile(r'\\text\s*\{\s*(.*?)\s*\}', re.DOTALL)  # non-greedy
_ISLAND_DD   = re.compile(r'\$\$\s*\\text\s*\{\s*(.*?)\s*\}\s*\$\$', re.DOTALL)
_INLINE_MATH = re.compile(r'(\$[^$\n]+?\$)')      # single-line $…$ spans
_BARE_TEXT   = re.compile(r'\\text\s*\{\s*(.*?)\s*\}', re.DOTALL)
_ORPHAN_DD   = re.compile(r'\$\$\s*\$\$')


def sanitize_latex(raw: str) -> str:
    """
    Strip $$\\text{…}$$ scraper artefacts, preserve real LaTeX math.

    Pass A1 — fully $$-wrapped string (common scraper pattern):
               Strip outer $$, flatten every \\text{}, collapse spaces.
               Early-return — fully clean.

    Pass A2 — fully $-wrapped string containing \\text{} (produced by
               test_regex.py's better_clean() which converts $$ → $).
               Same strategy as A1 — early-return.

    Pass B  — $$ \\text{} $$ islands inside a longer mixed string.

    Pass C  — bare \\text{} outside $…$ math spans.
               Tokenizes on $…$ to preserve real math like $V_{\\text{rms}}$.

    >>> sanitize_latex(
    ...   r'$$ \\text { In the circuit } D \\text { will be of the form: } $$'
    ... )
    'In the circuit D will be of the form:'

    >>> sanitize_latex(r'The value of $V_{\\text{rms}}$ is $220V$')
    'The value of $V_{\\text{rms}}$ is $220V$'    # ← preserved unchanged
    """
    if not raw:
        return raw
    result = raw.strip()

    # Pass A1 ─────────────────────────────────────────────────────────────────
    m = _OUTER_DD.match(result)
    if m:
        inner = _ALL_TEXT_RE.sub(r'\1', m.group(1))
        lines = inner.split('\n')
        lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in lines]
        return '\n'.join(lines).strip()

    # Pass A2 ─────────────────────────────────────────────────────────────────
    # Only treat as scraper noise if the entire string is a single $ block
    # AND it contains \text{} (i.e. it was never real inline math).
    m2 = _OUTER_SD.match(result)
    if m2 and _ALL_TEXT_RE.search(m2.group(1)):
        inner = _ALL_TEXT_RE.sub(r'\1', m2.group(1))
        lines = inner.split('\n')
        lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in lines]
        return '\n'.join(lines).strip()

    # Pass B ─────────────────────────────────────────────────────────────────
    result = _ISLAND_DD.sub(r'\1', result)

    # Pass C ─────────────────────────────────────────────────────────────────
    parts = _INLINE_MATH.split(result)
    result = ''.join(
        seg if i % 2 == 1 else _BARE_TEXT.sub(r'\1', seg)
        for i, seg in enumerate(parts)
    )

    result = _ORPHAN_DD.sub('', result)
    lines = result.split('\n')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


# ══════════════════════════════════════════════════════════════════════════════
# §2  Options normaliser
# ══════════════════════════════════════════════════════════════════════════════

_IMAGE_EXT = re.compile(r'\.(png|jpg|jpeg|gif|webp|svg)$', re.IGNORECASE)
_OPT_KEYS  = ['A', 'B', 'C', 'D']


def parse_options(raw) -> dict:
    """
    Normalise the options column to:
      { "A": "…", "B": "…", "C": "…", "D": "…", "__type__": "text"|"image" }

    Handles:
      • dict  (psycopg2 auto-parses JSONB → already a dict)
      • list  ["opt_A.png", …]
      • str   (TEXT column storing JSON string)
      • None / empty / invalid JSON

    Image filenames are converted to full Supabase URLs.
    """
    if raw is None:
        return {"__type__": "text"}

    # psycopg2 + JSONB column → raw is already a dict or list; no json.loads needed.
    # TEXT column storing JSON → raw is a str.
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("options is not valid JSON: %r", str(raw)[:80])
            return {"__type__": "text"}

    # Normalise list → dict
    if isinstance(raw, list):
        raw = {_OPT_KEYS[i]: v for i, v in enumerate(raw) if i < 4}

    # Normalise nested {"options": {…}}
    if isinstance(raw, dict) and "options" in raw and isinstance(raw["options"], dict):
        raw = raw["options"]

    if not isinstance(raw, dict) or not raw:
        return {"__type__": "text"}

    # Build clean dict (only A-D keys, string values)
    opts: dict = {}
    for k in _OPT_KEYS:
        v = raw.get(k)
        if v is not None:
            opts[k] = str(v).strip()

    if not opts:
        return {"__type__": "text"}

    has_images = any(_IMAGE_EXT.search(v) for v in opts.values())

    # ✅ Convert image filenames to full Supabase URLs
    if has_images:
        for k in _OPT_KEYS:
            if k in opts and _IMAGE_EXT.search(opts[k]):
                opts[k] = make_image_url(opts[k])

    opts["__type__"] = "image" if has_images else "text"
    return opts


# ══════════════════════════════════════════════════════════════════════════════
# §3  Row serializer  (RealDictCursor → JSON-safe dict)
# ══════════════════════════════════════════════════════════════════════════════

def serialize_row(row: dict) -> dict:
    """
    Convert one RealDictCursor row to the shape practice.html expects.
    All sanitization happens here — the JS template stays logic-free.
    """
    raw = row.get("question_text") or ""
    sanitized = sanitize_latex(raw)
    parsed = parse_match_list(raw)

    print(f"RAW: {repr(raw[:80])}")
    print(f"SANITIZED: {repr(sanitized[:80])}")
    print(f"PARSED: {parsed is not None}")

    # ✅ Convert image_path to full Supabase URL
    image_path = row.get("image_path") or row.get("question_image")
    question_image = make_image_url(image_path)

    return {
        "id":                row.get("id"),
        "subject":           row.get("subject", ""),
        "chapter":           row.get("chapter", ""),
        "year":              row.get("year", ""),
        "difficulty":        row.get("difficulty", "medium"),
        # ← sanitized: no $$\text{} artefacts reach the frontend
        "question_text":     sanitized,
        "match_list_parsed": parsed,
        # ✅ Full Supabase URL
        "question_image":    question_image,
        # options: normalised + type-flagged + image URLs fixed
        "options":           parse_options(row.get("options")),
        "correct_answer":    row.get("correct_answer", ""),
        "explanation":       row.get("explanation", ""),
        "tags":              row.get("tags") or [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# §4  Route: GET /api/questions/{chapter}
#     Returns all questions for a chapter (what practice.html loads on mount)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{chapter}")
def get_questions_by_chapter(
    chapter: str,
    subject: Optional[str] = Query(None),
    year:    Optional[int] = Query(None),
    limit:   int           = Query(200, ge=1, le=500),
    offset:  int           = Query(0, ge=0),
):
    """
    Fetch all questions for a chapter slug (e.g. "semiconductor-electronics").
    The chapter URL slug uses hyphens; the DB stores spaces, so we convert.
    """
    # URL slug "semiconductor-electronics" → DB value "Semiconductor Electronics"
    chapter_name = chapter.replace("-", " ").title()

    try:
        with db_cursor() as cur:
            # ── Build query dynamically based on optional filters ────────────
            conditions = ["LOWER(chapter) = LOWER(%s)"]
            params: list = [chapter_name]

            if subject:
                conditions.append("LOWER(subject) = LOWER(%s)")
                params.append(subject)
            if year:
                conditions.append("year = %s")
                params.append(year)

            where = " AND ".join(conditions)
            params += [limit, offset]

            cur.execute(
                f"""
                SELECT
                    id, subject, chapter, year, difficulty,
                    question_text, image_path,
                    options, correct_answer, explanation, tags
                FROM neet_pyqs
                WHERE {where}
                ORDER BY id
                LIMIT %s OFFSET %s
                """,
                params,
            )
            rows = cur.fetchall()

            # Total count (for pagination)
            cur.execute(
                f"SELECT COUNT(*) AS n FROM neet_pyqs WHERE {where}",
                params[:-2],   # strip limit/offset
            )
            total = cur.fetchone()["n"]

    except Exception as exc:
        logger.exception("DB error fetching chapter %r", chapter)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc

    return {
        "chapter":   chapter_name,
        "total":     total,
        "offset":    offset,
        "questions": [serialize_row(dict(r)) for r in rows],
    }


# ══════════════════════════════════════════════════════════════════════════════
# §5  Route: GET /api/questions/{chapter}/{index}
#     Single question by 0-based index (used by Next/Previous buttons)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{chapter}/{index}")
def get_question_by_index(chapter: str, index: int):
    """Return one question by its 0-based position within the chapter."""
    chapter_name = chapter.replace("-", " ").title()

    try:
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT
                    id, subject, chapter, year, difficulty,
                    question_text, image_path,
                    options, correct_answer, explanation, tags
                FROM neet_pyqs
                WHERE LOWER(chapter) = LOWER(%s)
                ORDER BY id
                LIMIT 1 OFFSET %s
                """,
                (chapter_name, index),
            )
            row = cur.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Question not found")

            cur.execute(
                "SELECT COUNT(*) AS n FROM neet_pyqs WHERE LOWER(chapter) = LOWER(%s)",
                (chapter_name,),
            )
            total = cur.fetchone()["n"]

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("DB error fetching %r[%d]", chapter, index)
        raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc

    return {
        "total":    total,
        "index":    index,
        "question": serialize_row(dict(row)),
    }
