"""Apply reviewed, source-specific introductions without modifying research claims or maps."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = [line.split('\t') for line in (root / 'content/guide-updates.tsv').read_text().splitlines()]
assert len(rows) == len({r[0] for r in rows}) == 234
catalogue = json.loads((root / 'dist/data/catalogue.json').read_text())
families = {f['id']: f for f in catalogue['families']}
map_path = root / 'public-shell/explore/map-data.json'
map_data = json.loads(map_path.read_text())
docs = {d['id']: d for d in map_data['docs']}
out = root / 'public-shell/explanations'
out.mkdir(exist_ok=True)
for family_id, question, idea in rows:
    family = families[family_id]
    guide = json.loads((root / f'dist/explanations/{family_id}.json').read_text())
    guide.update(question=question, idea=idea, exactClaim=family['summary'],
                 explanationVersion=3, sourceCommit=catalogue['commit'],
                 reviewStatus='assistant-authored from source summary; not mathematically reviewed',
                 scope='Family-level introduction based on the pinned catalogue summary. Summarizes manuscript claims; not an independent proof review.')
    guide.pop('model', None)
    guide.pop('revision', None)
    (out / f'{family_id}.json').write_text(json.dumps(guide, ensure_ascii=False) + '\n')
    docs[family_id].update(question=question, idea=idea)
map_path.write_text(json.dumps(map_data, ensure_ascii=False))
print(f'Applied {len(rows)} guides; retained source claims, references and map geometry.')
