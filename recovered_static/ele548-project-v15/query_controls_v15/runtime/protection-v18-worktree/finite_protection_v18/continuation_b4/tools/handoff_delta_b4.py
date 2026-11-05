"""Small immutable source/gate continuation overlay; not a completed campaign."""
import sys,pathlib,json,zipfile,io,hashlib
sys.dont_write_bytecode=True
import resources as r
ROOT=r.BASE;K=ROOT/'runtime/continuation_b4'
def package():
 paths={}
 def add(p):
  p=pathlib.Path(p)
  if p.is_file() and '__pycache__' not in p.parts:paths[str(p.relative_to(ROOT))]=p
 for folder in ('producer_source/B4','continuation_b4/tools','docs'):
  for p in (ROOT/folder).rglob('*'):add(p)
 for name in ('START_HERE_B4.ko.md','reports/USER_ACTIONS_REQUIRED.md','sources/B4_FAULT_AND_RESOURCE_MODEL_CARD.ko.md','sources/B4_SOURCE_AND_LOGICAL_MANIFEST.lock.json','reports/PRODUCER_B4.lock.json','reports/INITIALIZATION_B4.json','reports/B4_CORRECTNESS_ACCEPTANCE.json','reports/B4_COMMIT_BACKPRESSURE_GATE.json','reports/B3_REPEATED_FAULT_GATE_FAILURE.json','reports/CPU_4199_PROPOSAL.lock.json','reports/CPU_4161_AUTHORIZATION.lock.json','reports/CPU_4199_AUTHORIZATION.lock.json','reports/BUDGET_AUTHORIZATION.lock.json','reports/BUDGET_PROPOSAL.json','reports/CPU_4161_PROPOSAL.lock.json','reports/CPU_BUILD_B4_C1.json','reports/CPU_BUILD_PLAN_B4_C1.lock.json','reports/CPU_BUILD_B4_C1.source.lock.json'):add(ROOT/name)
 for p in (ROOT/'reports').glob('*_B4_C1.json'):add(p)
 for p in (ROOT/'reports').glob('B4_GATE_*.json'):add(p)
 for folder in (ROOT/'runtime/initialization_B4',K/'reports',ROOT/'runtime/producers/B4'):
  for p in folder.rglob('*'):add(p)
 raw=[]
 for folder in sorted((ROOT/'runtime/cpu_trials').glob('*_B4.*')):
  record=folder/'EXECUTION.json'
  if not record.exists():continue
  x=r.load(record)
  for name,digest in x.get('hashes',{}).items():assert r.sha(folder/name)==digest
  for p in folder.rglob('*'):add(p)
  raw.append(r.ref(record))
 assert len(raw)==18
 blobs={name:p.read_bytes() for name,p in sorted(paths.items())}
 inventory={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in blobs.items()}
 header={'status':'B4_SOURCE_GATE_CONTINUATION_NOT_COMPLETED_ABCD','raw_CPU_gate_count':18,'raw_gate_records':raw,'resources':r.snapshot(),'active_program_raw_excluded':True,'ELF_bytes_not_embedded_reference_only':r.load(ROOT/'reports/PRODUCER_B4.lock.json')['binary'],'B3_preserved_terminal_bundle':r.load(ROOT/'runtime/continuation_b3/reports/PACKAGE_TERMINAL_A1.json')['archive'],'original_host_paths_and_external_dependencies_required':True}
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  z.writestr('HANDOFF_STATUS.json',json.dumps(header,indent=2)+'\n');z.writestr('ARCHIVE_SHA256.json',json.dumps(inventory,indent=2)+'\n')
  for name,data in blobs.items():z.writestr(name,data)
 payload=buffer.getvalue();r.snapshot(extra_MiB=len(payload)/(1024*1024)+1)
 dest=ROOT/'runtime/artifacts/BP_SEU_Finite_Protection_B4_Gates_Continuation.zip'
 with dest.open('xb') as f:f.write(payload)
 with zipfile.ZipFile(dest) as z:
  assert z.testzip() is None
  for name,item in inventory.items():assert hashlib.sha256(z.read(name)).hexdigest()==item['sha256']
 report={'status':'PASS_CRC_EVERY_MEMBER_SHA_SOURCE_GATE_OVERLAY_ONLY','archive':r.ref(dest),'bytes':len(payload),'members':len(blobs)+2,'closed_O3_gate_raw':18,'resources':r.snapshot()}
 r.put(K/'reports/PACKAGE_GATES_CONTINUATION.json',report);print(json.dumps(report),flush=True)
if __name__=='__main__':package()
