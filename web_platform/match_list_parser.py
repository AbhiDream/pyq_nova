"""
match_list_parser.py
======================================================================
Handles ALL match-list format variations found in neet_pyqs:

  1.  $$ \text { Match List I with List II } $$   (LaTeX heading)
  2.  Match List I with List II.                  (plain, keys A. I.)
  3.  Match List-I with List-II                   (hyphenated, keys (a) (i))
  4.  Match the reagents (List-I) with ...        (descriptive)
  5.  Match the following :                        (generic)
  6.  Keys without trailing dot  A  I  (no period)

Returns a structured dict that the Jinja template renders as a
clean 2-column table.  Returns None for non-match questions.

Usage (FastAPI):
    from match_list_parser import parse_match_list

    @app.get("/api/questions/{chapter}")
    async def get_questions(chapter: str, ...):
        questions = db_fetch(...)
        for q in questions:
            q["match_list_parsed"] = parse_match_list(q["question_text"])
        return questions
======================================================================
"""

import re
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Detection
# ─────────────────────────────────────────────────────────────────────────────

# All heading patterns that signal a match-list question
_HEADING_PATTERNS = [
    r'\$\$\s*\\text\s*\{[^}]*[Mm]atch[^}]*\}\s*\$\$',   # $$ \text{Match...} $$
    r'[Mm]atch\s+(?:the\s+)?[Ll]ist',                    # Match List / Match the List
    r'[Mm]atch\s+(?:the\s+)?(?:following|reagents|compounds|items)',
    r'[Mm]atch\s+[Ll]ist-?I',
]
_HEADING_RE = re.compile('|'.join(_HEADING_PATTERNS))


def is_match_list(text: str) -> bool:
    return bool(_HEADING_RE.search(text or ''))


# ─────────────────────────────────────────────────────────────────────────────
# Key patterns  —  all real variations seen in CSV
# ─────────────────────────────────────────────────────────────────────────────

# List-I keys:   A.   (a)   (A)   A   (with or without trailing dot/paren)
_L1_KEY_RE = re.compile(
    r'^(?:\(([A-Da-d])\)|([A-Da-d])\.?\s*)$'
)

# List-II keys:  I.   (i)   (I)   (ii)  II  etc.
_L2_KEY_RE = re.compile(
    r'^(?:\(([IiVv]{1,4})\)|([IiVv]{1,4})\.?\s*)$'
)

# List-I / List-II header line variants
_COL1_RE = re.compile(r'^List\s*[-\s]?\s*I\b', re.IGNORECASE)
_COL2_RE = re.compile(r'^List\s*[-\s]?\s*II\b', re.IGNORECASE)


def _is_l1_key(s: str) -> bool:
    return bool(_L1_KEY_RE.match(s.strip()))


def _is_l2_key(s: str) -> bool:
    return bool(_L2_KEY_RE.match(s.strip()))


def _normalize_key(s: str) -> str:
    """'(a)' -> 'a',  'A.' -> 'A',  'A' -> 'A',  '(III)' -> 'III'"""
    s = s.strip()
    m = re.match(r'^\(([A-Za-zIViv]+)\)$', s)
    if m:
        return m.group(1).upper()
    return s.rstrip('. ').upper()


# ─────────────────────────────────────────────────────────────────────────────
# Heading extractor
# ─────────────────────────────────────────────────────────────────────────────

def _clean_heading(raw: str) -> str:
    """
    '$$ \\text { Match List I with List II : } $$'
      -> 'Match List I with List II'

    'Match the reagents (List-I) with the product (List-II) obtained from phenol.'
      -> 'Match the reagents (List-I) with the product (List-II) obtained from phenol.'
    """
    # Remove LaTeX $$ \text{...} $$ wrapper
    s = re.sub(r'\$\$\s*\\text\s*\{([^}]*)\}\s*\$\$', lambda m: m.group(1), raw)
    # Remove standalone $$ markers
    s = re.sub(r'\$\$', '', s)
    return s.strip(' :')


# ─────────────────────────────────────────────────────────────────────────────
# Main parser
# ─────────────────────────────────────────────────────────────────────────────

def parse_match_list(question_text: str) -> Optional[dict]:
    """
    Returns structured dict or None.

    Return shape:
    {
        "heading":     "Match List I with List II",
        "col1_header": "(Order of reaction)",   # may be ""
        "col2_header": "(Unit of rate constant)",
        "rows": [
            {"left_key": "A", "left_val": "Zero order",
             "right_key": "I", "right_val": "$\\mathrm{mol}^{-1}...$"},
            ...
        ],
        "footer": "Choose the correct answer from the options given below :"
    }
    """
    if not is_match_list(question_text):
        return None

    # ── Normalize whitespace variants to newlines ──────────────────────────
    import re
    text = question_text
    text = re.sub(r'<br\s*/?>', '\n', text)      # <br> tags
    text = re.sub(r'\t+', '\n', text)            # tabs
    text = re.sub(r' {4,}', '\n', text)          # 4+ consecutive spaces

    # ── Tokenize: split on newlines, strip blanks ──────────────────────────
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # ── Extract heading (everything before first "List" column header) ──────
    heading_lines = []
    list_start_idx = 0

    for i, line in enumerate(lines):
        if _COL1_RE.match(line) or _COL2_RE.match(line):
            list_start_idx = i
            break
        heading_lines.append(line)
    else:
        # No column headers found — might be an image-based question
        # Still try to extract rows from key pattern
        list_start_idx = 0

    # Build heading from all pre-List lines
    raw_heading = ' '.join(heading_lines)
    heading = _clean_heading(raw_heading)

    # ── Parse column headers ───────────────────────────────────────────────
    col1_header = ''
    col2_header = ''
    parse_start = list_start_idx

    remaining = lines[list_start_idx:]
    i = 0

    # Consume:  List-I \n (header) \n List-II \n (header)
    # or just:  List-I \n List-II  (no sub-headers)
    if i < len(remaining) and _COL1_RE.match(remaining[i]):
        i += 1  # skip "List I"
        # Next line: sub-header or List-II
        if i < len(remaining) and not _COL2_RE.match(remaining[i]) \
                and not _is_l1_key(remaining[i]) and not _is_l2_key(remaining[i]):
            col1_header = remaining[i]
            i += 1
    if i < len(remaining) and _COL2_RE.match(remaining[i]):
        i += 1  # skip "List II"
        if i < len(remaining) and not _is_l1_key(remaining[i]) \
                and not _is_l2_key(remaining[i]) \
                and not remaining[i].startswith('Choose'):
            col2_header = remaining[i]
            i += 1

    # ── Parse rows ─────────────────────────────────────────────────────────
    list1: list[dict] = []   # [{"key": "A", "val": "Zero order"}, ...]
    list2: list[dict] = []

    footer = ''
    pending_key  = None
    pending_side = None   # 'L1' or 'L2'

    def flush(val_line: str):
        nonlocal pending_key, pending_side
        if pending_side == 'L1':
            list1.append({"key": pending_key, "val": val_line})
        elif pending_side == 'L2':
            list2.append({"key": pending_key, "val": val_line})
        pending_key = pending_side = None

    val_buffer: list[str] = []

    def flush_buffer():
        if pending_key and val_buffer:
            flush(' '.join(val_buffer))
            val_buffer.clear()

    while i < len(remaining):
        line = remaining[i]
        i += 1

        # Footer line
        if re.match(r'^[Cc]hoose\s+the\s+correct', line):
            flush_buffer()
            footer = line
            break

        # List-I key
        if _is_l1_key(line):
            flush_buffer()
            pending_key  = _normalize_key(line)
            pending_side = 'L1'
            val_buffer.clear()
            continue

        # List-II key
        if _is_l2_key(line):
            flush_buffer()
            pending_key  = _normalize_key(line)
            pending_side = 'L2'
            val_buffer.clear()
            continue

        # Value line (accumulate — some values span multiple lines)
        if pending_key:
            val_buffer.append(line)

    # Flush any remaining buffered value
    flush_buffer()

    # ── Build rows: zip list1 and list2 by index ───────────────────────────
    max_rows = max(len(list1), len(list2), 1)
    rows = []
    for j in range(max_rows):
        rows.append({
            "left_key":  list1[j]["key"] if j < len(list1) else "",
            "left_val":  list1[j]["val"] if j < len(list1) else "",
            "right_key": list2[j]["key"] if j < len(list2) else "",
            "right_val": list2[j]["val"] if j < len(list2) else "",
        })

    # ── Guard: if we got nothing, return None (don't show empty table) ──────
    has_data = any(r["left_val"] or r["right_val"] for r in rows)
    if not has_data:
        return None

    return {
        "heading":     heading,
        "col1_header": col1_header,
        "col2_header": col2_header,
        "rows":        rows,
        "footer":      footer,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Quick self-test  (python match_list_parser.py)
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import json

    samples = [
        # Format 1 — LaTeX heading, A/I keys
        """$$ \\text { Match List I with List II : } $$
List-I
(Order of reaction)
List-II
(Unit of rate constant)
A.
Zero order
I.
$\\mathrm{mol}^{-1} \\mathrm{~L} \\mathrm{~s}^{-1}$
B.
First order
II.
$\\mathrm{mol}^{-2} \\mathrm{~L}^2 \\mathrm{~s}^{-1}$
C.
Second order
III.
$\\mathrm{s}^{-1}$
D.
Third order
IV.
$\\mathrm{mol} \\mathrm{L}^{-1} \\mathrm{~s}^{-1}$
Choose the correct answer from the options given below :""",

        # Format 2 — (a)/(i) keys with descriptive heading
        """Match the reagents (List-I) with the product (List-II) obtained from phenol.
List-I
List-II
(a)
(i) NaOH (ii) CO2
(i)
Benzoquinone
(b)
Aqueous NaOH + CHCl3
(ii)
Benzene
Choose the correct answer from the options given below :""",

        # Format 3 — no trailing dot on keys
        """Match List-I with List-II
List - I
List - II
A
The Evil Quartet
I
Cryopreservation
B
Ex situ conservation
II
Alien species invasion
Choose the correct answer from the options given below :""",

        # Format 4 — Match the following
        """Match the following :
List-I
List-II
(a)
Physalia
(i)
Pearl oyster
(b)
Limulus
(ii)
Portuguese Man of War
(c)
Ancylostoma
(iii)
Living fossil
Choose the correct answer from the options given below :""",
    ]

    for idx, s in enumerate(samples, 1):
        result = parse_match_list(s)
        print(f"\n{'='*60}")
        print(f"Sample {idx}:")
        if result:
            print(f"  Heading:     {result['heading']}")
            print(f"  Col1 header: {result['col1_header']}")
            print(f"  Col2 header: {result['col2_header']}")
            for r in result['rows']:
                print(f"  {r['left_key']:4} {r['left_val'][:30]:30} | {r['right_key']:4} {r['right_val'][:30]}")
        else:
            print("  -> None (not a match list)")
