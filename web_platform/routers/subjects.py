from fastapi import APIRouter, HTTPException
from database import db_cursor
from config import SUBJECT_META

router = APIRouter(prefix="/api", tags=["Subjects"])


@router.get("/subjects")
def get_subjects():
    """Return all distinct subjects with question counts and display metadata."""
    try:
        with db_cursor() as cur:
            cur.execute("""
                SELECT subject, COUNT(*) AS count
                FROM neet_pyqs
                GROUP BY subject
                ORDER BY subject
            """)
            rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    result = []
    for row in rows:
        slug = (row["subject"] or "").lower()
        meta = SUBJECT_META.get(slug, {
            "name": slug.title(), "icon": "📚",
            "color": "#94A3B8", "bg": "rgba(148,163,184,0.08)"
        })
        result.append({
            "slug":  slug,
            "name":  meta["name"],
            "icon":  meta["icon"],
            "color": meta["color"],
            "bg":    meta["bg"],
            "count": row["count"],
        })

    return {"subjects": result, "total": sum(r["count"] for r in result)}
