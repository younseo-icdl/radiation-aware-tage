"""Actual execution count, integrity and scope checks; no inferred success."""
from v5_common import ROOT,write,sha,used_cpu
import json,re,csv,subprocess,datetime
F=ROOT/'rate_state_v5/results';unique={};reports=[];invalid_isa=[];changed=[]
for folder in (ROOT/'rate_state_v5').glob('runtime*'):
 for p in (folder/'reports').glob('*.json'):
  try:d=json.loads(p.read_text())
  except json.JSONDecodeError:continue
  if not isinstance(d,dict):continue
  for r in d.get('tasks',[]):
   if not isinstance(r,dict) or not r.get('producer_binary_sha256') or not r.get('output'):continue
   key=r['output']
   if key in unique:
    assert unique[key]['status']==r['status'] and unique[key].get('cycles')==r.get('cycles'),('DUPLICATE_CONFLICT',key)
   else:unique[key]=r
  reports.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p)))
for key,r in unique.items():
 d=ROOT/key
 for name,digest in r.get('hashes',{}).items():
  if sha(d/name)!=digest:changed.append(str((d/name).relative_to(ROOT)))
 log=(d/'gem5.log').read_text(errors='replace')
 warnings=[s for s in log.splitlines() if re.search(r"instruction .*unimplemented|ignoring syscall|unimplemented syscall",s,re.I)]
 if warnings:
  invalid_isa.append(dict(output=key,status=r['status'],warnings=warnings));assert r['status']!='PASS',('UNSUPPORTED_ISA_MARKED_SUCCESS',key)
 if r['status']=='PASS':
  assert r['cycles']>0 and r['instructions']>0 and r.get('failure') is None
  m=json.loads((d/'logical_manifest.json').read_text());assert m['total_bits']==r['total_bits']
  if m.get('direct'):
   assert m['removed_fold_bits']==200
   assert len(m['additional_sites'])+65170==m['total_bits']
   assert len({s['id'] for s in m['additional_sites']})==len(m['additional_sites'])
  s=r['seu']
  for stem in ['hot','shadow','journal']:
   if stem+'_accepted' in s:assert s[stem+'_accepted']==sum(s[stem+'_'+suffix] for suffix in ['completed','cancelled','pending'])
assert not changed,changed[:3]
assert len(unique)<=2400,('CPU_BUDGET',len(unique))
assert used_cpu()<96*3600,('RECORDED_CORE_BUDGET',used_cpu()/3600)
disk=sum(int(s.split()[0]) for s in subprocess.check_output(['du','-sk','rate_state_v5','third_party/gem5-rate-state-v5','build/v5_producers'],cwd=ROOT,text=True).splitlines())/1024**2
assert disk<20,('DISK_BUDGET_GIB',disk)
for folder in ['runtime','runtime_r5']:
 p=ROOT/'rate_state_v5'/folder/'configs/PRODUCER.lock.json';d=json.loads(p.read_text());binary=ROOT/d['binary']
 relocation=p.parent/'PRODUCER.relocation.json'
 if relocation.exists():
  moved=json.loads(relocation.read_text());assert moved['original_lock_sha256']==sha(p);binary=ROOT/moved['binary']
 assert sha(binary)==d['binary_sha256'] and sha(ROOT/d['config'])==d['config_sha256']
 source=p.parent/'source.lock.json';lock=json.loads(source.read_text())
 for file,digest in lock['sources'].items():assert sha(ROOT/file)==digest,('SOURCE_CHANGED',file)
 if folder=='runtime_r5':
  for file,digest in lock['transport'].items():assert sha(ROOT/'third_party/gem5-rate-state-v5/src'/file)==digest,('TRANSPORT_CHANGED',file)
pres=json.loads((ROOT/'rate_state_v5/runtime/reports/FINAL_PRESERVATION_AUDIT.json').read_text());assert pres['status']=='PASS' and not pres['mismatches']
counts={}
for r in unique.values():
 k=r['phase'];counts.setdefault(k,dict(total=0,successes=0,failures=0));counts[k]['total']+=1;counts[k]['successes' if r['status']=='PASS' else 'failures']+=1
write(F/'EXECUTION_AUDIT.json',dict(status='PASS_EVIDENCE_INTEGRITY_NOT_HARDWARE_SAFETY',actual_distinct_cpu_executions=len(unique),
 actual_successes=sum(r['status']=='PASS' for r in unique.values()),actual_failures=sum(r['status']!='PASS' for r in unique.values()),
 phases=counts,recorded_core_hours=used_cpu()/3600,new_disk_gib=disk,unsupported_ISA_failed_runs=invalid_isa,
 preserved_old_files=pres['checked'],old_commit=pres['baseline_commit'],all_recorded_success_hashes_match=True,
 pending_at_exit='Recorded in each seu.json; retained as censoring, not free completed work',
 accounting='Merged evaluation clean view deduplicated by actual output directory. Initial superseded gates and all failures count toward trial budget.',
 remaining_scope='Integrity PASS does not override failing adverse metadata gate or partial physical population/calibration.',reports=reports))
write(F/'software.lock.json',dict(status='FINAL_SOFTWARE_EVIDENCE',root=str(ROOT),branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),
 source_commit_before_result_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 gem5_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',gem5_version='25.1.0.1',compiler='/opt/rh/gcc-toolset-11/enable',
 python=subprocess.check_output([ROOT/'.venv/bin/python','--version'],text=True).strip(),
 producers={name:json.loads((ROOT/'rate_state_v5'/name/'configs/PRODUCER.lock.json').read_text()) for name in ['runtime','runtime_r5']},
 reference_archives={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'reports/BP_SEU_PostV3_Completed_20261014.zip',ROOT/'reports/BP_SEU_CostAware_v3_Completed_20261013.zip']},
 no_EDA_or_TCAD=True,actual_execution_audit_sha256=sha(F/'EXECUTION_AUDIT.json')))
print('PASS immutable success evidence, producers, native/program gates, finite conservation, preserved',pres['checked'],'files;',len(unique),'actual CPU trials')
