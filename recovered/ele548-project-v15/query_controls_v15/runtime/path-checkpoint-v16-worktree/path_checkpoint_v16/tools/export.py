#!/usr/bin/env python3
"""Audit actual references and produce a bounded local handoff; no CPU jobs."""
from pathlib import Path
import hashlib,importlib.util,json,sys,zipfile
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('v16gate',Path(__file__).with_name('gate.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
B=g.BASE
def refs(value):
 if isinstance(value,dict):
  if isinstance(value.get('path'),str) and isinstance(value.get('sha256'),str):yield value
  for v in value.values():yield from refs(v)
 elif isinstance(value,list):
  for v in value:yield from refs(v)
def export(attempt):
 g.preserve();g.parent.budget(extra_MiB=.5)
 bindings={}
 for p in (B/'reports').glob('*.json'):
  for item in refs(json.loads(p.read_text())):bindings[(item['path'],item['sha256'])]=item
 rows=[]
 for (name,sha),item in sorted(bindings.items()):
  path=Path(name);current=path.exists() and g.sha(path)==sha
  frozen=[p for p in (B/'runtime/frozen').glob(sha+'.*') if g.sha(p)==sha]
  assert current or frozen,('UNRESOLVED_REFERENCE',name,sha)
  rows.append({'reference':item,'current_matches':current,'immutable_frozen_match':str(frozen[0]) if not current else None})
 audit=B/'reports'/('REFERENCE_AUDIT_'+attempt+'.json');g.put(audit,{'status':'ALL_REFERENCES_RESOLVED_CURRENT_OR_RETAINED_BYTES','bindings':rows,'new_CPU':0})
 paths=[]
 for folder in ('src','tests','tools','reports'):
  paths += [p for p in (B/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
 for p in (B/'runtime').rglob('*'):
  if 'export_'+attempt in p.parts:continue
  if p.is_file() and (p.name in ('stdout','stderr','job.time','EXECUTION.json','tage_base.cc','observed_tool_output.txt') or 'frozen' in p.parts):paths.append(p)
 paths += [B/'PLAN.ko.md',B/'.gitignore',g.ROOT/'AGENTS.md',g.ROOT/'docs/00_LATEST_DECISIONS.ko.md']
 paths=sorted(set(paths))
 # Preserve every exact inventory byte version before report/tool paths may
 # change later. Frozen files themselves are immutable and need no extra copy.
 for p in paths:
  if 'frozen' in p.parts:continue
  snapshot=B/'runtime/frozen'/(g.sha(p)+p.suffix)
  if not snapshot.exists():snapshot.write_bytes(p.read_bytes())
 excluded=[g.ref(B/'runtime'/('protocol_'+a)) for a in ('A1','A2')]
 inventory=B/'reports'/('EXPORT_CONTENTS_'+attempt+'.json')
 g.put(inventory,{'included':[g.ref(p) for p in paths],'excluded_large_ELFs_preserved_in_place':excluded,'CPU_new':0})
 directory=B/'artifacts';directory.mkdir(exist_ok=True)
 archive=directory/('BP_SEU_V16_PATH_CHECKPOINT_CPP_'+attempt+'.zip')
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in paths+[inventory]:z.write(p,str(p.relative_to(g.ROOT)))
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for item in json.loads(inventory.read_text())['included']:
   assert hashlib.sha256(z.read(str(Path(item['path']).relative_to(g.ROOT)))).hexdigest()==item['sha256']
 g.preserve();budget=g.parent.budget()
 g.put(B/'reports'/('POST_VERIFICATION_'+attempt+'.json'),{'status':'VERIFIED_CPP_EXPORT_NOT_CPU_OR_HARDWARE_QUALIFICATION','archive':g.ref(archive),'entries':len(paths)+1,'reference_audit':g.ref(audit),'actual_failed_compile_runs':0,'prior_export_failures':2,'CPU_new':0,'resources':budget})
 print(json.dumps({'archive':g.ref(archive),'bytes':archive.stat().st_size,'references':len(rows),'resources':budget},indent=2))
if __name__=='__main__':export(sys.argv[1])
