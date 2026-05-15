import requests
import json
try:
    r = requests.get('http://127.0.0.1:8000/api/questions/semiconductor-electronics')
    with open('api_response.json', 'w') as f:
        json.dump(r.json(), f, indent=2)
    print("Success")
except Exception as e:
    print(f"Error: {e}")
