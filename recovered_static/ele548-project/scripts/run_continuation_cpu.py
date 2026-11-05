"""Actual O3 runner: bounded independent owners, raw logs and finite timing gates."""
import argparse,json,csv,os,statistics,concurrent.futures,math
import numpy as np
from continuation_common import *
from rng_namespace import rng,descriptor
from run_o3_public_baseline import stats
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['design','holdout'],required=True);a=p.parse_args();phase=a.phase
assert json.loads((OUT/'reports/G4_CPU_GATE.json').read_text())['status']=='PASS'
selection=json.loads((OUT/'configs/policy_selection.lock.json').read_text())['selection'];kN=int(selection['N1'].split('k')[-1]);kH=int(selection['H1'].split('k')[-1])
variants=[dict(id=s,scheme=s,policy='LEGACY',k=0,C=0 if s=='P0' else 1,U=0) for s in ['P0','P_ED','P_ECC','P_TMR']]+[dict(id='N1',scheme='P_ED',policy='N1',k=kN,C=1,U=0),dict(id='H1',scheme='P_ED',policy='H1',k=kH,C=1,U=1)]
if phase=='design':
 inputs=json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text())['programs'][:2]
 trials=2;scenarios=['CHARM_6T']
 variants+= [dict(id='N1_U1',scheme='P_ED',policy='N1',k=kN,C=1,U=1)]
else:
 freeze=json.loads((OUT/'configs/cpu_policy_freeze.lock.json').read_text());assert freeze['status']=='FROZEN_BEFORE_NEW_INPUT_POLICY_EVALUATION'
 inputs=json.loads((OUT/'configs/holdout_inputs.lock.json').read_text())['programs'];trials=freeze['owners_per_scenario'];scenarios=freeze['scenarios'];variants=freeze['variants']
base=1815480000 if phase=='design' else 1915480000
binary=ROOT/'third_party/gem5-continuation/build/X86_STAGE0/gem5.opt';config=ROOT/'gem5/o3_continuation.py';out=OUT/f'reports/cpu_{phase}';out.mkdir(parents=True,exist_ok=True)
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=[w['site_ids'] for w in scope['payload_words']];sizes=np.array(list(map(len,words)));ends=np.cumsum(sizes);payload=sum(words,[])
env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
record_path=OUT/f'reports/G{4 if phase=="design" else 5}_CPU_{phase.upper()}.json';results=[];jobs=[];clean={}
def persist(status):write(record_path,dict(status=status,phase=phase,planned=len(jobs),completed=len(results),tasks=results,binary_sha256=sha(binary),source_lock_sha256=sha(OUT/'configs/gem5_source.lock.json'),policy_selection_sha256=sha(OUT/'configs/policy_selection.lock.json'),host_core_hours=sum(r.get('host_cpu_seconds') or 0 for r in results)/3600))
def run(t):
 item=next(x for x in inputs if x['name']==t['program']);d=out/t['label'];d.mkdir(exist_ok=True);schedule=d/'schedule.ticks';schedule.write_text(t['events_text']);assert sha(ROOT/item['binary'])==item['binary_sha256'] and sha(ROOT/item['input'])==item['input_sha256']
 cmd=[binary,'--outdir='+str(d),config,'--binary',ROOT/item['binary'],'--input',ROOT/item['input'],'--scheme',t['scheme'],'--role-policy',t['policy'],'--inspection-interval',str(t['k']),'--check-cycles',str(t['C']),'--maintenance-cycles',str(t['U']),'--repair-cycles','0' if t['scheme']=='P0' else '4','--schedule',schedule,'--max-ticks',str(t.get('max_ticks',250000000000))]
 rr=timed(cmd,d/'gem5.log',env=env,timeout=1800);rr.update({k:v for k,v in t.items() if k!='events_text'});rr.update(output=str(d.relative_to(ROOT)),schedule_sha256=sha(schedule),input_sha256=item['input_sha256'],binary_program_sha256=item['binary_sha256'],status='FAIL_EXECUTION')
 if rr['exit_code']:return rr
 try:
  assert sha(d/'program.stdout')==item['native_stdout_sha256'] and not (d/'program.stderr').read_bytes(),'native answer'
  log=(d/'gem5.log').read_text();assert 'Exit cause: exiting with last active thread context code: 0' in log
  assert not any(s in log.lower() for s in ['ignoring syscall','unimplemented syscall'])
  st=stats(d/'stats.txt');s=json.loads((d/'seu.json').read_text());m=json.loads((d/'logical_manifest.json').read_text());cycles=int(st['system.cpu.numCycles']);ni=int(st['system.cpu.commitStats0.numInsts']);assert ni==int(st['simInsts']) and cycles>0
  if (t['program'],'P0') in clean:assert ni==clean[(t['program'],'P0')]['instructions']
  expected=[line for line in t['events_text'].splitlines() if int(line.split()[0])<=s['end_tick']];events=list(csv.DictReader((d/'events.csv').open()));assert len(expected)==len(events)==s['applied_events']
  for line,e in zip(expected,events):
   tick,ids=line.split();assert e['tick']==tick and e['site_ids']==ids and e['XOR_verified']=='1';assert all(x!=y for x,y in zip(e['before_bits'],e['after_bits']))
  repairs=list(csv.DictReader((d/'events.csv.repairs.csv').open()));assert len(repairs)==s['repair_batches'];previous=0
  for e in repairs:previous=max(previous,int(e['tick']))+500*(0 if t['scheme']=='P0' else 4);assert previous==int(e['repair_busy_until'])
  rebuild=list(csv.DictReader((d/'events.csv.rebuild.csv').open()));assert len({x['tick'] for x in rebuild})==len(rebuild)
  assert all(int(x['source_bits_delta'])<=16 and int(x['rebuild_writes_delta'])<=1 for x in rebuild)
  assert s['max_update_queue']<=16
  if t['scenario']=='zero':assert s['detected']==s['applied_events']==0
  mis=st['system.cpu.branchPred.mispredicted_0::DirectCond']+st['system.cpu.branchPred.mispredicted_0::IndirectCond']
  rr.update(status='PASS',cycles=cycles,instructions=ni,IPC=ni/cycles,conditional_misses=int(mis),seu=s,total_bits=m['total_bits'],hashes={f:sha(d/f) for f in ['stats.txt','seu.json','config.json','logical_manifest.json','events.csv','events.csv.repairs.csv','events.csv.rebuild.csv','program.stdout']},failure=None)
 except Exception as e:rr.update(status='FAIL_VALIDATION',failure=str(e))
 return rr
# All deterministic clean rows are concrete measurements of the exact new config/input.
clean_jobs=[]
for pi,item in enumerate(inputs):
 for v in variants:
  t=dict(v,program=item['name'],scenario='zero',trial=0,owner=f'CONT_{phase.upper()}_ZERO_W{pi}',label=f"{item['name']}.zero.{v['id']}",events_text='');clean_jobs.append(t)
jobs.extend(clean_jobs);persist('RUNNING_CLEAN')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run,clean_jobs):
  results.append(r);persist('RUNNING_CLEAN');print(r['label'],r['status'],r.get('failure',''),flush=True)
  if r['status']=='PASS':clean[(r['program'],r['id'])]=r
assert all(r['status']=='PASS' for r in results),'clean protocol/output gate failed'
# Events freeze from pristine clean A, not the protected outcome. Arrivals continue during holds.
fault_jobs=[]
for pi,item in enumerate(inputs):
 A=clean[(item['name'],'P0')]['cycles'];cap=A*4
 for si,scenario in enumerate(scenarios):
  for n in range(trials):
   master=base+pi*1000000+si*10000+n;tr=rng(master,'time');kr=rng(master,'K');lr=rng(master,'location');events=[]
   if scenario=='SBU_SINGLE':arrivals=[float(tr.uniform(.1*A,.8*A))]
   else:
    arrivals=[];t=0
    while True:
     t+=float(tr.exponential(1e6))
     if t>=cap:break
     arrivals.append(t)
   for t in arrivals:
    K=1 if scenario=='SBU_SINGLE' or int(kr.integers(214))<205 else 2
    ids=words[int(np.searchsorted(ends,int(lr.integers(346)),side='right'))];anchor=int(lr.integers(len(ids)-K+1));events.append((max(1,int(round(t*500))),ids[anchor:anchor+K]))
   events_text=''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events)
   for v in variants:
    fault_jobs.append(dict(v,program=item['name'],scenario=scenario,trial=n,owner=f'CONT_{phase.upper()}_V2_W{pi}_S{si}_N{n}',seed=master,namespace={r:descriptor(master,r) for r in ['time','K','location']},label=f"{item['name']}.{scenario}.n{n}.{v['id']}",events_text=events_text,max_ticks=cap*500))
jobs.extend(fault_jobs);write(OUT/f'configs/cpu_{phase}.runs.lock.json',dict(status='FROZEN_BEFORE_FAULT_OUTCOMES',jobs=jobs,phase=phase,variants=variants,owners_per_scenario=trials,models={'SBU_SINGLE':'single conditional selected payload event; no rate','CHARM_6T':'fixed declared1e-6events/cycle with205K1:9K2; adjacent within natural word'},rate_calibrated=False));persist('RUNNING')
# Conservative measured runtime projection under the32core-hour cap; no unbounded background job.
forecast=sum(r['host_cpu_seconds'] for r in results)/len(results)*len(fault_jobs)*1.5/3600
write(OUT/f'reports/CPU_{phase.upper()}_RUNTIME_PROJECTION.json',dict(clean_host_core_hours=sum(r['host_cpu_seconds'] for r in results)/3600,fault_forecast_core_hours=forecast,planned_fault_runs=len(fault_jobs),clean_p50_seconds=statistics.median(r['host_cpu_seconds'] for r in results),clean_p95_seconds=float(np.percentile([r['host_cpu_seconds'] for r in results],95)),peak_RSS_KiB=max(r['max_rss_kib'] for r in results),assumption='1.5*clean mean host CPU seconds; actual totals budget checked separately'))
assert forecast<24,'forecast leaves too little32core-hour budget; freeze smaller scope before fault runs'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run,fault_jobs):results.append(r);persist('RUNNING');print(r['label'],r['status'],r.get('failure',''),flush=True)
status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED_TRIALS';persist(status)
assert status=='PASS','Failures retained; no promotion until diagnosed'
print('PASS',len(results),'actualCPU runs, hostcorehours',sum(r['host_cpu_seconds'] for r in results)/3600)
