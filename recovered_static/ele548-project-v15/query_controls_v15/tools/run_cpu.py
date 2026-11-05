#!/usr/bin/env python3
"""Exact CPU18 plan; fail-closed gates; no execution without actual approval."""
from pathlib import Path
import argparse,ast,concurrent.futures,fcntl,importlib.util,json,sys
sys.dont_write_bytecode=True
import prepare as m
import resources_cpu as r
BASE=m.BASE;OUT=r.OUT
s=importlib.util.spec_from_file_location('frozen_v14_runner',m.V14/'tools/run_cpu.py');old=importlib.util.module_from_spec(s);s.loader.exec_module(old)
def load(p):return json.loads(Path(p).read_text())
def checked(v):assert m.sha(v['path'])==v['sha256'],('CHANGED_BINDING',v['path']);return Path(v['path'])
def validate(t,d,exit_code):
 result=old.validate(t,d,exit_code);seu=result['seu'];manifest=load(d/'logical_manifest.json')
 assert seu['early_enabled']==t['early'] and seu['early_pending']==0
 assert seu['early_claimed']==seu['early_delivered']+seu['early_pending']
 assert not t['early'] or seu['early_claimed']>0
 assert manifest['source_query_L']==t['query_L'] and manifest['source_update_L']==(1 if t['representation']=='direct' else t['update_L'])
 assert manifest['early_unconditional']==t['early'] and manifest['early_checkpoint_bits']==(848 if t['early'] else 0)
 if t.get('regression_reference'):
  reference=load(checked(t['regression_reference']))
  assert result['cycles']==reference['cycles'] and result['simInsts']==reference['simInsts'] and result['IPC']==reference['IPC'],'V14_BACKWARD_CPU_REGRESSION'
  for key,value in reference['seu'].items():
   if key not in ['model','max_lookup_pending','max_source_pending']:assert seu[key]==value,('V14_STATE_PROTOCOL_DIFFERENCE',key)
 if t.get('architectural_reference'):
  ref=load(checked(t['architectural_reference']))['seu']
  for key in ['committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash']:assert seu[key]==ref[key],('ARCHITECTURAL_OR_COMMITTED_RNG_DIFFERENCE',key)
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 proposal_path=BASE/'reports/CPU18_PROPOSAL.lock.json';proposal=load(proposal_path);assert len(proposal['tasks'])==18
 if not a.run:
  print(json.dumps({'status':'DRY_RUN_NO_CPU_DISPATCH','primary_cases':18,'proposal':m.ref(proposal_path),'resources':r.snapshot()},indent=2));return
 assert r.AUTH.exists(),'USER_BUDGET_AMENDMENT_REQUIRED'
 auth=load(r.AUTH);checked(auth['proposal']);assert auth['proposal']['sha256']==m.sha(proposal_path)
 assert r.snapshot()['caps']['approved'] and not OUT.exists(),'DO_NOT_RESTART_FROZEN_OUTPUT'
 binary=checked(proposal['binary']);config=checked(proposal['config']);build=load(checked(proposal['build']))
 for dep in build['actual_dependencies']:checked(dep)
 assert load(checked(proposal['initialization']))['status']=='PASS_15_TICK0_CONFIGS_NOT_CPU_EXECUTION'
 m.preserve();OUT.mkdir();(OUT/'run_starts').mkdir()
 plan=BASE/'reports/CPU18_EXECUTION.lock.json';m.put(plan,{'status':'FROZEN_AFTER_USER_AUTHORIZATION_BEFORE_TRIALS','proposal':m.ref(proposal_path),'authorization':m.ref(r.AUTH),'binary':m.ref(binary),'config':m.ref(config),'runner':m.ref(__file__),'resources':r.snapshot()})
 original_plan=load(checked(proposal['v14_execution_plan']))
 namespace=vars(old).copy();namespace.update(BASE=BASE,ROOT=m.ROOT,OUT=OUT,m=m,r=r,binary=binary,config=config,build=build,proposal=proposal,plan=plan,validate=validate)
 tree=ast.parse(checked(original_plan['runner']).read_text());main_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');one=next(n for n in main_node.body if isinstance(n,ast.FunctionDef) and n.name=='one')
 exec(compile(ast.Module(body=[one],type_ignores=[]),str(checked(original_plan['runner'])),'exec'),namespace);dispatch=namespace['one'];rows=[]
 def save(name,status,extra=None):m.put(BASE/'reports'/(name+'.json'),{'status':status,'tasks':rows,'plan':m.ref(plan),'extra':extra,'resources':r.snapshot()})
 def batch(tasks,name):
  r.snapshot(sum(t['timeout_seconds']+5 for t in tasks),len(tasks))
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(32,len(tasks))) as pool:out=list(pool.map(dispatch,tasks))
  rows.extend(out);save(name,'PASS_FUNCTIONAL_PHASE' if all(x['status'].startswith('PASS_') for x in out) else 'FAILURES_RETAINED')
  print(name,len(rows),'terminal',flush=True);return out
 tasks=proposal['tasks'];backward=batch(tasks[:2],'CPU_BACKWARD2')
 if not all(x['status'].startswith('PASS_') for x in backward):save('CPU_STOP','STOP_SHARED_BACKWARD_GATE_FAILED');return
 micro=batch(tasks[2:6],'CPU_MICRO4');valid_micro=all(x['status'].startswith('PASS_') for x in micro)
 by_label={t['label']:t for t in tasks}
 overlap=valid_micro and len({tuple(x['seu'][k] for k in ['committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash']) for x in micro})==1 and all(x['seu']['max_lookup_pending']>=2 if by_label[x['label']]['early'] else x['seu']['max_lookup_pending']==1 for x in micro)
 save('CPU_OVERLAP_GATE','PASS_ACTUAL_O3_OVERLAP' if overlap else 'NOT_PASSED_EARLY_WORKLOADS_NOT_DISPATCHED',{'functional_micro_pass':valid_micro,'overlap':overlap})
 smoke=batch([t for t in tasks[6:9] if overlap or not t['early']],'CPU_CANDIDATE_CHECKSUMS')
 eligible={t['variant'] for t in tasks[6:9] if any(x['label']==t['label'] and x['status'].startswith('PASS_') for x in smoke)}
 groups=[[t for t in tasks[i:i+3] if t['variant'] in eligible] for i in range(9,18,3)];groups=[g for g in groups if g]
 active={};result_index=0;failed=False
 with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
  while groups or active:
   if not failed:
    for group in list(groups):
     if len(active)+len(group)>32:continue
     with (OUT/'COUNT.lock').open('a+') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX);unmarked=[t for t in active.values() if not (OUT/'run_starts'/(t['label']+'.json')).exists()]
      try:r.snapshot(sum(t['timeout_seconds']+5 for t in group+unmarked),len(group+unmarked))
      except AssertionError:continue
     groups.remove(group)
     for t in group:active[pool.submit(dispatch,t)]=t
     print('ADMITTED',','.join(t['label'] for t in group),flush=True)
   if not active:break
   finished,_=concurrent.futures.wait(active,timeout=55,return_when=concurrent.futures.FIRST_COMPLETED)
   for future in finished:
    t=active.pop(future);row=future.result();rows.append(row);failed|=not row['status'].startswith('PASS_')
    with (OUT/'COUNT.lock').open('a+') as lock:
     fcntl.flock(lock,fcntl.LOCK_EX);resource=r.snapshot()
    m.put(BASE/'reports'/('CPU_WORKLOAD_RESULT'+str(result_index)+'.json'),{'task':row,'resources':resource,'plan':m.ref(plan)});result_index+=1;print('COMPLETED',t['label'],row['status'],row.get('cycles'),flush=True)
 seen={x['label'] for x in rows};unrun=[t for t in tasks if t['label'] not in seen]
 save('CPU18_FINAL','PASS_18_CLEAN_O3_COST_CONTROL_NOT_PROTECTION_RANKING' if len(rows)==18 and all(x['status'].startswith('PASS_') for x in rows) and overlap else 'PARTIAL_OR_FAILED_VISIBLE',{'unrun':unrun,'overlap_gate':overlap})
 print('TERMINAL',len(rows),'unrun',len(unrun),'overlap_gate',overlap,flush=True)
if __name__=='__main__':main()
