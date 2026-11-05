#!/usr/bin/env python3
"""Freeze18 exact CPU cases and prospective budgets, launch none."""
import datetime,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
import prepare as m
BASE=m.BASE
def load(p):return json.loads(Path(p).read_text())
def main():
 m.budget();m.preserve();build=BASE/'reports/CPU_BUILD_A1.json';init=BASE/'reports/INITIALIZATION_A1.json'
 assert load(build)['status']=='PASS_NEW_BINARY_BUILD_NOT_CPU_EXECUTED' and load(init)['status']=='PASS_15_TICK0_CONFIGS_NOT_CPU_EXECUTION'
 for item in load(build)['actual_dependencies']:assert m.sha(item['path'])==item['sha256']
 old=load(m.V14/'reports/CPU_EXECUTION_PROPOSAL_B1.lock.json');micro=load(BASE/'reports/MICRO_NATIVE_A1.json');checksum=old['tasks'][0]
 config=BASE/'gem5_overlay/o3_query_v15.py';tasks=[]
 def add(label,stage,program,rep,Q,U,early,elf,input_,expected,timeout,variant,regression=None,arch=None):
  for ref in [elf,input_,expected,regression,arch]:
   if ref:assert m.sha(ref['path'])==ref['sha256']
  args=['--binary',elf['path'],*(['--input',input_['path']] if input_ else []),'--representation',rep,'--query-latency',str(Q),'--update-latency',str(U),*(['--early-unconditional'] if early else []),'--execute']
  tasks.append({'label':label,'stage':stage,'program':program,'representation':rep,'query_L':Q,'update_L':U,'source_L':Q,'early':early,'variant':variant,'program_binary':elf,'input':input_,'expected_stdout':expected,'timeout_seconds':timeout,'arguments':args,'output':str(BASE/'runtime/cpu_trials'/label),'regression_reference':regression,'architectural_reference':arch})
 for rep in ['recurrent','direct']:
  reference=m.ref(m.V14/'runtime/cpu_trials'/('checksum.'+rep+'.L1')/'EXECUTION.json')
  add('backward.checksum.'+rep,'BACKWARD2','checksum',rep,1,1,False,checksum['program_binary'],None,checksum['expected_stdout'],180,'BACKWARD',reference,reference)
 for rep in ['recurrent','direct']:
  for early in [False,True]:add('micro.'+rep+'.E'+str(int(early)),'MICRO4','pipeline_micro',rep,2,1,early,micro['binary'],None,micro['expected_stdout'],180,'MICRO')
 variants=[('QUERY_REC_Q2U1','recurrent',2,False),('EARLY_REC_Q1U1','recurrent',1,True),('EARLY_DIRECT_Q1U1','direct',1,True)]
 ref=m.ref(m.V14/'runtime/cpu_trials/checksum.recurrent.L1/EXECUTION.json')
 for name,rep,Q,early in variants:add('checksum.'+name,'CANDIDATE3','checksum',rep,Q,1,early,checksum['program_binary'],None,checksum['expected_stdout'],180,name,arch=ref)
 for program,timeout in [('dijkstra_small',3600),('qsort_small',1800),('sha1',600)]:
  original=next(t for t in old['tasks'] if t['program']==program)
  reference=m.ref(m.V14/'runtime/cpu_trials'/(program+'.R1.recurrent.L1')/'EXECUTION.json')
  for name,rep,Q,early in variants:add(program+'.R1.'+name,'PROGRAM9',program,rep,Q,1,early,original['program_binary'],original['input'],original['expected_stdout'],timeout,name,arch=reference)
 assert len(tasks)==18 and len({t['label'] for t in tasks})==18
 plan=BASE/'reports/CPU18_PROPOSAL.lock.json'
 m.put(plan,{'status':'PREPARED_NOT_AUTHORIZED_NOT_EXECUTED','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requested':{'actual_CPU_before':3511,'old_cap':3513,'new_cap':3531,'primary_new_CPU':18,'existing_failed_stage_reserve':2,'recent_coreh_cap_old':5,'recent_coreh_cap':8,'v9_coreh_cap_old':16,'v9_onward_coreh_cap':19,'CPU_phase_coreh_cap':4,'global_coreh_cap':108,'recent_disk_MiB_cap':320,'all7_roots_GiB_cap':8,'build_jobs':2,'shared_CPU_slots':32},'binary':load(build)['binary'],'build':m.ref(build),'config':m.ref(config),'initialization':m.ref(init),'query_gate':m.ref(BASE/'reports/query_gate_A1.json'),'early_gate':m.ref(BASE/'reports/early_gate_A2.json'),'native_micro':m.ref(BASE/'reports/MICRO_NATIVE_A1.json'),'v14_execution_plan':m.ref(m.V14/'reports/CPU24_PLAN.lock.json'),'runner':m.ref(BASE/'tools/run_cpu.py'),'resource_guard':m.ref(BASE/'tools/resources_cpu.py'),'tasks':tasks,'seed':548,'fault_events':0,'event_contract':'No new fault schedules. Existing S*346 P0/P_ED/ECC/TMR/whole/source-informed contracts preserved. This P0 clean source/front-end control does not rank recovery schemes.','host_estimate':'Planning only1.5..3.5 recorded coreh; hard CPU phase4. Timeouts fixed before CPU: checksums/micro180s, dijkstra3600s, qsort1800s, sha600s, same across variants. Longest complete group reserves3*(3600+5)=3.0042coreh; staged checksums plus this group fit4coreh. Dynamic complete-group admission charges full outstanding reservations. No automatic retry.','execution_order':'Backward checksum2 parallel2 exact v14 cycles/RNG/path/counters -> micro4 functional/actual overlap -> candidate checksums3 -> qualified variant program groups, largest first, up to32shared leases. Failed/unexercised early gate leaves early workloads unrun; pure-query work can continue. Failed program stage stops new workload dispatch while admitted jobs finish.','statistics_scope':'Exposed R1 development inputs, deterministic clean seed548. Micro is synthetic, not HW1 representative workload. No B-D/paired fault CI or independent holdout claims.','storage_scope':'Extra848 actual early metadata bits included; CPU-owned BI payload and host pointer association explicitly excluded. Global retirement/squash checkpoint barrier conservative; four added97-bit mirrored-SECDED decode/write paths assumed to fit normal stage. Trial bytes excluded only from preparation-only disk sublimit; still all charged to recent320MiB and all-root8GiB.','resources':m.budget()})
 print('PREPARED18_NOT_EXECUTED',m.ref(plan))
if __name__=='__main__':main()
