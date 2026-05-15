from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import JSONResponse
from database import db_cursor
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["progress"])

@router.post("/api/progress/upsert")
async def upsert_progress(request: Request, data: dict = Body(...)):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")

    question_id = data.get("question_id")
    status = data.get("status") # 'correct', 'wrong', 'skipped'
    selected_option = data.get("selected_option")

    if not question_id or not status:
        raise HTTPException(status_code=400, detail="Missing required fields")

    try:
        with db_cursor() as cur:
            cur.execute("""
                INSERT INTO user_progress (user_id, question_id, status, selected_option, last_attempt_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, question_id) DO UPDATE 
                SET status = EXCLUDED.status,
                    selected_option = EXCLUDED.selected_option,
                    last_attempt_at = NOW()
            """, (user["id"], question_id, status, selected_option))
        return JSONResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Error upserting progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/api/progress/sync")
async def sync_progress(request: Request, data: dict = Body(...)):
    """Batch sync from localStorage on first login."""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not logged in")

    progress_items = data.get("progress", [])
    if not progress_items:
        return JSONResponse({"status": "success", "message": "Nothing to sync"})

    try:
        with db_cursor() as cur:
            for item in progress_items:
                q_id = item.get("qId")
                status = item.get("status")
                selected = item.get("selected_option")
                if q_id and status:
                    cur.execute("""
                        INSERT INTO user_progress (user_id, question_id, status, selected_option, last_attempt_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT (user_id, question_id) DO UPDATE 
                        SET status = EXCLUDED.status,
                            selected_option = EXCLUDED.selected_option,
                            last_attempt_at = NOW()
                    """, (user["id"], q_id, status, selected))
        return JSONResponse({"status": "success"})
    except Exception as e:
        logger.error(f"Error syncing progress: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/progress/chapter/{chapter}")
async def get_chapter_progress(request: Request, chapter: str):
    user = request.session.get("user")
    if not user:
        return JSONResponse({"progress": {}})

    try:
        # We join with neet_questions to only get progress for this chapter
        with db_cursor() as cur:
            cur.execute("""
                SELECT p.question_id, p.status, p.selected_option 
                FROM user_progress p
                JOIN neet_questions q ON p.question_id = q.id
                WHERE p.user_id = %s AND q.chapter = %s
            """, (user["id"], chapter))
            rows = cur.fetchall()
            
        progress_dict = {}
        for row in rows:
            progress_dict[row["question_id"]] = {
                "status": row["status"],
                "selected_option": row["selected_option"]
            }
        return JSONResponse({"progress": progress_dict})
    except Exception as e:
        logger.error(f"Error fetching chapter progress: {e}")
        return JSONResponse({"progress": {}})
