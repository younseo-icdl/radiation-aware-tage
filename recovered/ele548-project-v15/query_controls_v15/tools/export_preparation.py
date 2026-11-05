#!/usr/bin/env python3
"""Read-only source/provenance audit and bounded local preparation export."""
from pathlib import Path
import hashlib,io,json,sys,zipfile
sys.dont_write_bytecode=True
import prepare as m
BASE=m.BASE
def load(p):return json.loads(p.read_text())
def main():
 m.budget();m.preserve();assert not (BASE/'runtime/cpu_trials').exists()
 refs={}
 def collect(v,report):
  if isinstance(v,dict):
   if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str):refs.setdefault((v['path'],v['sha256']),[]).append(str(report))
   for x in v.values():collect(x,report)
  elif isinstance(v,list):
   for x in v:collect(x,report)
 for p in (BASE/'reports').glob('*.json'):collect(load(p),p)
 for p in (BASE/'runtime').rglob('EXECUTION.json'):collect(load(p),p)
 frozen={m.sha(p):p for p in (BASE/'runtime/frozen').glob('*') if p.is_file()};versions=[]
 for (name,digest),reports in sorted(refs.items()):
  p=Path(name)
  if p.is_file() and m.sha(p)==digest:actual=p
  else:assert digest in frozen,('MISSING_SOURCE_VERSION',name,digest);actual=frozen[digest]
  versions.append({'original_path':name,'sha256':digest,'verified_bytes':str(actual),'referenced_by':reports})
 deps=load(BASE/'reports/CPU_BUILD_A1.json')['actual_dependencies']
 for ref in deps:assert m.sha(ref['path'])==ref['sha256']
 m.put(BASE/'reports/SOURCE_VERSIONS.json',{'status':'PASS_ALL_REFERENCED_BYTES_CURRENT_OR_PRESERVED','versions':versions,'CPU_new':0})
 failed=[]
 for p in (BASE/'runtime').rglob('EXECUTION.json'):
  if load(p)['exit_code']!=0:failed.append(m.ref(p))
 assert not failed
 m.put(BASE/'reports/PREPARATION_GATES.json',{'status':'PASS_SOFTWARE_PREPARATION_NOT_CPU_RUN_OR_HARDWARE_QUALIFIED','gates':[m.ref(BASE/'reports'/p) for p in ['query_gate_A1.json','early_gate_A2.json','CPU_BUILD_A1.json','INITIALIZATION_A1.json','MICRO_NATIVE_A1.json','SOURCE_VERSIONS.json']],'proposal':m.ref(BASE/'reports/CPU18_PROPOSAL.lock.json'),'report':m.ref(BASE/'reports/PREPARED_REPORT.ko.md'),'actual_failed_executions':failed,'CPU_new':0,'hardware_qualified_candidates':0,'goal':'active','resources':m.budget()})
 files=[];excluded=[]
 for p in sorted(BASE.rglob('*')):
  if not p.is_file() or any(x in p.relative_to(BASE).parts for x in ['artifacts','__pycache__']):continue
  with p.open('rb') as f:elf=f.read(4)==b'\x7fELF'
  if elf and (p.stat().st_size>1048576 or p.suffix=='.o'):excluded.append(m.ref(p));continue
  files.append(p)
 contents=BASE/'reports/EXPORT_CONTENTS.json';m.put(contents,{'files':[m.ref(p) for p in files],'large_ELF_preserved_in_place_not_embedded':excluded});files.append(contents)
 memory=io.BytesIO()
 with zipfile.ZipFile(memory,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in files:z.write(p,'query_controls_v15/'+str(p.relative_to(BASE)))
 blob=memory.getvalue();m.budget(extra_MiB=len(blob)/1048576+.25)
 output=BASE/'artifacts/BP_SEU_V15_PREPARED_QUERY_EARLY.zip';output.parent.mkdir(exist_ok=True)
 with output.open('xb') as f:f.write(blob)
 with zipfile.ZipFile(output) as z:
  assert z.testzip() is None
  for ref in load(contents)['files']:
   name='query_controls_v15/'+str(Path(ref['path']).relative_to(BASE));assert hashlib.sha256(z.read(name)).hexdigest()==ref['sha256']
 m.preserve();m.put(BASE/'reports/POST_EXPORT_VERIFICATION.json',{'status':'PASS_PREPARATION_ZIP_BYTES_AND_BUDGET_NOT_CPU_TEST','archive':m.ref(output),'files':len(files),'ELF_excluded':len(excluded),'CPU_new':0,'resources':m.budget()});print('PASS_PREPARATION_EXPORT',len(versions),'bindings',m.ref(output))
if __name__=='__main__':main()
