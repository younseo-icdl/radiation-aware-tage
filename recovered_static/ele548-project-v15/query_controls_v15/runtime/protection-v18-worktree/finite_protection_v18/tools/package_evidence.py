"""Immutable local handoff of actual evidence; active raw runs excluded."""
import argparse,sys,pathlib,json,zipfile,hashlib,subprocess
sys.dont_write_bytecode=True
import resources as r
B=r.BASE

def package(label):
 out=B/'runtime/artifacts';out.mkdir(exist_ok=True);dest=out/('BP_SEU_Finite_Protection_'+label+'.zip');assert not dest.exists()
 files={}
 def add(path,arc=None):
  path=pathlib.Path(path)
  if path.is_file():files[arc or str(path.relative_to(B))]=path
 for name in ('docs','src','tests','tools','gem5_overlay','producer_source','sources','reports'):
  for p in (B/name).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:add(p)
 add(B.parent/'AGENTS.md','AGENTS.md')
 for name in ('START_HERE.ko.md','CODEX_PROMPT.ko.txt'):add(B/name)
 for folder in ('frozen','producers','configs','initialization_A1','initialization_B1','initialization_B2','inputs'):
  for p in (B/'runtime'/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:add(p)
 raw=[]
 for d in sorted((B/'runtime/cpu_trials').iterdir()):
  if not d.is_dir() or not(d/'EXECUTION.json').exists():continue
  x=r.load(d/'EXECUTION.json')
  if label.startswith('G2') and x.get('task',{}).get('phase') not in ('CPU_GATE24','REGRESSION_RESERVE_B2') and not d.name.startswith('DIAGNOSTIC_B1'):continue
  for name,digest in x.get('hashes',{}).items():assert r.sha(d/name)==digest,('RAW_CHANGED',str(d/name))
  for p in d.rglob('*'):
   if p.is_file():add(p)
  raw.append({'label':d.name,'status':x['status'],'execution':r.ref(d/'EXECUTION.json')})
 for p in (B/'runtime').glob('*/*'):
  if p.is_file() and p.name in ('stdout','stderr','job.time','EXECUTION.json'):add(p)
 for p in (B/'runtime').glob('gem5_build_*/*.d'):add(p)
 add(B/'runtime/gem5_build_B2/gem5.protection_v18.opt')
 dependencies=r.load(B/'reports/CPU_BUILD_B2.json')['actual_dependencies']
 # Preserve compiled own sources and public dependency bytes already recorded;
 # system libraries/toolchain/datasets remain SHA-locked external references.
 inventory={name:{'sha256':r.sha(path),'bytes':path.stat().st_size} for name,path in sorted(files.items())}
 header={'status':'ACTUAL_EVIDENCE_SNAPSHOT_NOT_FABRICATED_NEW_RESULTS','label':label,'closed_cpu_raw':len(raw),'raw':raw,'active_or_non_gate_raw_excluded':True,'software_source_closure':r.ref(B/'sources/manifest.lock.json'),'current_resources_at_snapshot':r.snapshot(),'external_dependencies':dependencies,'scope':'No PDK/library/license/media uploads. Separate original baseline ZIP preserved. Absolute paths are original host references, not a portable installed toolchain.'}
 with zipfile.ZipFile(dest,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.writestr('HANDOFF_STATUS.json',json.dumps(header,indent=2)+'\n');z.writestr('ARCHIVE_SHA256.json',json.dumps(inventory,indent=2)+'\n')
  for name,path in sorted(files.items()):z.write(path,name)
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  for name,item in inventory.items():assert hashlib.sha256(z.read(name)).hexdigest()==item['sha256'],('ZIP_HASH',name)
 report={'status':'PASS_ZIP_CRC_AND_EVERY_MEMBER_SHA256','archive':r.ref(dest),'archive_bytes':dest.stat().st_size,'members':len(files)+2,'closed_cpu_raw':len(raw),'resources':r.snapshot()};r.put(B/'reports'/('PACKAGE_'+label+'.json'),report);print(json.dumps(report),flush=True);return dest
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);a=p.parse_args();package(a.label)
