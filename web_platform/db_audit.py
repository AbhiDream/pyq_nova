import psycopg2
import json, os, re

conn = psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur = conn.cursor()

# Find questions with all-blank options
cur.execute("""
    SELECT id, question_text, image_path, solution_image_path,
           options, correct_answer, chapter
    FROM neet_pyqs
    WHERE options::text = '{"A": "", "B": "", "C": "", "D": ""}'
       OR options::text = '{"A":"","B":"","C":"","D":""}'
    LIMIT 10
""")
rows = cur.fetchall()
print(f"Found {len(rows)} questions with all-blank options.\n")

IMAGES_DIR = r"C:\Users\abhid\Desktop\neet_scrap\examside_data\images"

for r in rows:
    qid, qtext, img_path, sol_img_path, opts, correct, chapter = r
    print(f"ID: {qid}  Chapter: {chapter}  Correct: {correct}")
    print(f"  image_path: {img_path}")
    print(f"  solution_image_path: {sol_img_path}")
    # Check if filesystem has _opt images
    for ext in ['.png','.jpg','.jpeg']:
        fname = os.path.join(IMAGES_DIR, f"{qid}_opt{ext}")
        if os.path.exists(fname):
            print(f"  [FOUND] opt image: {fname}")
        for key in ['A','B','C','D']:
            fname2 = os.path.join(IMAGES_DIR, f"{qid}_opt_{key}{ext}")
            if os.path.exists(fname2):
                print(f"  [FOUND] per-option image: {fname2}")
    print()
