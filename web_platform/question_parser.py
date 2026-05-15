import re

def parse_match_list(question_text: str) -> dict | None:
    if not question_text:
        return None
    if "Match List" not in question_text and "match list" not in question_text and "MatchList" not in question_text:
        return None

    lines = [l.strip() for l in question_text.split('\n') if l.strip()]

    # Extract heading
    heading = ""
    start_idx = 0
    for i, line in enumerate(lines):
        if line == "List-I" or "List-I" in line and len(line) < 15:
            start_idx = i
            break
        # Clean $$ \text { Match List I with List II : } $$
        clean = re.sub(r'\$\$.*?\$\$', '', line)
        clean = re.sub(r'\\text\s*\{([^}]*)\}', r'\1', clean).strip()
        if clean:
            heading = clean

    if start_idx == 0 and "List-I" not in lines[0]:
        return None  # Couldn't find List-I

    col1_header = col2_header = footer = ""
    list1, list2 = [], []

    i = start_idx
    state = "col1_header"

    while i < len(lines):
        line = lines[i]

        if state == "col1_header":
            # Might be List-I, skip it
            if "List-I" in line and len(line) < 15:
                i += 1
                continue
            col1_header = line
            state = "col2_label"

        elif state == "col2_label":
            if "List-II" in line:
                state = "col2_header"
            else:
                # Sometimes List-II is on the same line or next
                pass

        elif state == "col2_header":
            if "List-II" in line and len(line) < 15:
                i += 1
                continue
            col2_header = line
            state = "rows"

        elif state == "rows":
            if line.startswith("Choose the correct") or "Choose the correct" in line:
                footer = line
                break

            # List-I key: A. B. C. D.
            if re.match(r'^[A-D]\.$', line):
                key = line[:-1]
                val = lines[i + 1] if i + 1 < len(lines) else ""
                list1.append({"key": key, "val": val})
                i += 1

            # List-II key: I. II. III. IV.
            elif re.match(r'^(I{1,3}|IV|V?I{0,3})\.$', line):
                key = line[:-1]
                val = lines[i + 1] if i + 1 < len(lines) else ""
                list2.append({"key": key, "val": val})
                i += 1

        i += 1

    if not list1 and not list2:
        return None

    rows = []
    for j in range(max(len(list1), len(list2))):
        rows.append({
            "left_key":  list1[j]["key"] if j < len(list1) else "",
            "left_val":  list1[j]["val"] if j < len(list1) else "",
            "right_key": list2[j]["key"] if j < len(list2) else "",
            "right_val": list2[j]["val"] if j < len(list2) else "",
        })

    return {
        "type":        "match_list",
        "heading":     heading,
        "col1_header": col1_header,
        "col2_header": col2_header,
        "rows":        rows,
        "footer":      footer,
    }
