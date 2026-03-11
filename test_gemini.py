import requests, json, os

api_key = os.environ.get('GEMINI_API_KEY', '')
if not api_key:
    print("ERROR: Set GEMINI_API_KEY environment variable first!")
    print("  Windows CMD:  set GEMINI_API_KEY=your-key-here")
    print("  PowerShell:   $env:GEMINI_API_KEY='your-key-here'")
    exit(1)
url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}'
payload = {
    'contents': [{'role': 'user', 'parts': [{'text': 'Hello'}]}],
    'generationConfig': {'temperature': 0.7, 'maxOutputTokens': 50}
}
try:
    r = requests.post(url, json=payload, headers={'Content-Type': 'application/json'}, timeout=30)
    print('Status:', r.status_code)
    data = r.json()
    print('Response:', json.dumps(data, indent=2, ensure_ascii=False)[:1500])
except Exception as e:
    print('Error:', e)
