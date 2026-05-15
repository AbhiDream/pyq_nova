import httpx, json

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'application/json',
    'Referer': 'https://questions.examside.com/'
}

def decode_svelte_devalue(arr):
    resolved = {}
    def walk(idx):
        if not isinstance(idx, int) or idx < 0 or idx >= len(arr): return idx
        if idx in resolved: return resolved[idx]
        val = arr[idx]
        if isinstance(val, dict):
            obj = {}; resolved[idx] = obj
            for k, v in val.items(): obj[k] = walk(v)
            return obj
        elif isinstance(val, list):
            lst = []; resolved[idx] = lst
            for v in val: lst.append(walk(v))
            return lst
        else:
            resolved[idx] = val; return val
    return walk(0)

q_id = 'bCJXwHgAjG2mc7ziP7NjG'
url = f'https://questions.examside.com/past-years/medical/question/{q_id}/__data.json?x-sveltekit-invalidated=11'
print('Testing:', url)

c = httpx.Client(http2=True, headers=HEADERS, follow_redirects=True)
r = c.get(url, timeout=20)
print('Status:', r.status_code)
d = r.json()
nodes = d.get('nodes', [])
print('Nodes:', len(nodes))

for i, node in enumerate(nodes):
    if node:
        ntype = node.get('type', '?')
        data = node.get('data', [])
        print(f'  Node {i}: type={ntype}, data_len={len(data)}')
        if ntype == 'data' and data:
            tree = decode_svelte_devalue(data)
            txt = json.dumps(tree)
            for kw in ['explanation', 'solution', 'en', 'question']:
                if kw in txt.lower():
                    idx = txt.lower().find(kw)
                    print(f'    HAS [{kw}]: ...{txt[max(0,idx-10):idx+200]}...')
                    break

c.close()
