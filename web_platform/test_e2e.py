"""
Quick test of the new get_question_by_index logic:
Simulates what the route does and prints key fields.
"""
import sys; sys.path.insert(0, '.')
from database import create_pool, db_cursor
from routers.questions import format_question

create_pool()  # must call before db_cursor

CHAPTER = "Semiconductor Electronics"
INDEX   = 1  # the blank-options question

with db_cursor() as cur:
    cur.execute("SELECT COUNT(*) AS cnt FROM neet_pyqs WHERE chapter = %s", (CHAPTER,))
    total = cur.fetchone()["cnt"]

    cur.execute("""
        SELECT id, subject, chapter, year, paper, question_text,
               options, correct_answer, solution,
               image_path, solution_image_path, data_quality, options_image
        FROM neet_pyqs
        WHERE chapter = %s
        ORDER BY year DESC, id
        LIMIT 1 OFFSET %s
    """, (CHAPTER, INDEX))
    row = cur.fetchone()

q = format_question(row)

print(f"total            : {total}")
print(f"id               : {q['id']}")
print(f"year             : {q['year']}")
print(f"question_text    : {q['question_text'][:80]}")
print(f"options          : {q['options']}")
print(f"image_url        : {q['image_url']}")
print(f"options_image_url: {q['options_image_url']}")
print(f"solution_image   : {q['solution_image_url']}")
print(f"correct_answer   : {q['correct_answer']}")
