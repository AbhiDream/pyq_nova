import re

def sanitize_latex(raw: str) -> str:
    if not raw:
        return raw
    result = raw.strip()
    
    # 1. Strip outer $$ ... $$ or $ ... $
    if result.startswith('$$') and result.endswith('$$'):
        result = result[2:-2].strip()
    elif result.startswith('$') and result.endswith('$'):
        result = result[1:-1].strip()
        
    # 2. Flatten all \text{ ... } blocks
    # We replace \text{anything} with anything
    # This non-greedy match works: \\text\s*\{\s*(.*?)\s*\}
    result = re.sub(r'\\text\s*\{\s*(.*?)\s*\}', r'\1', result)
    
    # 3. Orphaned $$
    result = re.sub(r'\$\$\s*\$\$', '', result)
    
    return result.strip()

print(sanitize_latex("$$ \\text { In the circuit shown below, the voltage appearing across the diode } D \\text { will be of the form: } $$"))
