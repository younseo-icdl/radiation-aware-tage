#!/usr/bin/env python3
"""Budgeted CPU correctness/resource cohort, no automatic retries.
Default is read-only --dry-run. --run requires actual new user authorization.
"""
from pathlib import Path
import argparse,concurrent.futures,datetime,fcntl,importlib.util,json,math,os,re,subprocess,sys,time,traceback
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;OUT=BASE/'runtime/cpu_trials'
def mod(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=mod('bounded',BASE/'tools/prepare.py');r=mod('resources',BASE/'tools/resources.py')
prior=mod('shared_slots',m.V10/'native_lifetime_next/tools/lifetime_runner.py')
def load(p):return json.loads(Path(p).read_text())
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def checked(v):assert m.sha(v['path'])==v['sha256'],('CHANGED_BINDING',v['path']);return Path(v['path'])
def atomic(p,v):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(v,indent=2)+'\n');assert not p.exists();os.replace(tmp,p)
def validate(t,d,exit_code):
 assert exit_code==0,'SIMULATOR_FAILURE_OR_TIMEOUT'
 assert (d/'program.stdout').read_bytes()==checked(t['expected_stdout']).read_bytes(),'PROGRAM_CHECKSUM_MISMATCH'
 assert not (d/'program.stderr').read_bytes(),'PROGRAM_STDERR'
 text=(d/'gem5.log').read_text();assert 'Exit cause: exiting with last active thread context code: 0 tick:' in text,'UNEXPECTED_EXIT'
 for line in text.splitlines():
  if re.search(r'unsupported|unimplemented|ignoring syscall',line,re.I):
   assert re.fullmatch(r'src/sim/syscall_emul\.hh:816: warn: Unsupported ioctl call \(return ENOTTY\): ioctl\(1, 0x5413, \.\.\.\) @ \(0x[0-9a-f]+=>0x[0-9a-f]+\)\.\(0=>1\)',line),'UNKNOWN_UNSUPPORTED_WARNING'
 s=load(d/'seu.json');assert s['conserved'] and s['applied_faults']==0 and s['lookups']==s['lookup_consumed']
 assert s['lookup_accepted']==s['lookup_consumed']+s['lookup_cancelled']+s['lookup_pending']
 assert s['source_accepted']==s['source_completed']+s['source_cancelled']+s['source_pending']
 assert s['tick']>0 and s['source_cycles']==s['tick']//500 and s['max_lookup_pending']>0
 stats={line.split()[0]:line.split()[1] for line in (d/'stats.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#') and len(line.split())>=2}
 cycles=int(stats['system.cpu.numCycles']);insts=int(stats['simInsts']);assert cycles>0 and insts>0
 ipc=float(stats.get('system.cpu.ipc',str(insts/cycles)))
 return {'cycles':cycles,'simInsts':insts,'IPC':ipc,'seu':s,'lookup_consumed_per_source_cycle':s['lookup_consumed']/s['source_cycles'],'note':'stall calls may overlap, not a causal CPI decomposition; synthetic independent II1 is separate from the real next-PC stream'}
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--dry-run',action='store_true');a=p.parse_args()
 proposal_path=BASE/'reports/CPU_EXECUTION_PROPOSAL_B1.lock.json';proposal=load(proposal_path);assert proposal['status']=='PREPARED_NOT_AUTHORIZED_NOT_EXECUTED';assert len(proposal['tasks'])==24
 if not a.run:
  print(json.dumps({'status':'DRY_RUN_NO_CPU_DISPATCH','proposal':m.ref(proposal_path),'primary_cases':24,'reserve':2,'caps':r.caps(),'next_after_user_approval':['link_measured.py','initialize.py --attempt B1 --build-report MEASURED_BINARY_B1.json','run_cpu.py --run']},indent=2));return
 assert r.caps()['approved'],'USER_BUDGET_APPROVAL_REQUIRED_NO_CPU_DISPATCH';auth=load(r.APPROVAL);checked(auth['proposal']);assert auth['proposal']['sha256']==m.sha(proposal_path)
 assert not OUT.exists(),'DO_NOT_RESTART_FROZEN_COHORT'
 binary_report=BASE/'reports/MEASURED_BINARY_B1.json';build=load(binary_report);binary=checked(build['binary']);config=checked(proposal['config'])
 init=load(BASE/'reports/INITIALIZATION_B1.json');assert init['status']=='PASS_SIX_TICK0_OBJECT_CONFIGS_NOT_O3_FUNCTIONAL_GATE'
 assert load(checked(init['plan']))['build']['sha256']==m.sha(binary_report)
 for item in build['actual_dependencies']:checked(item)
 OUT.mkdir();(OUT/'run_starts').mkdir();rows=[];tasks=proposal['tasks']
 plan=BASE/'reports/CPU24_PLAN.lock.json';m.put(plan,{'status':'USER_AUTHORIZED_FROZEN_BEFORE_CPU24','proposal':m.ref(proposal_path),'authorization':m.ref(r.APPROVAL),'binary':m.ref(binary),'config':m.ref(config),'runner':m.ref(Path(__file__)),'tasks':tasks,'shared_slot_validator':m.ref(m.V10/'native_lifetime_next/tools/lifetime_runner.py'),'phase':'Clean correctness/resource regression, existing exposed inputs; P0 only, not final protection comparison','resources':r.snapshot()})
 def one(t):
  with prior.slot() as lease:
   with (OUT/'COUNT.lock').open('a+') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX);r.snapshot(t['timeout_seconds']+5,1);assert len(list((OUT/'run_starts').glob('*.json')))<24
    for key in ['program_binary','input','expected_stdout']:
     if t[key]:checked(t[key])
    assert m.sha(binary)==build['binary']['sha256'] and m.sha(config)==proposal['config']['sha256']
    m.put(OUT/'run_starts'/(t['label']+'.json'),{'label':t['label'],'started':now(),'plan':m.ref(plan),'reserved_cpu_seconds':t['timeout_seconds']+5})
   d=Path(t['output']);d.mkdir(exist_ok=False);affinity=sorted(os.sched_getaffinity(0));assert len(affinity)>=32;cpu=affinity[lease]
   command=[str(binary),'--outdir='+str(d),str(config),*t['arguments']];env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
   row={'label':t['label'],'program':t['program'],'representation':t['representation'],'source_L':t['source_L'],'status':'FAIL_RETAINED','cycles':None,'command':command,'host_core':cpu,'started':now()};start=time.perf_counter()
   try:
    with (d/'gem5.log').open('x') as log:
     result=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'gem5.time'),'/usr/bin/prlimit','--core=0','--fsize=524288','--','/usr/bin/taskset','-c',str(cpu),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(t['timeout_seconds']),*command],stdout=log,stderr=subprocess.STDOUT,cwd=ROOT,env=env,timeout=t['timeout_seconds']+20)
    row['exit_code']=result.returncode;row.update(validate(t,d,result.returncode));row['status']='PASS_PROGRAM_AND_PROTOCOL_CONSERVATION_NOT_HARDWARE_QUALIFICATION'
   except Exception as exc:
    row['failure']=repr(exc);row['cycles']=None;(d/'validation_exception.txt').write_text(traceback.format_exc())
   row['wall_seconds']=time.perf_counter()-start;row['ended']=now();row['host_cpu_seconds']=r.seconds(d/'gem5.time') if (d/'gem5.time').is_file() else None
   row['hashes']={p.name:m.sha(p) for p in d.iterdir() if p.is_file()};atomic(d/'EXECUTION.json',row);return row
 def save(name,status,unrun=None):
  m.put(BASE/'reports'/(name+'.json'),{'status':status,'tasks':rows,'unrun':unrun or [],'plan':m.ref(plan),'resources':r.snapshot()})
 def batch(group,name):
  r.snapshot(sum(t['timeout_seconds']+5 for t in group),len(group))
  with concurrent.futures.ThreadPoolExecutor(max_workers=min(32,len(group))) as pool:result=list(pool.map(one,group))
  rows.extend(result);passed=all(x['status'].startswith('PASS_') for x in result);save(name,'PASS_PHASE' if passed else 'FAIL_RETAINED_NO_AUTOMATIC_RETRY');assert passed,'FAILED_STAGE_PRESERVED_NO_RETRY';print(name,len(rows),'PASS',flush=True)
 batch(tasks[:2],'CPU_PILOT2');batch(tasks[2:6],'CPU_CHECKSUM6')
 # A deterministic timeout rule selected before any PROGRAM dispatch; event
 # inputs/RNG/config remain frozen, no synthetic fault-rate compression.
 slowest=max(x['host_cpu_seconds']/x['seu']['source_cycles'] for x in rows)
 for t in tasks[6:]:t['timeout_seconds']=min(3600,max(120,math.ceil(3*t['reference_CPU_cycles']*slowest)))
 workload_plan=BASE/'reports/CPU_PROGRAM18_HOST_BOUNDS.lock.json';m.put(workload_plan,{'status':'FROZEN_AFTER_CHECKSUM6_BEFORE_PROGRAMS','CPU24_plan':m.ref(plan),'checksum_gate':m.ref(BASE/'reports/CPU_CHECKSUM6.json'),'slowest_measured_seconds_per_source_cycle':slowest,'tasks':tasks[6:]})
 # Match all three representations at each program/L. Admit complete groups
 # only; run as many groups in parallel as the exact timeout reservations allow.
 groups=[tasks[i:i+3] for i in range(6,24,3)];wave=0
 while groups:
  selected=[];reserve=0
  for group in groups:
   cost=sum(t['timeout_seconds']+5 for t in group)
   try:r.snapshot(reserve+cost,len(selected)+3)
   except AssertionError:break
   selected.extend(group);reserve+=cost
  if not selected:
   save('CPU_STOP_BUDGET','STOP_BEFORE_DISPATCH_COMPLETE_MATCHED_GROUPS',groups);return
  batch(selected,'CPU_PROGRAM_WAVE_'+str(wave));groups=groups[len(selected)//3:];wave+=1
 # A change in committed architectural identity is visible and disqualifies the
 # performance comparison even when checksum succeeds. Do not hide/exclude it.
 identities={}
 for row in rows[6:]:identities.setdefault(row['program'],set()).add(row['seu']['committed_identity'])
 matched=all(len(values)==1 for values in identities.values())
 save('CPU24_FINAL','PASS_24_CLEAN_CORRECTNESS_AND_RESOURCES_NOT_PROTECTION_COMPARISON' if matched else 'PROGRAM_PASS_ARCH_PATH_DIFFERENCE_REQUIRES_REVIEW')
 print('CPU24_FINISHED',len(rows),'matched_architectural_identity',matched,flush=True)
if __name__=='__main__':main()
