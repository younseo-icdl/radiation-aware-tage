#!/usr/bin/env python3
"""Private source evidence bundle; no executable, dataset, PDK or environment."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,subprocess,sys,zipfile
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;REPORT=BASE/'reports'
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 gate=json.loads((REPORT/'FINAL_GATES.json').read_text());assert gate['new_CPU']==gate['new_EDA']==0 and gate['actual_global_CPU']==3487
 sources=json.loads((REPORT/'FROZEN_SOURCE_INDEX.json').read_text())
 for item in sources['files']:assert m.sha(item['frozen_path'])==item['sha256']
 candidates=[ROOT/'AGENTS.md',ROOT/'docs/00_LATEST_DECISIONS.ko.md',BASE/'README.ko.md',BASE/'PLAN.ko.md']
 for directory in ['src','tests','tools','reports','frozen_sources']:
  for p in sorted((BASE/directory).rglob('*')):
   if p.is_file() and not p.is_symlink() and '__pycache__' not in p.parts and p.suffix in {'.md','.py','.hpp','.cpp','.hh','.cc','.json','.csv'} and p.name not in ['BUNDLE_MANIFEST.json','PACKAGE_VERIFICATION.json']:candidates.append(p)
 for p in sorted((BASE/'runtime').rglob('*')):
  if p.is_file() and not p.is_symlink() and (p.suffix in {'.json','.time','.csv','.log','.txt'} or p.name in ['stdout','stderr']):candidates.append(p)
 candidates=sorted(set(candidates));before=m.budget();allocated_bound=sum(p.stat().st_size for p in candidates)/1024**2+2
 def kib(p):return int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0])
 assert kib(ROOT)/1024+allocated_bound<64
 assert (kib(ROOT)+kib(m.V11))/1024+allocated_bound<192
 assert before['all4_worktrees_GiB']+allocated_bound/1024<8 and shutil.disk_usage(ROOT).free/1024**3-allocated_bound/1024>=10
 records=[{'path':str(p.relative_to(ROOT)),'sha256':m.sha(p),'bytes':p.stat().st_size} for p in candidates]
 manifest=REPORT/'BUNDLE_MANIFEST.json';m.put(manifest,{'status':'ACTUAL_PRIVATE_SOURCE_COMPONENT_EVIDENCE','members':records,'exclusions':['ELF/object','full datasets/papers/PDK/libraries','environment dump'],
 'historical_exact_sources':m.ref(REPORT/'FROZEN_SOURCE_INDEX.json'),'requires_preserved_workspace':True,'packager':m.ref(Path(__file__))});candidates.append(manifest)
 output=BASE/'artifacts/BP_SEU_V12_FINITE_SOURCE_RESULTS.zip';output.parent.mkdir(exist_ok=True)
 with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in candidates:z.write(p,str(p.relative_to(ROOT)))
 with zipfile.ZipFile(output) as z:
  assert z.testzip() is None and len(z.infolist())==len(candidates)
  for r in records:assert hashlib.sha256(z.read(r['path'])).hexdigest()==r['sha256']
 for item in json.loads((m.V11/'overwrite_v11/reports/PRESERVATION.json').read_text())['preserved']:assert m.sha(item['path'])==item['sha256']
 assert m.sha(m.V11/'overwrite_v11/artifacts/BP_SEU_V11_OVERWRITE_RESULTS.zip')=='695b7975d0c3c8d02383c6734f3debca35684755ab7b46da7a6aa10a9044b3de'
 m.put(REPORT/'PACKAGE_VERIFICATION.json',{'status':'PASS_CRC_MEMBER_SHA_FROZEN_SOURCES_PRESERVATION_AND_SCOPED_BUDGET_NOT_CPU_OR_HARDWARE_QUALIFICATION',
 'archive':m.ref(output),'bytes':output.stat().st_size,'member_count':len(candidates),'manifest':m.ref(manifest),'before':before,'after':m.budget(),'new_CPU':0,'new_EDA':0,'actual_global_CPU':3487,
 'disk_scope':'Four actual worktrees plus inherited charged legacy20.5437088013GiB, not a fresh full original reference workspace audit'})
 print(json.dumps({'status':'PASS_PRIVATE_SOURCE_PACKAGE','archive':str(output),'sha256':m.sha(output),'bytes':output.stat().st_size,'members':len(candidates),'budget':m.budget()}))
if __name__=='__main__':main()
