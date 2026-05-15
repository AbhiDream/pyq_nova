from fastapi import APIRouter, HTTPException, Path
from database import db_cursor
from config import SUBJECT_META

router = APIRouter(prefix="/api", tags=["Chapters"])


def slug_to_title(slug: str) -> str:
    stop_words = {"and", "of", "in", "the", "a", "an", "its", "at", "to", "for"}
    parts = slug.replace("-", " ").split()
    return " ".join(
        w.capitalize() if (i == 0 or w not in stop_words) else w
        for i, w in enumerate(parts)
    )


@router.get("/chapters/{subject}")
def get_chapters(
    subject: str = Path(..., description="Subject slug: physics | chemistry | biology"),
):
    subject = subject.lower()
    if subject not in SUBJECT_META:
        raise HTTPException(status_code=404, detail=f"Subject '{subject}' not found.")

    try:
        with db_cursor() as cur:
            cur.execute("SELECT MAX(year) FROM neet_pyqs WHERE year <= 2030")
            max_year_row = cur.fetchone()
            max_year = max_year_row["max"] if max_year_row and max_year_row["max"] else 2026
            
            year_10_start = max_year - 9
            year_3_start = max_year - 2

            cur.execute("""
                SELECT chapter, 
                       COUNT(*) AS total_count,
                       COUNT(*) FILTER (WHERE year >= %s) AS count_10yr,
                       COUNT(*) FILTER (WHERE year >= %s) AS count_3yr,
                       COUNT(DISTINCT year) FILTER (WHERE year >= %s) AS consistency_years
                FROM neet_pyqs
                WHERE LOWER(subject) = %s
                GROUP BY chapter
                ORDER BY total_count DESC
            """, (year_10_start, year_3_start, year_10_start, subject))
            rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    chapters = []
    for row in rows:
        total_count = row["total_count"]
        count_10yr = row["count_10yr"] or 0
        count_3yr = row["count_3yr"] or 0
        consistency_years = row["consistency_years"] or 0

        avg_10yr = count_10yr / 10.0
        avg_3yr = count_3yr / 3.0
        
        final_score = (0.60 * avg_10yr) + (0.25 * avg_3yr) + (0.15 * consistency_years)

        chapters.append({
            "slug": row["chapter"], 
            "name": slug_to_title(row["chapter"]), 
            "count": total_count,
            "max_year": max_year,
            "final_score": round(final_score, 2)
        })

    # Sort by composite score to apply percentile ranking
    chapters.sort(key=lambda x: x["final_score"], reverse=True)

    # Assign percentile-based categories (per subject)
    N = len(chapters)
    if N > 0:
        num_high = max(1, round(0.28 * N))  # ~28% High
        num_low = max(1, round(0.17 * N))   # ~17% Low
        
        for i, c in enumerate(chapters):
            if i < num_high:
                c["weightage"] = "High Weightage"
            elif i >= N - num_low:
                c["weightage"] = "Low Weightage"
            else:
                c["weightage"] = "Medium Weightage"

    meta = SUBJECT_META[subject]
    return {
        "subject":       subject,
        "subject_name":  meta["name"],
        "subject_icon":  meta["icon"],
        "subject_color": meta["color"],
        "total":         sum(c["count"] for c in chapters),
        "chapters":      chapters,
    }
