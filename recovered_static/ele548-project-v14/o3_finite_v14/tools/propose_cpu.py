#!/usr/bin/env python3
"""Freeze exact clean checksum/program cases; launches no CPU simulation."""
from pathlib import Path
import datetime,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 m.budget();oldplan=m.V11/'overwrite_v11/reports/CPU_REGRESSION_PLAN.lock.json';old=json.loads(oldplan.read_text());tasks=[]
 checksum=Path('/home/youns/workspace/ele548-project/build/checksum_freestanding');expected=Path('/home/youns/workspace/ele548-project/reports/native_freestanding_checksum2.log')
 assert m.sha(checksum)=='d51408b0f09f4d9ad811066707f532cd98ff9c27e1b12f5abe748608f2170f66' and expected.read_bytes()==b'checksum=1321703870693\n'
 reps=['recurrent','direct','overwrite'];target=BASE/'runtime/gem5_measured_B1/gem5.finite_measured.opt';config=BASE/'gem5_overlay/o3_finite_v14.py'
 for rep in reps:
  for L in [1,2]:
   tasks.append({'label':'checksum.'+rep+'.L'+str(L),'kind':'CHECKSUM','program':'checksum','R':None,'representation':rep,'source_L':L,'program_binary':m.ref(checksum),'expected_stdout':m.ref(expected),'input':None,'timeout_seconds':180,'reference_CPU_cycles':340433})
 # First2 are the correctness/speed pilot. Remaining4 only after both pass.
 tasks.sort(key=lambda t:(0 if t['source_L']==1 and t['representation'] in ['recurrent','direct'] else 1,t['label']))
 for program in ['qsort_small','dijkstra_small','sha1']:
  original=next(t for t in old['tasks'] if t['program']==program and t['R']==1)
  stats=m.V11/'overwrite_v11/runtime/cpu_regression'/(program+'.R1.OVERWRITE')/'stats.txt'
  cycles=int(next(line.split()[1] for line in stats.read_text().splitlines() if line.startswith('system.cpu.numCycles ')))
  for L in [1,2]:
   for rep in reps:
    tasks.append({'label':program+'.R1.'+rep+'.L'+str(L),'kind':'PROGRAM','program':program,'R':1,'representation':rep,'source_L':L,'program_binary':original['program_binary'],'input':original['control'],'expected_stdout':original['expected_stdout'],'reference_CPU_cycles':cycles,'timeout_rule':'ceil(max120, 3*reference_C0_cycles*slowest_checksum_seconds_per_source_cycle); <=3600; fixed after checksum6 before program starts'})
 for t in tasks:
  for k in ['program_binary','input','expected_stdout']:
   if t[k]:assert m.sha(t[k]['path'])==t[k]['sha256']
  t['arguments']=['--binary',t['program_binary']['path'],*(['--input',t['input']['path']] if t['input'] else []),'--representation',t['representation'],'--source-latency',str(t['source_L']),'--execute']
  t['output']=str(BASE/'runtime/cpu_trials'/t['label'])
 assert len(tasks)==24
 obj=BASE/'reports/MEASURED_OBJECTS_B1.json';assert json.loads(obj.read_text())['status']=='PASS_MEASURED_FOUR_OBJECTS_NOT_LINKED_OR_CPU_EXECUTED'
 native=m.invoke('native_checksum_B1',[checksum]);assert Path(native['stdout']['path']).read_bytes()==expected.read_bytes()
 m.put(BASE/'reports/CPU_EXECUTION_PROPOSAL_B1.lock.json',{'status':'PREPARED_NOT_AUTHORIZED_NOT_EXECUTED','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'requested':{'CPU_global_before':3487,'CPU_cap':3513,'primary_CPU':24,'reserve_CPU':2,'recent_coreh_before':2.5,'recent_coreh_cap':5,'recent_MiB_before':192,'recent_MiB_cap':320,'all_worktrees_GiB_cap':8,'all_v9_onward_coreh_cap':16,'global_recorded_coreh_cap':108,'shared_slots_cap':32,'CPU_phase_coreh_initial_cap':3.5},'actual_producer_A1':m.ref(BASE/'reports/CPU_BUILD_A1.json'),'measured_objects':m.ref(obj),'pending_measured_binary':str(target),'config':m.ref(config),'runner':m.ref(BASE/'tools/run_cpu.py'),'resource_guard':m.ref(BASE/'tools/resources.py'),'link_tool':m.ref(BASE/'tools/link_measured.py'),'initialize_tool':m.ref(BASE/'tools/initialize.py'),'native_gate':m.ref(BASE/'reports/CONTROLLER_GATE_B1.json'),'ack_metadata_gate':m.ref(BASE/'reports/recovery_A1.json'),'initialization_only_gate':m.ref(BASE/'reports/INITIALIZATION_A1.json'),'native_checksum':native,'old_case_reference':m.ref(oldplan),'tasks':tasks,'RNG_seed':548,'faults':0,'fault_contract':'No change to old event tapes/rates; no fault simulation in this request. Existing S*346 P0/P_ED/ECC/TMR and frequent/periodic/native results preserved. New backend currently P0 only; this is correctness/resource comparison, not final protection-method ranking.','statistics_scope':'Exposed existing R1 inputs, deterministic clean regression. Not independent holdout or paired-fault A/B/C/D; no confidence interval from these repetitions.','reserve_rule':'At most2 failed-stage regression retries only with preserved failure and newly frozen source/config plus updated correctness gate; never overwrite/relabel an old result. Runner primary path has no automatic retries.','execution_order':'After approval: link measured B1, verify immutable inputs, new tick0 initialization, first2checksum serial-reserved pilot (parallel2); if pass remaining4 checksum, freeze workload host-time bounds, then all18 program cases under time/disk/shared32 limits. Insufficient reserve stops before dispatch with exact unrun commands.','host_estimate':'2..3.5 core-hours planning estimate from C++ source-clock gates and old CPU cycle counts; NOT measured new O3 runtime. Refine after checksum6.','resources':m.budget()})
 print('PREPARED_NOT_AUTHORIZED_NOT_EXECUTED: CPU3487->3513, recent2.5->5coreh,192->320MiB; primary24+reserve2')
if __name__=='__main__':main()
