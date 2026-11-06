"""Backend-only user conversations; isolated database, optional real configured AI."""
import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from scripts.message_polling import TextPollingClient as TestClient
from app.main import create_app
from app.web import store

if '--live' not in sys.argv:
    raise SystemExit('Pass --live to exercise configured AI with synthetic text.')
out = Path('output/text-flow-review')
out.mkdir(parents=True, exist_ok=True)
results = []

scenarios = {
    'combined-after-prompt': ['9 feet', 'Sunny, mostly Netflix, all of us straight ahead, the old one sounds muffled, on a cabinet, around seventy thousand'],
    'correction-without-keywords': ['9 feet and bright sunlight', 'Actually make that twelve feet'],
    'text-demo-preference': ['9 feet, bright daylight, cricket, side seating, blurry old TV, wall mount, budget 70000 rupees', 'Correct', 'Demo A/B', 'Demo done', 'They preferred Samsung Vision Q55 because cricket motion looked smoother'],
    'all-seven-at-once': ['Viewing distance 9 feet. Bright daylight. Cricket and movies. Family sits on sides. Wants to fix motion blur. Wall mounting. Budget 70000 rupees.', 'Correct'],
    'two-answers-at-once': ['9 feet and bright sunlight falls on the screen'],
    'implicit-multiple-answers': ['About three metres, quite sunny, mostly Netflix, everyone straight ahead, the old one has muffled dialogue, mounted vertically, around seventy thousand'],
    'two-hand-lengths': ['2 hand lengths', 'I mean from the sofa to the TV. I have not measured it.'],
    'object-distance': ['About the length of that big cupboard'],
    'vague-everything': ['Not far, fairly bright, usual stuff, everyone together, want something better, on that thing, not too expensive'],
    'unknown-distance': ["I don't know the distance", 'Bright daylight and mostly cricket'],
    'mixed-vague-and-known': ['Distance is about 2 hand lengths, sunny room, cricket and films, side seats, old TV is blurry, wall mount, budget 60k'],
    'correction': ['9 feet and bright daylight, cricket and movies', 'Actually 12 feet, no direct sunlight, and gaming too'],
    'vague-placement-after-answers': ['9 feet', 'Bright daylight', 'Cricket', 'Sides', 'Blurry picture', 'On that wooden thing near the window'],
    'vague-budget-after-answers': ['9 feet', 'Bright daylight', 'Cricket', 'Sides', 'Blurry picture', 'Wall', 'Something affordable, not too expensive', 'Correct'],
    'belief-label-expert': ['Customer says every 4K TV gives the same picture. What should I say?', 'Explain Samsung Vision Q55 HDMI 2.1 for this customer.', 'Explain model XYZ-UNKNOWN-999', 'Ask an expert', 'Does that big black TV support my old box?', 'Resolved'],
    'early-price-and-dates': ['What is the price of Samsung Vision Q55?', 'Customers from 5 Nov 2026 to 1 Nov 2026', 'Customers from 01/11/2026 to 05/11/2026', 'Customers yesterday'],
}
if '--extra' in sys.argv:
    scenarios = {name: turns for name, turns in scenarios.items() if name in ['combined-after-prompt', 'correction-without-keywords', 'text-demo-preference']}
    out = out / 'extra'
    out.mkdir(exist_ok=True)

with tempfile.TemporaryDirectory() as directory, patch.object(store, 'DB_PATH', Path(directory) / 'probe.db'):
    with TestClient(create_app()) as client:
        assert client.post('/api/auth/login', json={'phone':'9000000009','password':'Admin@123'}).status_code == 200
        rebuilt = client.post('/api/admin/reindex')
        print(f'Isolated index rebuild: HTTP {rebuilt.status_code}', flush=True)
        assert client.post('/api/auth/login', json={'phone':'9000000001','password':'Associate@123'}).status_code == 200
        for name, turns in scenarios.items():
            c = client.post('/api/customers', json={'name': 'Synthetic ' + name}).json()
            for number, utterance in enumerate(turns):
                before = len(c['messages'])
                started = time.monotonic()
                r = client.post(f"/api/customers/{c['id']}/messages", json={'text':utterance,'request_id':f'{name}-{number}'})
                if r.status_code == 429:
                    time.sleep(61)
                    r = client.post(f"/api/customers/{c['id']}/messages", json={'text':utterance,'request_id':f'{name}-{number}'})
                elapsed = round(time.monotonic()-started, 2)
                body = r.json()
                c = client.get(f"/api/customers/{c['id']}").json()
                item = {'scenario':name,'input':utterance,'status':r.status_code,'seconds':elapsed,'home':c['home'],'question':c['flow'].get('question'),'stage':c['stage'],'confirmed':c['confirmed'],'selected':c['selected'],'replies':[m['text'] for m in c['messages'][before:] if m['role'] != 'user'],'flow':c['flow']['lines']}
                if r.status_code != 200:
                    item['error'] = body
                results.append(item)
                (out/'conversations.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
                print(f'{name}/{number}: HTTP {r.status_code}, {elapsed}s, next={item["question"]}, home={json.dumps(c["home"], ensure_ascii=True)}', flush=True)
                if r.status_code >= 500:
                    break
print(f'Saved {len(results)} turns to {out}/conversations.json')
