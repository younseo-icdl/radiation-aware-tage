#!/usr/bin/env python3
"""Read-only existing evidence -> bounded continuation ZIP, no staging copies."""
from pathlib import Path
from zoneinfo import ZoneInfo
import datetime,hashlib,json,subprocess,sys,zipfile
sys.dont_write_bytecode=True
B=Path(__file__).resolve().parents[1]
V15=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
V17=V15/'runtime/termination-v17-worktree/termination_v17'
V9=Path('/home/youns/workspace/ele548-project-v9')
OLD=Path('/home/youns/workspace/ele548-project')
sys.path.insert(0,str(V17/'tools'));import resources_disk328 as r
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def main():
 state=r.snapshot(0,4);assert state['CPU_global']==3531 and state['outstanding_reservations']==0
 baseline=load(B/'reports/PRESERVED_BASELINE.lock.json')
 for x in baseline['references']+[baseline['current_binary']]:assert sha(x['path'])==x['sha256']
 binding=load(V17/'reports/FINAL_BINDINGS.json');assert binding['compiled_dependency_count']==408
 for x in binding['exact_refs']+binding['compiled_dependencies_verified']:assert sha(x['path'])==x['sha256']
 before={str(x['path']):x['sha256'] for x in load(V17/'reports/PRECHECK_A1.json')['old_failed_files_preserved']}
 content={};index={}
 def add(p,member=None):
  p=Path(p).resolve();assert p.is_file(),str(p)
  assert p.suffix.lower() not in {'.lib','.lef','.gds','.oas','.spef','.lic','.db','.opt','.o','.pdf','.zip'}
  if member is None:member='snapshot/'+str(p).lstrip('/')
  assert not member.startswith('/') and '..' not in Path(member).parts
  if member in content:assert content[member]==p;return
  content[member]=p;index[member]={'member':member,'original_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
 for p in sorted(B.rglob('*')):
  if p.is_file() and 'runtime' not in p.relative_to(B).parts and p.name not in {'PACKAGE_REPORT.json'}:add(p,p.relative_to(B).as_posix())
 add(B.parent/'AGENTS.md','AGENTS.md')
 for p in sorted(V17.rglob('*')):
  if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc':add(p,'prior/v17/'+p.relative_to(V17).as_posix())
 for x in binding['compiled_dependencies_verified']:add(x['path'])
 proposal=load(V15/'reports/CPU18_PROPOSAL.lock.json')
 for p in sorted((V15/'reports').glob('*')):
  if p.is_file() and (p.name.startswith(('CPU','early_gate','query_gate')) or p.name in {'PREPARATION_GATES.json','PREPARED_REPORT.ko.md','USER_ACTIONS_REQUIRED.md'}):add(p,'prior/v15/reports/'+p.name)
 for p in sorted((V15/'tools').glob('*.py')):add(p)
 for p in sorted((V15/'gem5_overlay').rglob('*.py')):add(p)
 for gate in ('early_gate_A1','early_gate_A2','early_gate_A3','query_gate_A1'):
  for x in load(V15/'reports'/(gate+'.source.lock.json'))['files']:
   assert sha(x['verified_bytes'])==x['sha256'];add(x['verified_bytes'])
 trialdirs={V15/'runtime/cpu_trials'/t['label'] for t in proposal['tasks']}
 trialdirs|={V15/'runtime/cpu_trials'/('dijkstra_small.R1.EARLY_'+k+'_Q1U1.terminal_A1') for k in ('REC','DIRECT')}
 assert len(trialdirs)==20
 for d in sorted(trialdirs):
  execution=load(d/'EXECUTION.json')
  for name,digest in execution['hashes'].items():assert sha(d/name)==digest
  for p in sorted(d.iterdir()):
   if p.is_file():add(p,'prior/v15/raw/'+d.name+'/'+p.name)
 for p in sorted((V15/'runtime/cpu_trials/run_starts').glob('*.json')):add(p,'prior/v15/run_starts/'+p.name)
 for p in sorted((V15/'runtime/CPU18_DISPATCH_A1').iterdir()):
  if p.is_file():add(p,'prior/v15/dispatch/'+p.name)
 references={Path(t['architectural_reference']['path']) for t in proposal['tasks'] if t.get('architectural_reference')}
 for program in ('qsort_small','dijkstra_small','sha1'):
  root=Path('/home/youns/workspace/ele548-project-v14/o3_finite_v14/runtime/cpu_trials')
  references|={root/(program+'.R1.'+variant)/'EXECUTION.json' for variant in ('direct.L1','recurrent.L2')}
 for p in sorted(references):
  add(p,'prior/reference_records/'+p.parent.name+'.EXECUTION.json')
 for p in sorted((V9/'src/protection').glob('*.hpp')):add(p)
 for name in ('native_v9r2_eval.py','native_v9r2_eval_analyze.py','native_v9r2_eval_inputs.py','native_v9r2_gate.py','native_v9_common.py','native_v9_campaign.py','rng_namespace.py','v3_cpu_common.py','v3_common.py'):add(V9/'scripts'/name)
 for rel in ('sources/protection_scope.lock.json','sources/e2_protection_logical_manifest.json','sources/periodic_logical_state_manifest.json','sources/periodic_policy_selection.lock.json','data/derived/STAGE0_MODEL_CARD.json','rate_state_v5/results/DATA_MODEL_CARD.ko.md','rate_state_v9/r2_evaluation/runtime/configs/PROPOSAL.lock.json','rate_state_v9/r2_evaluation/runtime/configs/inputs.lock.json'):
  add(V9/rel)
 for rel in ('sources/manifest.json','sources/source_manifest.json','sources/references.bib','sources/SOURCE_INDEX.ko.md','sources/cern_methods.lock.json','reports/STAGE0_REPORT.md','reports/E1_REPORT.ko.md','reports/E2_REPORT.ko.md','reports/DATASET_READINESS.json','reports/software.lock.json'):
  add(OLD/rel)
 for name in ('OWNERS.lock.json','OWNER_REGISTRY.lock.json'):add(Path('/home/youns/workspace/ele548-project-v10/native_lifetime_next/runtime/configs')/name)
 for d in sorted((V9/'rate_state_v9/r2_evaluation/runtime/reports/EVAL_FAULT').glob('qsort_small.*.R2_EVALUATION.0.0.U')):
  for name in ('events.csv','schedule.ticks','logical_manifest.json','seu.json'):add(d/name)
 metadata={'status':'PLAN_AND_PRIOR_EVIDENCE_NOT_NEW_V18_RESULTS','at_America_New_York':datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(),'plan_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=B.parent,text=True).strip(),'parent_commit':baseline['parent_commit'],'all_members_except_this_manifest_are_hashed':True,'new_simulations':0,'new_v18_controller_or_ELF':False,'external_large_dependencies_not_embedded':[baseline['current_binary']],'continuation_scope':'same-server source/config/raw snapshot; full toolchain/workload/dataset/PDF external references retained; no proprietary PDK files','files':[index[k] for k in sorted(index)]}
 out=V15/'runtime/cpu_trials/handoff_v18_artifacts';out.mkdir(exist_ok=False)
 path=out/'BP_SEU_Finite_Protection_Pipeline_Handoff_v18.zip'
 with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for member in sorted(content):
   p=content[member];data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==index[member]['sha256'];z.writestr(member,data)
   assert path.stat().st_size<4*1024**2,'RESERVED_ARCHIVE_SIZE_EXCEEDED'
  z.writestr('PACKAGE_CONTENTS.json',json.dumps(metadata,indent=2,ensure_ascii=False)+'\n')
 result=subprocess.run([sys.executable,'-B',str(B/'tools/verify_handoff.py'),str(path)],capture_output=True,text=True)
 (out/'verification.stdout').write_text(result.stdout);(out/'verification.stderr').write_text(result.stderr);assert result.returncode==0,result.stderr
 for name,digest in before.items():assert sha(name)==digest
 digest=sha(path);(out/(path.name+'.sha256')).write_text(digest+'  '+path.name+'\n')
 after=r.snapshot();assert after['CPU_global']==3531 and after['outstanding_reservations']==0
 report={'status':'PASS_HANDOFF_ZIP_CRC_ALL_SHA_PRIOR_FAILURES_PRESERVED','zip':ref(path),'zip_bytes':path.stat().st_size,'included_files':len(content),'included_raw_trial_dirs':len(trialdirs),'compiled_dependency_files':408,'old_failed_files_unchanged':len(before),'verifier':ref(B/'tools/verify_handoff.py'),'command':[sys.executable,'-B',str(B/'tools/package_handoff.py')],'verification':json.loads(result.stdout),'plan_commit':metadata['plan_commit'],'resources_after_export':after,'new_gem5_trials':0,'budget_authorization_created':False,'artifact_disk_accounting':'ZIP/report output is in existing CPU output artifact subtree, charged to328MiB recent and8GiB physical aggregate; plan source files remain in preparation sublimit240MiB.'}
 with (B/'reports/PACKAGE_REPORT.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
