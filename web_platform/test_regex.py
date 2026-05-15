import re

text = "$$ \\text { In the circuit shown below, the voltage appearing across the diode } D \\text { will be of the form: } $$"

def clean_latex_title(t):
    # Replace outer $$ with nothing if it starts and ends with $$
    t = t.strip()
    if t.startswith('$$') and t.endswith('$$'):
        # Just convert it to inline math to avoid block centering?
        # Or remove $$ and then we have \text{...} which is bad.
        pass

    # A better approach: replace \text{ ... } with its content
    # But then what about variables like D? They would be left bare. We should wrap them in $ $.
    # Let's just replace outer $$ with nothing, then we need to handle \text{}.
    return t

def better_clean(t):
    t = t.strip()
    if t.startswith('$$') and t.endswith('$$'):
        inner = t[2:-2].strip()
        # Find all \text{...} and replace with just the text.
        # But wait! Anything NOT inside \text{...} was math. So it should be wrapped in $...$.
        # This is tricky because \text{} can contain escaped braces.
        
        # Alternative: Just replace $$ with $ so it's inline math.
        return f"${inner}$"
    return t

print(better_clean(text))
