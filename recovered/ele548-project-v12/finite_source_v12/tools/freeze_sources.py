#!/usr/bin/env python3
"""Keep exact source bytes for historical local gate versions, verified by SHA."""
from pathlib import Path
import hashlib,json,subprocess
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;OUT=BASE/'frozen_sources'
def digest(b):return hashlib.sha256(b).hexdigest()
def refs(v):
 if isinstance(v,dict):
  if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str):yield v
  for x in v.values():yield from refs(x)
 elif isinstance(v,list):
  for x in v:yield from refs(x)
def main():
 wanted={}
 for p in (BASE/'reports').glob('*.json'):
  for r in refs(json.loads(p.read_text())):
   f=Path(r['path'])
   if f.is_relative_to(BASE) and f.suffix in {'.hpp','.cpp','.cc','.hh','.py'}:wanted[str(f),r['sha256']]=f
 OUT.mkdir(exist_ok=False);result=[];cache={}
 for (original,expected),p in sorted(wanted.items()):
  body=p.read_bytes() if p.exists() else b'';how='current_worktree';revision=None
  if digest(body)!=expected:
   relative=str(p.relative_to(ROOT))
   if relative not in cache:
    versions=[]
    for rev in subprocess.check_output(['git','log','--format=%H','--',relative],cwd=ROOT,text=True).splitlines():
     raw=subprocess.check_output(['git','show',rev+':'+relative],cwd=ROOT);versions.append((rev,raw))
    cache[relative]=versions
   matches=[(rev,raw) for rev,raw in cache[relative] if digest(raw)==expected]
   if matches:revision,body=matches[0];how='committed_exact_source'
   elif p.name=='service.hpp':
    # A2 predates the read-only observer added for A3. Recover those bytes
    # only if deleting that exact added block reproduces the recorded SHA.
    for rev,raw in cache[relative]:
     text=raw.decode()
     if ' struct Observation {' in text and ' bool source_bit(' in text:
      start=text.index(' struct Observation {');end=text.index(' bool source_bit(',start)
      candidate=(text[:start]+text[end:]).encode()
      if digest(candidate)==expected:body=candidate;revision=rev;how='exact_A2_bytes_recovered_from_recorded_observer_delta';break
  assert digest(body)==expected,('MISSING_EXACT_HISTORICAL_SOURCE',original,expected)
  target=OUT/(expected+'__'+p.name)
  if target.exists():assert target.read_bytes()==body
  else:target.write_bytes(body)
  result.append({'original_path':original,'sha256':expected,'frozen_path':str(target),'method':how,'revision':revision})
 with (BASE/'reports/FROZEN_SOURCE_INDEX.json').open('x') as f:json.dump({'status':'PASS_ALL_REFERENCED_LOCAL_SOURCE_BYTES_FROZEN_BY_RECORDED_SHA','files':result},f,indent=2);f.write('\n')
 print(json.dumps({'status':'PASS_EXACT_HISTORICAL_AND_CURRENT_SOURCE_FREEZE','bindings':len(result)}))
if __name__=='__main__':main()
