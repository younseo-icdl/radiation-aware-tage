"""Independent whole-population and directed added-state stress, not a new policy search."""
import ast,csv,concurrent.futures,json,os,statistics
import numpy as np
from continuation_common import *
from rng_namespace import rng,descriptor
from run_o3_public_baseline import stats
phase='robustness';primary=json.loads((OUT/'reports/G5_CPU_HOLDOUT_V2.json').read_text());assert primary['status']=='PASS'
inputs=json.loads((OUT/'configs/holdout_inputs.lock.json').read_text())['programs'];variants=json.loads((OUT/'configs/cpu_policy_freeze.lock.json').read_text())['variants'];clean={(r['program'],r['id']):r for r in primary['tasks'] if r['scenario']=='zero'}
binary=ROOT/'third_party/gem5-continuation/build/X86_STAGE0/gem5.opt';config=ROOT/'gem5/o3_continuation.py';out=OUT/'reports/cpu_exposure_robustness';out.mkdir(parents=True,exist_ok=True)
env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
# Reuse exactly the already gated actual runner function; no plan-as-execution confusion.
source=ast.parse((ROOT/'scripts/run_continuation_cpu_v2.py').read_text());node=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='run');exec(compile(ast.Module(body=[node],type_ignores=[]),'<gated_actual_CPU_run>','exec'))
jobs=[];maxbits=max(r['total_bits'] for r in clean.values())
for pi,item in enumerate(inputs):
 A=clean[item['name'],'P0']['cycles'];cap=A*4
 for n in range(3):
  master=2115480000+pi*1000000+n;tr=rng(master,'time');lr=rng(master,'location');t=0;incidents=[]
  while True:
   t+=float(tr.exponential(1e6*65370/maxbits))
   if t>=cap:break
   incidents.append((max(1,int(round(t*500))),int(lr.integers(maxbits))))
  for v in variants:
   B=clean[item['name'],v['id']]['total_bits'];events=[(t,[site]) for t,site in incidents if site<B]
   jobs.append(dict(v,program=item['name'],scenario='FULL_EQUAL_PER_BIT_SBU',trial=n,owner=f'CONT_EXTRA_V2_W{pi}_WHOLE_N{n}',seed=master,namespace={role:descriptor(master,role) for role in ['time','location']},label=f"{item['name']}.whole.n{n}.{v['id']}",events_text=''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events),max_ticks=cap*500,exposure='all modeledenumerated predictor/controller bits; existingBI/queues/arch/aging/RNGexcluded',per_bit_rate_per_cycle=1e-6/65370,per_bit_rate_measured=False,mark_coupling='maxpopulation Poisson marks; keep same base bit incidents, reject absent extra sites; actuallambda scales exactpopulation'))
 # Directed added-state tests are vulnerability diagnostics, not workload-average recovery samples.
 for v in variants:
  if v['id']=='P0':continue
  m=json.loads((ROOT/clean[item['name'],v['id']]['output']/'logical_manifest.json').read_text());structures=sorted({s['structure'] for s in m['additional_sites']})
  for si,structure in enumerate(structures):
   sites=[s for s in m['additional_sites'] if s['structure']==structure];lr=rng(2125480000+pi*1000000+si*100,'location');s=sites[int(lr.integers(len(sites)))];tick=int(A*.25)*500
   jobs.append(dict(v,program=item['name'],scenario='DIRECT_ADDED_'+structure,trial=0,owner=f'CONT_EXTRA_V2_W{pi}_DIRECT_{structure}',label=f"{item['name']}.direct.{structure}.{v['id']}",events_text=str(tick)+' '+str(s['id'])+'\n',max_ticks=cap*500,exposure='directed singled added storage bit; not radiatedpopulationaverage'))
forecast=sum(r['host_cpu_seconds'] for r in clean.values())/len(clean)*len(jobs)*1.5/3600
write(OUT/'configs/cpu_exposure_robustness.lock.json',dict(status='FROZEN_BEFORE_NEW_EXTRA_OUTCOMES',jobs=jobs,forecast_core_hours=forecast,base_primary_sha256=sha(OUT/'reports/G5_CPU_HOLDOUT_V2.json'),sampler='independentSBU totalbaseline1e-6percycle; equal per-bit assumption; no gamma penalty in addition toactualevents',scope='predictor logical storage only',hardware_PPA_measured=False))
assert forecast+budget_charge_seconds()/3600<32,'Extra robust scope exceeds remaining budget'
results=[];path=OUT/'reports/G5_CPU_EXPOSURE_ROBUSTNESS.json'
def persist(status):write(path,dict(status=status,planned=len(jobs),completed=len(results),tasks=results,config_sha256=sha(OUT/'configs/cpu_exposure_robustness.lock.json'),binary_sha256=sha(binary),host_core_hours=sum(r.get('host_cpu_seconds') or 0 for r in results)/3600,conditional_rate_not_calibrated=True))
persist('RUNNING')
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for start in range(0,len(jobs),8):
  assert budget_charge_seconds()<32*3600
  for r in pool.map(run,jobs[start:start+8]):results.append(r);persist('RUNNING');print(r['label'],r['status'],flush=True)
assert all(r['status']=='PASS' for r in results);persist('PASS')
print('PASS',len(results),'whole/addedCPU stress cases')
