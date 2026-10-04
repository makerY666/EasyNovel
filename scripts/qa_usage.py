"""Report paid acceptance usage from isolated databases, without reading credentials."""
import json
import sqlite3
from pathlib import Path

root=Path(__file__).resolve().parents[1]/'artifacts/acceptance-novels'
items=[]
for folder in ('2026-10-03','2026-10-03-v2'):
    for case in ('daily','mystery','fantasy'):
        database=root/folder/case/'data/studio.sqlite3'
        if not database.exists(): continue
        with sqlite3.connect(f'{database.as_uri()}?mode=ro',uri=True) as conn:
            usage=[json.loads(row[0]) for row in conn.execute('select usage from runs')]
            calls=dict(conn.execute('select status,count(*) from model_calls group by status'))
        items.append({'folder':folder,'case':case,'input_tokens':sum(x.get('input_tokens',0) for x in usage),'output_tokens':sum(x.get('output_tokens',0) for x in usage),'reserved_tokens':sum(x.get('reserved_tokens',0) for x in usage),'calls':calls})
report={'items':items,'input_tokens':sum(x['input_tokens'] for x in items),'output_tokens':sum(x['output_tokens'] for x in items),'reserved_tokens':sum(x['reserved_tokens'] for x in items),'money':'unknown; supplier bill authoritative','scope':'isolated three-novel trials including rejected drafts, truncated outputs, reviews and author revisions; excludes earlier live-smoke'}
(root/'2026-10-03-usage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
