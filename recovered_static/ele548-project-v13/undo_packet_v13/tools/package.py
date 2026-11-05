#!/usr/bin/env python3
"""Exclusive evidence archive; preserves all older producer/archive bytes."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys,zipfile
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 m.budget();gate=BASE/'reports/FINAL_GATES_A2.json';g=json.loads(gate.read_text());assert g['CPU_actual_global']==3487 and g['CPU_v13']==0
 for x in json.loads((BASE/'reports/PRESERVATION.lock.json').read_text())['preserved']:assert m.sha(x['path'])==x['sha256']
 members={}
 for p in sorted(BASE.rglob('*')):
  if not p.is_file() or 'artifacts' in p.relative_to(BASE).parts:continue
  name='undo_packet_v13/'+str(p.relative_to(BASE));members[name]=p
 for name in ['AGENTS.md','docs/00_LATEST_DECISIONS.ko.md']:members['workspace/'+name]=ROOT/name
 metadata={name:{'sha256':m.sha(p),'bytes':p.stat().st_size} for name,p in members.items()}
 target=BASE/'artifacts';target.mkdir(exist_ok=True);archive=target/'BP_SEU_V13_UNDO_PROVIDER_RESULTS.zip'
 with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,p in members.items():z.write(p,name)
  z.writestr('MEMBER_SHA256.json',json.dumps(metadata,indent=2)+'\n')
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for name,ref in metadata.items():
   content=z.read(name);assert len(content)==ref['bytes'] and hashlib.sha256(content).hexdigest()==ref['sha256']
 resources=m.budget()
 result={'status':'PASS_ARCHIVE_BYTES_AND_PREVIOUS_PRODUCER_PRESERVATION_NOT_O3_QUALIFICATION','archive':m.ref(archive),'bytes':archive.stat().st_size,'verified_members':len(metadata),'code_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'gate':m.ref(gate),'packager':m.ref(Path(__file__)),'resources_after_archive':resources,'global_CPU':3487,'CPU_cap':3487,'CPU_v13':0,'goal_status':'active','legacy_charge_scope':'20.54370880126953GiB is inherited charged-scope snapshot, not fresh entire legacy du'}
 m.put(BASE/'reports/POST_PACKAGE_VERIFICATION.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
