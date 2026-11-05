"""Small private handoff: actual new evidence and locks, no build binaries/PDK."""
from v5_common import ROOT,write,sha
import json,zipfile,datetime,subprocess
F=ROOT/'rate_state_v5/results';assert json.loads((F/'EXECUTION_AUDIT.json').read_text())['status'].startswith('PASS')
assert json.loads((F/'FINAL_INTERPRETATION.lock.json').read_text())['qualified_new_candidates']==0
paths=set()
def addtree(folder,filter=lambda p:True):
 for p in folder.rglob('*'):
  if p.is_file() and filter(p):paths.add(p)
addtree(F,lambda p:p.name not in ['BUNDLE.json','BUNDLE_CONTENTS.sha256'])
for folder in ['src/rate_state_v5','src/rate_state_v5_support','src/rate_state_v5_r5','src/rate_state_v5_r5_support','src/rate_state_v5_tools','gem5_rate_state_v5_ext','gem5_rate_state_v5_r5_ext']:
 addtree(ROOT/folder)
for p in (ROOT/'scripts').glob('v5_*.py'):paths.add(p)
for name in ['gem5/o3_rate_state_v5.py','gem5/o3_rate_state_v5_r5.py','setup/build_rate_state_v5.sh','setup/build_rate_state_v5_r5.sh','AGENTS.md','docs/00_LATEST_DECISIONS.ko.md','rate_state_v5/RESUME.ko.md']:
 paths.add(ROOT/name)
for name in ['data/manifests/datasets.json','data/manifests/cern_files.json','data/derived/flying_laptop_audit.json',
             'data/curated/cern_footprint_model_card.json','data/curated/flying_timing_model_card.json',
             'sources/source_manifest.json','sources/manifest.json','sources/protection_scope.lock.json','sources/public_workload_sources.lock.json']:
 paths.add(ROOT/name)
for p in (ROOT/'data/derived/cern').glob('*.audit.json'):paths.add(p)
addtree(ROOT/'rate_state_v5/handoff',lambda p:p.suffix!='.zip')
for name in ['runtime','runtime_r5']:
 folder=ROOT/'rate_state_v5'/name
 for sub in ['configs','sources','literature','inputs']:
  addtree(folder/sub,lambda p:p.suffix not in ['.opt','.o'] and p.stat().st_size<5*1024**2 and not (p.name.startswith('basicmath_') and p.suffix==''))
 for p in folder.glob('*'):
  if p.is_file() and p.stat().st_size<5*1024**2:paths.add(p)
 # Raw simulator logs, schedules, state/event/checksum summaries and stdout.
 # Verbose diagnostic cost/read files stay local with hashes in the report locks.
 raw_names={'gem5.log','gem5.log.time','schedule.ticks','seu.json','logical_manifest.json','program.stdout','program.stderr','events.csv','stats.txt'}
 addtree(folder/'reports',lambda p:p.name in raw_names or p.suffix in ['.json','.log','.time','.plan'] or (p.suffix=='.csv' and 'CPP_' in str(p.parent)))
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
lock=F/'BUNDLE_CONTENTS.sha256';lock.write_text(''.join(f'{h}  {p}\n' for p,h in manifest.items()));paths.add(lock)
dest=ROOT/'reports/BP_SEU_Rate_State_v5_Completed_20261015.zip';assert not dest.exists()
with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in sorted(paths):z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(paths) and len(set(z.namelist()))==len(paths)
 import hashlib
 for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest,('ARCHIVED_HASH_MISMATCH',name)
write(F/'BUNDLE.json',dict(status='PASS_ZIP_CRC_AND_FILE_HASHES',path=str(dest.relative_to(ROOT)),sha256=sha(dest),bytes=dest.stat().st_size,files=len(paths),
 content_manifest_sha256=sha(lock),excluded='Large build ELFs/full gem5 tree/old research raw archives/verbose cost and read diagnostics remain local, locked by SHA. No PDK/license material.',
 reproducibility='Exact producer/input/source locks and local raw evidence locations included; HW1 traces and pinned build dependencies require existing user workspace. Private local archive, never publicly pushed.'))
print('PASS package',dest.name,round(dest.stat().st_size/1024**2,2),'MiB;',len(paths),'actual files')
