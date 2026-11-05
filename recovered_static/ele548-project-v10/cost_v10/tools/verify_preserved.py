"""Read-only identity check of pre-V10 anchors, priorCPU starts and source locks."""
from pathlib import Path
import hashlib,json
from budget import BASE
lock=json.loads((BASE/'configs/PRESERVED_V9.lock.json').read_text());old=Path(lock['old_root'])
rows=[]
for rel,expected in lock['files'].items():
 p=old/rel;actual=hashlib.sha256(p.read_bytes()).hexdigest();rows.append(dict(path=str(p),expected_sha256=expected,actual_sha256=actual,status='PASS' if actual==expected else 'FAIL'))
assert all(x['status']=='PASS' for x in rows)
summary=dict(status='PASS_ALL_PRIOR_ANCHORS_IDENTICAL',files=rows,scope='Anchors and hashed bundle manifests; separateSTA_FINAL verifies94DBentries. Not a claim every arbitrary untracked oldworkspacefile was hashed.')
(BASE/'reports/PRESERVATION.json').write_text(json.dumps(summary,indent=2)+'\n');print(summary['status'],len(rows))
