import re

def is_truth_table(raw_text: str) -> bool:
    # After clean_text, it might look like "A B Y 0 0 0 0 1 1 1 0 1 1 1 1"
    # But wait, what if we run it before clean_text or after?
    # If we run it after clean_text:
    tokens = raw_text.split()
    if not tokens:
        return False
    
    # Truth table header is usually all letters, and the body is all 0s and 1s
    # Let's find where the 0s and 1s start.
    header = []
    body = []
    for token in tokens:
        if token in ('0', '1'):
            body.append(token)
        else:
            # If we already started body, but found a non 0/1, maybe it's not a simple truth table
            if len(body) > 0:
                return False
            header.append(token)
            
    if len(header) < 2 or len(header) > 4:
        return False
        
    if len(body) == 0 or len(body) % len(header) != 0:
        return False
        
    return True

def format_truth_table(raw_text: str) -> str:
    tokens = raw_text.split()
    header = []
    body = []
    for token in tokens:
        if token in ('0', '1'):
            body.append(token)
        else:
            header.append(token)
            
    cols = len(header)
    
    html = '<table class="truth-table">'
    html += '<tr>' + ''.join(f'<th>{h}</th>' for h in header) + '</tr>'
    
    for i in range(0, len(body), cols):
        row = body[i:i+cols]
        html += '<tr>' + ''.join(f'<td>{c}</td>' for c in row) + '</tr>'
        
    html += '</table>'
    return html

text = "A B Y 0 0 0 0 1 1 1 0 1 1 1 1"
if is_truth_table(text):
    print(format_truth_table(text))

text2 = "A B C Y 0 0 0 0 0 0 1 1 0 1 0 0 0 1 1 1 1 0 0 0 1 0 1 1 1 1 0 0 1 1 1 1"
if is_truth_table(text2):
    print(format_truth_table(text2))

