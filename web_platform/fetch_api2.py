import requests
import json
try:
    r = requests.get('http://127.0.0.1:8000/api/questions/semiconductor-electronics')
    print(json.dumps(r.json(), indent=2)[:2000])
except Exception as e:
    print(f"Error: {e}")
