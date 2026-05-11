from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import requests

API = 'http://127.0.0.1:8000'

payload = {'student_id': '20260001', 'question': '校园卡丢了应该怎么补办？'}
r = requests.post(f'{API}/api/questions', json=payload, timeout=120)
print(r.status_code, r.json())
qid = r.json()['question_id']
r = requests.get(f'{API}/api/questions/{qid}', params={'student_id': payload['student_id']}, timeout=30)
print(r.status_code, r.json())
