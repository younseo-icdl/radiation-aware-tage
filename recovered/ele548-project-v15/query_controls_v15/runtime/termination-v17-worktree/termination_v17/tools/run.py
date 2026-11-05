#!/usr/bin/env python3
"""V17 failed-case regressions and then authorized unstarted programs only."""
from pathlib import Path
import argparse,ast,concurrent.futures,hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
V15=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
sys.path.insert(0,str(V15/'tools'))
import run_cpu as original
m=original.m;r=original.r;OUT=r.OUT
def load(p):return json.loads(Path(p).read_text())
def stats(path):return {x.split()[0]:x.split()[1] for x in path.read_text().splitlines() if x.strip() and not x.lstrip().startswith('#') and len(x.split())>=2}
def validate(t,d,code):
 result=original.old.validate(t,d,code)
 initial=load(d/'seu.program_exit.json');final=result['seu'];trace=load(d/'termination_trace.json')
 assert final['early_pending']==final['lookup_pending']==final['source_pending']==0
 assert final['ingress_enqueued']==final['ingress_issued'] and final['early_claimed']==final['early_delivered']
 assert trace['status']=='PASS_ACTUAL_HELPER_COMPLETION_AFTER_PROGRAM_EXIT' and trace['source_cycles_observed']<=64
 assert initial['conserved'] and initial['lookups']==initial['lookup_consumed']+initial['early_pending']
 manifest=load(d/'logical_manifest.json');assert manifest['source_query_L']==t['query_L'] and manifest['source_update_L']==(1 if t['representation']=='direct' else t['update_L'])
 assert manifest['early_unconditional']==t['early'] and manifest['early_checkpoint_bits']==(848 if t['early'] else 0)
 if t.get('failed_reference'):
  oldpath=Path(t['failed_reference']);assert initial==load(oldpath/'seu.json'),'PRE_EXIT_STATE_CHANGED'
  oldstats=stats(oldpath/'stats.txt')
  assert result['cycles']==int(oldstats['system.cpu.numCycles']) and result['simInsts']==int(oldstats['simInsts']) and result['IPC']==float(oldstats['system.cpu.ipc']),'PRE_EXIT_PERFORMANCE_CHANGED'
 reference=load(original.checked(t['architectural_reference']))['seu']
 for key in ('committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash'):assert initial[key]==reference[key],('PRE_EXIT_ARCHITECTURAL_DIFFERENCE',key)
 result['program_exit_seu']=initial;result['termination']=trace;result['performance_boundary']='first program exit; final seu is helper completion observation, not program performance/censoring extension'
 return result
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--phase',choices=('regressions','remaining'),required=True);a=p.parse_args()
 proposal=load(V15/'reports/CPU18_PROPOSAL.lock.json');state=r.snapshot();assert state['caps']['approved']
 candidates=proposal['tasks'][9:];tasks=[]
 if a.phase=='regressions':
  for t in candidates:
   if t['program']=='dijkstra_small' and t['early']:
    old=Path(t['output']);assert load(old/'EXECUTION.json')['status']=='FAIL_RETAINED'
    u=dict(t,label=t['label']+'.terminal_A1',output=str(OUT/(t['label']+'.terminal_A1')),failed_reference=str(old));tasks.append(u)
 else:
  assert load(BASE/'reports/REGRESSIONS_A1.json')['status']=='PASS_TWO_TERMINAL_REGRESSIONS'
  for t in candidates:
   if not (OUT/'run_starts'/(t['label']+'.json')).exists():tasks.append(t)
 assert len(tasks)==(2 if a.phase=='regressions' else 6)
 if not a.run:print(json.dumps({'status':'DRY_RUN_ONLY','phase':a.phase,'labels':[t['label'] for t in tasks],'resources':state},indent=2));return
 assert load(V15/'runtime/CPU18_DISPATCH_A1/TERMINAL.json')['terminal'] and state['outstanding_reservations']==0
 assert load(BASE/'reports/OBSERVER_UNIT_A1.json')['status']=='PASS_OBSERVER_UNIT_ONLY_NOT_O3_TERMINATION'
 binary=original.checked(proposal['binary']);config=BASE/'config/o3_terminal_v17.py';build=load(original.checked(proposal['build']))
 for dep in build['actual_dependencies']:original.checked(dep)
 assert config.read_text().split('import atexit,sys',1)[0]==Path(proposal['config']['path']).read_text().split('if a.initialize_only:\n',1)[0]
 for line in subprocess.check_output(['ps','-u','youns','-o','comm=,args='],text=True).splitlines():
  fields=line.split(None,1);assert not(len(fields)==2 and fields[0].startswith('gem5') and str(binary) in fields[1]),'EXISTING_CPU_STILL_LIVE'
 plan=BASE/'reports'/(a.phase.upper()+'_A1.lock.json')
 m.put(plan,{'status':'FROZEN_BEFORE_EXECUTION','phase':a.phase,'original_proposal':m.ref(V15/'reports/CPU18_PROPOSAL.lock.json'),'authorization':m.ref(r.AUTH),'binary':m.ref(binary),'config':m.ref(config),'observer':m.ref(BASE/'config/terminal_observer.py'),'runner':m.ref(__file__),'tasks':tasks,'original_failed_regressions_are_not_replaced':True,'timing':'identical until first program exit, then <=64 actual helper cycles; first exit stats/censor boundary preserved','resources':state})
 oldplan=load(original.checked(proposal['v14_execution_plan']));source=original.checked(oldplan['runner']);tree=ast.parse(source.read_text());main_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main');one=next(n for n in main_node.body if isinstance(n,ast.FunctionDef) and n.name=='one')
 modified=dict(proposal,config=m.ref(config));scope=vars(original.old).copy();scope.update(BASE=BASE,ROOT=m.ROOT,OUT=OUT,m=m,r=r,binary=binary,config=config,build=build,proposal=modified,plan=plan,validate=validate)
 exec(compile(ast.Module(body=[one],type_ignores=[]),str(source),'exec'),scope)
 rows=[]
 if a.phase=='regressions':
  r.snapshot(sum(t['timeout_seconds']+5 for t in tasks),2)
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(scope['one'],tasks))
 else:
  # One active output reservation, exact original unstarted cases. Changing
  # dispatch parallelism never changes any per-case input/seed/timeout/argument.
  for t in tasks:
   try:r.snapshot(t['timeout_seconds']+5,1)
   except AssertionError:print('STOP_RESOURCE_BEFORE',t['label'],flush=True);break
   row=scope['one'](t);rows.append(row);print('COMPLETED',t['label'],row['status'],row.get('cycles'),flush=True)
   if not row['status'].startswith('PASS_'):break
 good=len(rows)==len(tasks) and all(x['status'].startswith('PASS_') for x in rows)
 status=('PASS_TWO_TERMINAL_REGRESSIONS' if a.phase=='regressions' else 'PASS_SIX_REMAINING_PROGRAMS') if good else 'FAIL_OR_PARTIAL_PRESERVED'
 m.put(BASE/'reports'/('REGRESSIONS_A1.json' if a.phase=='regressions' else 'REMAINING_A1.json'),{'status':status,'rows':rows,'unrun':[t for t in tasks if t['label'] not in {x['label'] for x in rows}],'plan':m.ref(plan),'resources':r.snapshot()})
 print(status,len(rows),flush=True)
if __name__=='__main__':main()
