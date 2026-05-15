"""
fix_blank_options.py
────────────────────
Finds every question in neet_pyqs that has all-blank options {"A":"","B":"","C":"","D":""}
and a corresponding _opt.png / _opt.jpg on disk, then updates the DB:

  • Writes the image filename (e.g. "moubbxtq_opt.png") into a new column
    `options_image` (TEXT, nullable).
  • Does NOT touch the original `options` JSONB column (safe to re-run).

Run once from web_platform/ directory:
    python fix_blank_options.py

After running, restart uvicorn so questions.py picks up the new column.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

# ── Config ──────────────────────────────────────────────────────────────────
DB = dict(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', '..', 'neet_scrap', 'examside_data', 'images')
IMAGES_DIR = os.path.normpath(IMAGES_DIR)

BLANK_OPTIONS = ('{"A": "", "B": "", "C": "", "D": ""}',
                 '{"A":"","B":"","C":"","D":""}')

def find_opt_image(qid: str) -> str | None:
    """Return just the filename (e.g. 'moubbxtq_opt.png') or None."""
    for ext in ('.png', '.jpg', '.jpeg'):
        fname = f"{qid}_opt{ext}"
        if os.path.exists(os.path.join(IMAGES_DIR, fname)):
            return fname
    return None

def main():
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Step 1: Create the new column if it doesn't already exist
    cur.execute("""
        ALTER TABLE neet_pyqs
        ADD COLUMN IF NOT EXISTS options_image TEXT DEFAULT NULL;
    """)
    print("[INFO] Ensured `options_image` column exists.")

    # Step 2: Fetch all blank-option rows
    cur.execute("""
        SELECT id, options::text AS opts_text
        FROM neet_pyqs
        WHERE (options::text = %s OR options::text = %s)
    """, BLANK_OPTIONS)
    rows = cur.fetchall()
    print(f"[INFO] Found {len(rows)} questions with all-blank options.")

    updated = 0
    missing = 0
    for row in rows:
        qid = row['id']
        fname = find_opt_image(qid)
        if fname:
            cur.execute(
                "UPDATE neet_pyqs SET options_image = %s WHERE id = %s",
                (fname, qid)
            )
            updated += 1
        else:
            missing += 1
            print(f"  [WARN] No opt image found on disk for: {qid}")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n[DONE] Updated {updated} rows. {missing} had no image on disk.")
    if missing:
        print("       Those rows still have options_image = NULL (correct fallback).")

if __name__ == '__main__':
    main()
