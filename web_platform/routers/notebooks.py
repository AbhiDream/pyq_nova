from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from database import db_cursor

router = APIRouter(prefix="/api/notebooks", tags=["notebooks"])

class NotebookCreate(BaseModel):
    name: str
    color: str = "#1DD4C0"

class SaveQuestion(BaseModel):
    question_id: str
    notebook_ids: List[int]
    note: str = ""
    tags: List[str] = []

# GET all notebooks
@router.get("/")
def get_notebooks():
    with db_cursor() as cur:
        cur.execute("SELECT * FROM notebooks ORDER BY created_at DESC")
        return {"notebooks": [dict(r) for r in cur.fetchall()]}

# POST create notebook
@router.post("/")
def create_notebook(data: NotebookCreate):
    with db_cursor() as cur:
        cur.execute(
            "INSERT INTO notebooks (name, color) VALUES (%s, %s) RETURNING *",
            (data.name, data.color)
        )
        cur.connection.commit()
        return dict(cur.fetchone())

# DELETE notebook
@router.delete("/{notebook_id}")
def delete_notebook(notebook_id: int):
    with db_cursor() as cur:
        cur.execute("DELETE FROM notebooks WHERE id = %s", (notebook_id,))
        cur.connection.commit()
    return {"ok": True}

# POST save question to notebooks
@router.post("/save-question")
def save_question(data: SaveQuestion):
    with db_cursor() as cur:
        # Pehle purane entries delete karo (re-save on update)
        cur.execute(
            "DELETE FROM notebook_questions WHERE question_id = %s",
            (data.question_id,)
        )
        # Har selected notebook mein insert karo
        for nb_id in data.notebook_ids:
            cur.execute("""
                INSERT INTO notebook_questions (notebook_id, question_id, note, tags)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (notebook_id, question_id) DO UPDATE
                SET note = EXCLUDED.note, tags = EXCLUDED.tags
            """, (nb_id, data.question_id, data.note, data.tags))
        cur.connection.commit()
    return {"ok": True, "saved_to": len(data.notebook_ids)}

# GET check if question is saved (for bookmark icon state)
@router.get("/question/{question_id}")
def get_question_save_state(question_id: str):
    with db_cursor() as cur:
        cur.execute("""
            SELECT nq.*, n.name as notebook_name, n.color
            FROM notebook_questions nq
            JOIN notebooks n ON n.id = nq.notebook_id
            WHERE nq.question_id = %s
        """, (question_id,))
        rows = cur.fetchall()
    return {
        "saved": len(rows) > 0,
        "entries": [dict(r) for r in rows]
    }

# GET all saved questions (for notebooks page)
@router.get("/{notebook_id}/questions")
def get_notebook_questions(notebook_id: int):
    with db_cursor() as cur:
        cur.execute("""
            WITH ordered_qs AS (
                SELECT id, row_number() over (partition by chapter order by year desc, id) - 1 as global_index
                FROM neet_pyqs
            )
            SELECT nq.*, p.question_text, p.subject, p.chapter, p.year, 
                   p.correct_answer, p.options, oq.global_index
            FROM notebook_questions nq
            JOIN neet_pyqs p ON p.id = nq.question_id
            JOIN ordered_qs oq ON oq.id = p.id
            WHERE nq.notebook_id = %s
            ORDER BY nq.saved_at DESC
        """, (notebook_id,))
        rows = cur.fetchall()
        
        from match_list_parser import parse_match_list
        questions = []
        for r in rows:
            q = dict(r)
            q["match_list_parsed"] = parse_match_list(q["question_text"])
            questions.append(q)
            
        return {"questions": questions}
