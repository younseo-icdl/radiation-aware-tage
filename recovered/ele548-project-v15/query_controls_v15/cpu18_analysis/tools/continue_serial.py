#!/usr/bin/env python3
"""Only unstarted members of authorized CPU18, after old dispatcher ends."""
from pathlib import Path
import argparse,ast,json,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BASE/'tools'))
import run_cpu as original
m=original.m;r=original.r;OUT=r.OUT
def load(p):return json.loads(Path(p).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');a=p.parse_args()
 proposal=load(BASE/'reports/CPU18_PROPOSAL.lock.json');assert len(proposal['tasks'])==18
 if not a.run:
  print(json.dumps({'status':'PREPARED_FALLBACK_NOT_EXECUTED','requires':'Original dispatcher terminal evidence; all admitted trials terminal and PASS; no new case or retry','resources':r.snapshot()},indent=2));return
 terminal=BASE/'runtime/CPU18_DISPATCH_A1/TERMINAL.json';assert terminal.exists(),'ORIGINAL_DISPATCHER_NOT_TERMINAL'
 assert load(terminal)['terminal'] is True
 assert r.snapshot()['caps']['approved'] and r.snapshot()['outstanding_reservations']==0
 binary=original.checked(proposal['binary']);config=original.checked(proposal['config']);build=load(original.checked(proposal['build']))
 for dep in build['actual_dependencies']:original.checked(dep)
 for line in subprocess.check_output(['ps','-u','youns','-o','comm=,args='],text=True).splitlines():
  fields=line.split(None,1)
  assert not (len(fields)==2 and fields[0].startswith('gem5') and str(binary) in fields[1]),'OLD_CPU_PROCESS_STILL_LIVE'
 assert load(BASE/'reports/CPU_OVERLAP_GATE.json')['extra']['overlap']
 assert load(BASE/'reports/CPU_CANDIDATE_CHECKSUMS.json')['status']=='PASS_FUNCTIONAL_PHASE'
 tasks=proposal['tasks'];existing=[];unstarted=[]
 for t in tasks:
  marker=OUT/'run_starts'/(t['label']+'.json');result=Path(t['output'])/'EXECUTION.json'
  if marker.exists():
   assert result.exists(),'STARTED_CASE_NOT_TERMINAL';row=load(result);assert row['status'].startswith('PASS_'),'ACTUAL_FAILED_STAGE_NO_RETRY';existing.append(row)
  else:
   assert not Path(t['output']).exists(),'UNMARKED_OUTPUT_REQUIRES_REVIEW';unstarted.append(t)
 assert all(t['stage']=='PROGRAM9' for t in unstarted),'EARLY_GATES_NOT_FINISHED'
 assert unstarted,'ALL_AUTHORIZED_CASES_ALREADY_FINISHED'
 plan=BASE/'reports/CPU18_SERIAL_FOLLOWON.lock.json'
 m.put(plan,{'status':'SAME_AUTHORIZED_UNSTARTED_CASES_SERIAL_DISK_RESERVATION','proposal':m.ref(BASE/'reports/CPU18_PROPOSAL.lock.json'),'authorization':m.ref(r.AUTH),'original_terminal':m.ref(terminal),'original_execution':m.ref(BASE/'reports/CPU18_EXECUTION.lock.json'),'followon':m.ref(__file__),'unstarted_labels':[t['label'] for t in unstarted],'change':'One active trial at a time, same finite resource guard and original exact trial function. Same inputs/seed548/config/ELF/timeout/arguments; no retries, no existing output changes. Group CPU timeout budgets retained; only one active output reservation needed.','resources':r.snapshot()})
 oldplan=load(original.checked(proposal['v14_execution_plan']));runner=original.checked(oldplan['runner']);tree=ast.parse(runner.read_text());main=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='main');one=next(x for x in main.body if isinstance(x,ast.FunctionDef) and x.name=='one')
 scope=vars(original.old).copy();scope.update(BASE=BASE,ROOT=m.ROOT,OUT=OUT,m=m,r=r,binary=binary,config=config,build=build,proposal=proposal,plan=plan,validate=original.validate)
 exec(compile(ast.Module(body=[one],type_ignores=[]),str(runner),'exec'),scope)
 for program in dict.fromkeys(t['program'] for t in unstarted):
  group=[t for t in unstarted if t['program']==program]
  try:r.snapshot(sum(t['timeout_seconds']+5 for t in group),1)
  except AssertionError:print('STOP_GROUP_RESERVATION',program,flush=True);break
  failed=False
  for t in group:
   try:r.snapshot(t['timeout_seconds']+5,1)
   except AssertionError:print('STOP_SERIAL_RESERVATION',t['label'],flush=True);failed=True;break
   row=scope['one'](t);existing.append(row);print('SERIAL_COMPLETED',t['label'],row['status'],row.get('cycles'),flush=True)
   if not row['status'].startswith('PASS_'):failed=True;break
  if failed:break
 seen={x['label'] for x in existing};unrun=[t for t in tasks if t['label'] not in seen]
 existing.sort(key=lambda x:next(i for i,t in enumerate(tasks) if t['label']==x['label']))
 status='PASS_18_CLEAN_O3_COST_CONTROL_NOT_PROTECTION_RANKING' if len(existing)==18 and all(x['status'].startswith('PASS_') for x in existing) else 'PARTIAL_OR_FAILED_VISIBLE'
 m.put(BASE/'reports/CPU18_SERIAL_FINAL.json',{'status':status,'tasks':existing,'plan':m.ref(plan),'extra':{'unrun':unrun,'overlap_gate':True},'resources':r.snapshot()})
 print('SERIAL_TERMINAL',len(existing),'unrun',len(unrun),flush=True)
if __name__=='__main__':main()
