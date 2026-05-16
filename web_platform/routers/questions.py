import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query
from database import db_cursor

router = APIRouter(prefix="/api", tags=["Questions"])


import os
import re
import logging
from config import QUESTION_IMAGES_DIR

logger = logging.getLogger(__name__)

def safe_json(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    try:
        # Basic cleaning for single quotes
        cleaned = value.replace("'", '"').strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error(f"JSON Parse Error: {e} | RAW DATA: {value}")
        return value

def sanitize_latex(raw: str) -> str:
    if not raw:
        return raw
    result = raw.strip()
    
    # Pass A: Strip outer $$ ... $$ or $ ... $ wrappers
    if result.startswith('$$') and result.endswith('$$'):
        result = result[2:-2].strip()
    elif result.startswith('$') and result.endswith('$'):
        result = result[1:-1].strip()
        
    # Pass B: Flatten all \text{ ... } blocks
    # Non-greedy match to replace \text{anything} with anything
    result = re.sub(r'\\text\s*\{\s*(.*?)\s*\}', r'\1', result)
    
    # Pass C: Clean any orphaned double dollars left over
    result = re.sub(r'\$\$\s*\$\$', '', result)
    
    lines = result.split('\n')
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def clean_solution(sol: str) -> str:
    """Strip malformed LaTeX artifacts from scraped solution text."""
    if not sol:
        return sol
    s = sol
    # Fix double-escaped backslashes from DB
    s = s.replace('\\\\', '\\')
    # Remove empty inline math \(\) or \( \)
    s = re.sub(r'\\\(\s*\\\)', '', s)
    # Remove \(plain text\) — text with no math symbols → unwrap to plain text
    def unwrap_non_math(m):
        inner = m.group(1)
        has_math = bool(re.search(r'[\\^_{}\[\]]', inner))
        return inner.strip() if not has_math else m.group(0)
    s = re.sub(r'\\\(([^\\$]{1,60}?)\\\)', unwrap_non_math, s)
    # Remove stray isolated \( or \) with nothing meaningful inside
    s = re.sub(r'\\\(\s*\\\)', '', s)
    return s

def format_question_text(text: str) -> str:
    if not text:
        return ""
    
    t = sanitize_latex(text)
    
    # Structure statements A., B., C., D.
    formatted_text = re.sub(r'\b([A-D]\.)\s', r'<br><br><span class="statement-label">\1</span> ', t)
    
    # Structure Statement I, Statement II, etc.
    formatted_text = re.sub(r'(Statement\s+[IVX]+:?)\s', r'<br><br><span class="statement-label">\1</span> ', formatted_text, flags=re.IGNORECASE)
    
    # Separate the final instructional text
    formatted_text = re.sub(r'(Choose the correct answer)', r'<br><br>\1', formatted_text, flags=re.IGNORECASE)
    
    return formatted_text

def clean_text(text: str) -> str:
    if not text:
        return ""
    # Fix double-escaped backslashes (common in DBs)
    text = text.replace('\\\\', '\\')
    # Replace newlines with spaces and strip
    return text.replace('\n', ' ').replace('\r', '').strip()

def is_truth_table(raw_text: str) -> bool:
    tokens = raw_text.split()
    if not tokens or len(tokens) < 6:
        return False
        
    header = []
    body = []
    
    for token in tokens:
        if token in ('0', '1'):
            body.append(token)
        else:
            if len(body) > 0:
                return False
            header.append(token)
            
    if len(header) < 2 or len(header) > 5:
        return False
        
    if len(body) == 0 or len(body) % len(header) != 0:
        return False
        
    for h in header:
        if len(h) > 3 or not h.isalnum():
            return False
            
    return True

def format_truth_table(raw_text: str) -> str:
    tokens = raw_text.split()
    header = []
    body = []
    for token in tokens:
        if token in ('0', '1'):
            body.append(token)
        else:
            header.append(token)
            
    cols = len(header)
    
    html = '<table class="truth-table" style="margin: 0 auto; text-align: center; border-collapse: collapse; min-width: 120px;">'
    html += '<tr style="border-bottom: 1px solid var(--border-hi);">'
    for h in header:
        html += f'<th style="padding: 4px 12px;">{h}</th>'
    html += '</tr>'
    
    for i in range(0, len(body), cols):
        row = body[i:i+cols]
        html += '<tr>'
        for c in row:
            html += f'<td style="padding: 2px 12px; color: var(--text);">{c}</td>'
        html += '</tr>'
        
    html += '</table>'
    return html

def format_question(row) -> dict:
    try:
        opts = safe_json(row["options"])
        if opts is None:
            logger.error(f"⚠️ Question ID {row['id']} has NULL options in DB.")
            opts = {"A": "Missing", "B": "Missing", "C": "Missing", "D": "Missing"}
        elif isinstance(opts, dict):
            cleaned_opts = {}
            for k, v in opts.items():
                val = clean_text(str(v))
                if is_truth_table(val):
                    val = format_truth_table(val)
                cleaned_opts[k] = val
            opts = cleaned_opts
            if all(not v for v in opts.values()):
                opts = {k: "N/A" for k in opts.keys()}
        else:
            opts = {"A": "N/A", "B": "N/A", "C": "N/A", "D": "N/A"}
    except Exception as e:
        logger.error(f"❌ JSON Parse Error for ID {row['id']}: {e}")
        logger.error(f"RAW DATA: {row.get('options')}")
        opts = {"A": "Parse Error", "B": "Parse Error", "C": "Parse Error", "D": "Parse Error"}

    SUPABASE_BASE = "https://dmfvojxpcxqndfudwhmy.supabase.co/storage/v1/object/public/question-images"

    def to_supabase_url(path):
        if not path:
            return None
        path = str(path).strip()
        if path.startswith("http"):
            return path
        filename = os.path.basename(path)
        return f"{SUPABASE_BASE}/{filename}"

    image_url = to_supabase_url(row.get("image_path"))
    solution_image_url = to_supabase_url(row.get("solution_image_path"))

    # Determine if we have valid discrete options
    has_valid_opts = False
    for k in ['A', 'B', 'C', 'D']:
        if opts.get(k) and opts[k] not in ("N/A", "Missing", "Parse Error"):
            has_valid_opts = True
            break

    options_image_url = None
    if not has_valid_opts:
        if row.get("options_image"):
            options_image_url = to_supabase_url(row["options_image"])

    parsed_match = None
    try:
        from match_list_parser import parse_match_list
        parsed_match = parse_match_list(row.get("question_text", ""))
    except Exception as e:
        logger.error(f"Match list parser error for {row['id']}: {e}")

    return {
        "id":                  row["id"],
        "subject":             row["subject"],
        "chapter":             row["chapter"],
        "year":                row["year"],
        "paper":               row["paper"],
        "question_text":       format_question_text(row.get("question_text") or ""),
        "match_list_parsed":   parsed_match,
        "options":             opts,
        "correct_answer":      row["correct_answer"],
        "solution":            clean_solution(row["solution"]),
        "image_url":           image_url,
        "options_image_url":   options_image_url,
        "solution_image_url":  solution_image_url,
        "data_quality":        row["data_quality"],
    }


@router.get("/questions/{chapter_id}")
def get_questions(
    chapter_id: str = Path(..., description="Chapter slug e.g. 'electrostatics'"),
    year:  Optional[int] = Query(None),
    page:  int           = Query(1, ge=1),
    limit: int           = Query(20, ge=1, le=100),
):
    offset = (page - 1) * limit

    try:
        with db_cursor() as cur:
            # Total count
            if year:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM neet_pyqs WHERE chapter = %s AND year = %s",
                    (chapter_id, year)
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM neet_pyqs WHERE chapter = %s",
                    (chapter_id,)
                )
            total = cur.fetchone()["cnt"]

            # Paginated questions
            if year:
                cur.execute("""
                    SELECT id, subject, chapter, year, paper, question_text,
                           options, correct_answer, solution,
                           image_path, solution_image_path, data_quality,
                           options_image
                    FROM neet_pyqs
                    WHERE chapter = %s AND year = %s
                    ORDER BY year DESC, id
                    LIMIT %s OFFSET %s
                """, (chapter_id, year, limit, offset))
            else:
                cur.execute("""
                    SELECT id, subject, chapter, year, paper, question_text,
                           options, correct_answer, solution,
                           image_path, solution_image_path, data_quality,
                           options_image
                    FROM neet_pyqs
                    WHERE chapter = %s
                    ORDER BY year DESC, id
                    LIMIT %s OFFSET %s
                """, (chapter_id, limit, offset))
            rows = cur.fetchall()

            # Distinct years for the filter dropdown
            cur.execute(
                "SELECT DISTINCT year FROM neet_pyqs WHERE chapter = %s ORDER BY year DESC",
                (chapter_id,)
            )
            years = [r["year"] for r in cur.fetchall() if r["year"]]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")


    pages = -(-total // limit)  # ceiling division
    return {
        "chapter":   chapter_id,
        "total":     total,
        "page":      page,
        "limit":     limit,
        "pages":     pages,
        "years":     years,
        "questions": [format_question(r) for r in rows],
    }


@router.get("/questions/{chapter_id}/{index}")
def get_question_by_index(
    chapter_id: str = Path(...),
    index: int = Path(..., ge=0),
    year: Optional[int] = Query(None),
):
    """
    Return a single question by 0-based index within a chapter (optionally filtered by year).
    Used by practice.html JS: GET /api/questions/{chapter}/{index}
    Response: { total, index, question }
    """
    try:
        with db_cursor() as cur:
            # Total count for this chapter (+ optional year filter)
            if year:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM neet_pyqs WHERE chapter = %s AND year = %s",
                    (chapter_id, year)
                )
            else:
                cur.execute(
                    "SELECT COUNT(*) AS cnt FROM neet_pyqs WHERE chapter = %s",
                    (chapter_id,)
                )
            total = cur.fetchone()["cnt"]

            if total == 0:
                raise HTTPException(status_code=404, detail="No questions found for this chapter.")
            if index >= total:
                raise HTTPException(status_code=404, detail=f"Index {index} out of range (total={total}).")

            # Fetch the single row at this offset
            if year:
                cur.execute("""
                    SELECT id, subject, chapter, year, paper, question_text,
                           options, correct_answer, solution,
                           image_path, solution_image_path, data_quality, options_image
                    FROM neet_pyqs
                    WHERE chapter = %s AND year = %s
                    ORDER BY year DESC, id
                    LIMIT 1 OFFSET %s
                """, (chapter_id, year, index))
            else:
                cur.execute("""
                    SELECT id, subject, chapter, year, paper, question_text,
                           options, correct_answer, solution,
                           image_path, solution_image_path, data_quality, options_image
                    FROM neet_pyqs
                    WHERE chapter = %s
                    ORDER BY year DESC, id
                    LIMIT 1 OFFSET %s
                """, (chapter_id, index))

            row = cur.fetchone()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    return {
        "total":    total,
        "index":    index,
        "question": format_question(row),
    }
