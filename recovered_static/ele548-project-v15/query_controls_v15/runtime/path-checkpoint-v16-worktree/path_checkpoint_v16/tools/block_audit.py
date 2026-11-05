#!/usr/bin/env python3
"""Verify the recurring budget blocker. Never dispatch simulations."""
from pathlib import Path
import datetime,hashlib,json,subprocess,sys
sys.dont_write_bytecode=True
B=Path(__file__).resolve().parents[1]
V15=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
def ref(path):
 p=Path(path);return {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def write(path,value):
 with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def main():
 out=B/'runtime/goal_blocked_audit_A2';out.mkdir(exist_ok=False)
 command=['/home/youns/workspace/ele548-project-v10/.venv/bin/python','-B','query_controls_v15/tools/run_cpu.py']
 # A1 failed because the immutable guard read this wrapper's not-yet-written
 # *.time. Publish the file only once GNU time has completed; retain A1.
 inflight=out/'job.time.inflight'
 with (out/'stdout').open('x') as stdout,(out/'stderr').open('x') as stderr:
  result=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(inflight),*command],cwd=V15.parent,stdout=stdout,stderr=stderr)
 inflight.rename(out/'job.time')
 assert result.returncode==0,'SECOND_AUDIT_FAILURE_STOP_NO_FURTHER_FIX'
 dry=json.loads((out/'stdout').read_text());r=dry['resources']
 assert dry['status']=='DRY_RUN_NO_CPU_DISPATCH' and r['CPU_global']==3511 and r['CPU_new']==0 and r['outstanding_reservations']==0 and not r['caps']['approved']
 assert not (V15/'reports/CPU_AUTHORIZATION.lock.json').exists()
 live=[]
 for line in subprocess.check_output(['ps','-u','youns','-o','pid=,comm=,args='],text=True).splitlines():
  parts=line.strip().split(None,2)
  if len(parts)!=3:continue
  pid,comm,args=parts
  if comm.startswith(('gem5','protocol_')) or comm in ('cc1plus','g++') or comm.startswith('python') and 'query_controls_v15/tools/run_cpu.py --run' in args:live.append(line)
 assert not live,live
 for row in json.loads((B/'reports/PRESERVATION.lock.json').read_text())['preserved']:
  assert ref(row['path'])['sha256']==row['sha256']
 failure=B/'runtime/goal_blocked_audit_A1'
 audit={'status':'BLOCKED_AUDIT_SATISFIED_PENDING_EXISTING_CPU_BUDGET_REPLY','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'not_complete':True,
 'previous_goal_turn_classification':'PROGRESS: new path-only C++ implementation and executed gates; CPU18 remains unapproved',
 'recurring_condition':'No human reply to the already-presented CPU18 budget amendment. Original CPU3513 cap retains two failed-regression-only slots; automatic continuation does not amend it.',
 'consecutive_goal_turns':[{'turn':'v15 preparation','classification':'progress','condition_present':True,'evidence':ref(V15/'reports/USER_ACTIONS_REQUIRED.md')},{'turn':'v16 path-only C++ control','classification':'progress','condition_present':True,'evidence':ref(B/'reports/USER_ACTIONS_REQUIRED.md')},{'turn':'current continuation','classification':'no progress; authoritative blocker revalidation only','condition_present':True}],
 'current_state':{'command':command,'exit_code':result.returncode,'stdout':ref(out/'stdout'),'stderr':ref(out/'stderr'),'time':ref(out/'job.time'),'live_simulations_or_builds':live,'CPU_authorization_present':False,'resources':r,'preserved_originals_match':True},
 'independent_execution_unavailable':{'failed_regression_reserve':2,'actual_failed_new_CPU_stage':False,'CPP_preparation_disk_MiB':r['preparation_MiB'],'CPP_existing_gate_reservation_MiB':2,'sum_MiB':r['preparation_MiB']+2,'cap_MiB':240,'note':'Do not relabel candidates as failed-stage regressions, delete preserved files or create a new producer to reset accounting.'},
 'audit_wrapper_failure_preserved':{'attempt':'A1','CPU_started':False,'exception':'IndexError from reading the still-active wrapper time file','stderr':ref(failure/'stderr'),'stdout':ref(failure/'stdout'),'time':ref(failure/'job.time'),'fix1':'Keep the timing filename outside *.time until the command exits. Frozen budget guard/source/config/binary unchanged.'},
 'required_action_already_pending':{'proposal':ref(V15/'reports/CPU18_PROPOSAL.lock.json'),'proposed_not_approved':{'CPU_cap':3531,'recent_coreh':8,'v9_onward_coreh':19,'CPU_phase_coreh':4},'retained':{'global_coreh':108,'recent_disk_MiB':320,'all_root_GiB':8,'slots':32},'resume_command':'cd /home/youns/workspace/ele548-project-v15 && /home/youns/workspace/ele548-project-v10/.venv/bin/python -B query_controls_v15/tools/run_cpu.py --run','requires':'Actual human reply recorded with original proposal SHA in CPU_AUTHORIZATION.lock.json; never substitute v16 for v15.'},
 'goal_unachieved':['Actual O3 overlap and clean cost controls','Fair finite-port P_ED/SECDED/TMR comparison','SOURCE/WHOLE paired A/B/C/D with original fault/RNG/time/censoring and independent evaluation','Consumer routing/metadata scope and defensible hardware candidate decision'],
 'new_permission_question_sent':False}
 target=B/'reports/GOAL_BLOCKED_AUDIT_A2.json';write(target,audit)
 print(json.dumps({'audit':ref(target),'actual_CPU':r['CPU_global'],'CPU_cap':r['CPU_cap'],'live':live,'approved':False},indent=2))
if __name__=='__main__':main()
