"""Fail-closed authorized v18 phase dispatcher. No implicit retries or cap reset."""
import os,sys,pathlib,concurrent.futures,math,json,re
sys.dont_write_bytecode=True
os.environ['V18_PRODUCER']='B2'
import campaign as p
c=p.c;r=p.r;B=p.B

def execute(name,tasks,pilot=None):
 lock=B/'runtime/configs'/(name+'_FULL.lock.json')
 if lock.exists():assert r.load(lock)['tasks']==tasks
 else:r.put(lock,{'status':'FROZEN_BEFORE_FIRST_DISPATCH','tasks':tasks,'source_tools':[r.ref(B/'tools'/z) for z in ('run_round.py','campaign.py','analyze.py')],'authority':r.ref(r.AUTH)})
 existing=[];pending=[]
 for t in tasks:
  out=pathlib.Path(t['output'])
  if (out/'EXECUTION.json').exists():existing.append(r.load(out/'EXECUTION.json'))
  else:
   assert not out.exists(),('STARTED_TASK_WITHOUT_TERMINAL_RECORD',t['label']);pending.append(t)
 assert all(x['status'].startswith('PASS') for x in existing),('PRIOR_FAILED_STAGE_RETAINED',name)
 if pilot:
  first=[x for x in pending if pilot(x)]
  assert len(first) in (0,2)
  if first:
   good,rows=c.batch(name+'_INITIAL2',first,2)
   if not good:raise RuntimeError(('PILOT_FAILED',name))
   peak=max(int((pathlib.Path(x['task']['output'])/'gem5.time').read_text().splitlines()[-1].split()[2]) for x in rows);available=next(int(x.split()[1]) for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'));assert peak*32<available/2,'PILOT_MEMORY'
   r.put(B/'reports'/(name+'_PILOT_SPEED.json'),{'status':'PASS_OBSERVED_NOT_FULL_ROUND_GUARANTEE','CPU':2,'host_seconds':[x['host_cpu_seconds'] for x in rows],'max_rss_kib':peak,'shared_max_workers':32,'source':r.ref(B/'reports'/(name+'_INITIAL2.json'))});existing+=rows;pending=[x for x in pending if x not in first]
 offset=len(existing)
 while pending:
  state=r.snapshot();width=min(32,len(pending),int((160-state['round_recorded_coreh'])*3600//3605));assert width>0,'ACTUAL_COREH_LIMIT_NO_NEW_TRIAL'
  batch=pending[:width];good,rows=c.batch(name+'_CHUNK_'+str(offset),batch,width);existing+=rows;offset+=len(rows);pending=pending[width:]
  print(name,'TERMINAL',len(existing),'/',len(tasks),'failures',sum(not x['status'].startswith('PASS') for x in existing),flush=True)
  if not good:raise RuntimeError(('AFFECTED_STAGE_FAILED_RAW_RETAINED',name,[x['label'] for x in rows if not x['status'].startswith('PASS')]))
 for row in existing:
  assert not re.search(r'unimplemented syscall|ignoring syscall|instruction .*unimplemented',(pathlib.Path(row['task']['output'])/'gem5.log').read_text(),re.I),('UNSUPPORTED_NOT_SUCCESS',row['label'])
 r.put(B/'reports'/(name+'_COMPLETED.json'),{'status':'PASS','actual_runs':len(existing),'runs':[r.ref(pathlib.Path(x['task']['output'])/'EXECUTION.json') for x in existing],'plan':r.ref(lock),'resources':r.snapshot()});return existing

def run():
 assert r.load(B/'reports/G2_ACCEPTANCE.json')['status'].startswith('PASS')
 preg=r.load(B/'reports/COHORT_PREREGISTRATION.lock.json');actual=r.snapshot();assert actual['active']==0
 # Development clean speed/answer pilot precedes expanded concurrency.
 clean=execute('DEV_CLEAN',p.clean_tasks('DEV'),lambda t:t['program']=='qsort_small' and t['method'] in ('P0','P_ECC'));p.clean_accept('DEV')
 forecast={name:{x['method']:x['host_cpu_seconds'] for x in clean if x['program']==name} for name in ('qsort_small','dijkstra_small','sha1')}
 r.put(B/'reports/DEVELOPMENT_NORMAL_RUNTIME.json',{'status':'OBSERVED_THREE_PROGRAMS_SIX_METHODS','host_seconds':forecast,'remaining_proposal_not_a_guarantee':True,'resources':r.snapshot()})
 execute('DEV_SERIAL',p.clean_tasks('DEV','SERIAL'));execute('DEV_L2',p.clean_tasks('DEV','L2'))
 import native_reference
 native_reference.run()
 tasks=p.fault_plan('DEV');execute('DEV_FAULT',tasks,lambda t:t['program']=='qsort_small' and t['method'] in ('P0','P_ECC') and t['scenario']==p.SCENARIOS[1] and t['owner']=='DEV.0.1.0')
 import analyze
 analysis=analyze.summarize('DEV');r.put(B/'reports/DEV_ANALYSIS.json',analysis)
 freeze={'status':'FIXED_BEFORE_INDEPENDENT_INPUT_CPU_OR_FAULT_RESULTS','producer':r.ref(B/'reports/PRODUCER_B2.lock.json'),'methods':c.config.METHODS,'resource_contract':r.ref(B/'docs/02_IMPLEMENTED_RESOURCE_CONTRACT.ko.md'),'development':r.ref(B/'reports/DEV_ANALYSIS.json'),'cohort_owner_input_registry':r.ref(B/'reports/COHORT_PREREGISTRATION.lock.json'),'evaluation_owners_per_program_scenario':8,'no_evaluation_policy_tuning':True,'required_SSTAR_baselines':list(c.config.METHODS)[:-1],'SOURCE_WHOLE_all6':list(c.config.METHODS),'serial_control':'early conditional/unconditional CPU response wait; same source/update/check/encode/provider resources; not a different journal','statistic':'paired-owner B-D cycles and (B-D)/A, bootstrap95, exact sign/Holm within program/scenario; no zero imputation'}
 r.put(B/'reports/CANDIDATE_EVALUATION_FROZEN.lock.json',freeze)
 execute('EVAL_CLEAN',p.clean_tasks('EVAL'));p.clean_accept('EVAL');tasks=p.fault_plan('EVAL');execute('EVAL_FAULT',tasks);analysis=analyze.summarize('EVAL');r.put(B/'reports/EVAL_ANALYSIS.json',analysis)
 r.put(B/'reports/FINITE_MATRIX_COMPLETED.json',{'status':'ALL_FINITE_PIPELINE_DEVELOPMENT_EVALUATION_TERMINAL','native_reference6_complete_and_separate':True,'resources':r.snapshot()})
if __name__=='__main__':
 try:run()
 except Exception as exc:
  import traceback
  target=B/'reports'/('ROUND_STOP_'+str(len(list((B/'runtime/run_starts').glob('*.json'))))+'.json');r.put(target,{'status':'STOPPED_AFFECTED_STAGE_WITH_RAW_RETAINED','exception':repr(exc),'traceback':traceback.format_exc(),'resources':r.snapshot()});raise
