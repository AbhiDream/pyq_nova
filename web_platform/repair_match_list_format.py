"""
repair_match_list_format.py
======================================================================
63 questions fix karta hai jahan List-I aur List-II tab/space separated
hain newline ke bajaye.

Problem format (DB mein):
    "Match the reagents...\tList-I\tList-II\t(a)\t(i) NaOH...\t(i)\tBenzoquinone"

Target format (parser ke liye):
    "Match the reagents...\nList-I\nList-II\n(a)\n(i) NaOH...\n(i)\nBenzoquinone"

Strategy:
    1. Tabs → newlines
    2. 4+ consecutive spaces → newlines  
    3. <br> tags → newlines
    4. Multiple blank lines → single blank line
    5. Verify parser can now parse it
    6. UPDATE DB

Run:
    python repair_match_list_format.py --dry-run   # preview only
    python repair_match_list_format.py             # actual DB update
======================================================================
"""

import argparse
import re
import json
import logging
import psycopg2
import psycopg2.extras

# Import your parser to verify fix works
try:
    from match_list_parser import parse_match_list
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    print("⚠ match_list_parser.py not found — will skip parse verification")

DB_PARAMS = {
    "host": "127.0.0.1",
    "dbname": "neet_db",
    "user": "postgres",
    "password": "Dream@1234",
    "port": "5432",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("repair_match_list_format.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Normalizer
# ─────────────────────────────────────────────────────────────────────────────

def normalize_to_newlines(text: str) -> str:
    """
    Converts all whitespace-based separators to newlines.
    Order matters — do <br> first, then tabs, then multi-spaces.
    """
    if not text:
        return text

    # 1. HTML line breaks
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # 2. Tabs → newline
    text = re.sub(r'\t+', '\n', text)

    # 3. 4+ consecutive spaces → newline
    #    (careful: LaTeX like $\mathrm{ mol }$ has spaces too, but < 4)
    text = re.sub(r' {4,}', '\n', text)

    # 4. Collapse 3+ consecutive newlines → 2
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 5. Strip trailing whitespace per line
    lines = [l.rstrip() for l in text.split('\n')]
    text = '\n'.join(lines)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Fetch broken records
# ─────────────────────────────────────────────────────────────────────────────

def fetch_broken(conn) -> list[dict]:
    """
    Fetch match-list questions where List-I and List-II are on same line
    (i.e., no newline between them — tab/space separated).
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            r"""
            SELECT id, question_text, chapter, subject
            FROM neet_pyqs
            WHERE question_text LIKE '%List-I%List-II%'
              AND question_text LIKE '%List%'
              AND (
                  -- Has tabs (tab-separated format)
                  question_text LIKE '%' || E'\t' || '%'
                  OR
                  -- List-I and List-II on same line (no newline between)
                  question_text ~ 'List[-\s]?I\s{3,}List[-\s]?II'
              )
            ORDER BY chapter, id
            """
        )
        rows = [dict(r) for r in cur.fetchall()]
    log.info(f"Found {len(rows)} broken match-list questions")
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Main repair
# ─────────────────────────────────────────────────────────────────────────────

def repair(dry_run: bool = False):
    conn = psycopg2.connect(**DB_PARAMS)
    try:
        broken = fetch_broken(conn)
        if not broken:
            log.info("No broken records found — nothing to do.")
            return

        repaired     = []
        parse_fixed  = []   # parser can now parse these
        parse_still_none = []  # normalized but parser still returns None (malformed data)

        for rec in broken:
            q_id     = rec["id"]
            original = rec["question_text"]
            fixed    = normalize_to_newlines(original)

            if fixed == original:
                log.debug(f"  [{q_id}] No change after normalization — skipping")
                continue

            # Verify parser can now handle it
            parse_result = None
            if PARSER_AVAILABLE:
                parse_result = parse_match_list(fixed)

            repaired.append({
                "id":       q_id,
                "original": original,
                "fixed":    fixed,
                "parsed":   parse_result is not None,
            })

            if parse_result:
                parse_fixed.append(q_id)
                log.info(
                    f"  ✅ [{q_id}] {rec['chapter']} — "
                    f"normalized + parser OK ({len(parse_result['rows'])} rows)"
                )
            else:
                parse_still_none.append(q_id)
                log.warning(
                    f"  ⚠ [{q_id}] {rec['chapter']} — "
                    f"normalized but parser still None (malformed data)"
                )

            if dry_run:
                # Print diff preview
                orig_lines = original.split('\n')
                fixed_lines = fixed.split('\n')
                print(f"\n{'─'*60}")
                print(f"ID: {q_id}  |  {rec['chapter']}")
                print(f"BEFORE ({len(orig_lines)} lines): {repr(original[:120])}")
                print(f"AFTER  ({len(fixed_lines)} lines): {repr(fixed[:120])}")

        log.info(f"\n{'='*60}")
        log.info(f"  Total processed : {len(repaired)}")
        log.info(f"  Parser OK       : {len(parse_fixed)}")
        log.info(f"  Still malformed : {len(parse_still_none)}")

        if parse_still_none:
            log.warning(f"  Still-malformed IDs: {parse_still_none}")
            # Save for manual review
            with open("still_malformed_match.txt", "w") as f:
                f.write('\n'.join(parse_still_none))
            log.warning("  → Saved to still_malformed_match.txt")

        if dry_run:
            log.info("  DRY-RUN — no DB changes made")
            return

        # ── Write to DB ────────────────────────────────────────────────────
        if not repaired:
            log.info("Nothing to update.")
            return

        with conn.cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                """
                UPDATE neet_pyqs
                SET question_text = %s
                WHERE id = %s
                """,
                [(r["fixed"], r["id"]) for r in repaired],
                page_size=50,
            )
        conn.commit()
        log.info(f"  ✅ Updated {len(repaired)} records in DB")

    except Exception as e:
        conn.rollback()
        log.error(f"Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fix tab-separated match-list questions in neet_pyqs"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing to DB"
    )
    args = parser.parse_args()
    repair(dry_run=args.dry_run)
