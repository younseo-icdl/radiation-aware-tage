import csv,concurrent.futures,json
from continuation_common import *
c=json.loads((OUT/'reports/G3_CPP_SCREEN_FINAL.json').read_text());assert c['status']=='PASS'
selected=json.loads((OUT/'configs/policy_selection.lock.json').read_text())['selection']['N1'];cases=[r for r in c['tasks'] if r['variant']==selected];out=OUT/'reports/full_delta_ablation';out.mkdir(parents=True,exist_ok=True)
def run(t):
 cmd=t['command'][:-1];cmd[0]=str(ROOT/'build/periodic_scheduled');prefix=out/(Path(t['output']).name);cmd[7]=str(prefix)
 r=timed(cmd,prefix.with_suffix('.log'),timeout=120);assert r['exit_code']==0
 m=list(csv.DictReader(Path(str(prefix)+'.csv').open()))[0];new=t['metrics']
 equivalent=all(m[k]==new[k] for k in ['harm','help','net','clean_misses','faulty_misses','end_differing_base_bits','detected','reset_refill','first_detector_conditional','detector_delay_control_updates'])
 # Expected parity may differ for other fault models; never force equality by dropping a case.
 return dict(owner=t['owner'],workload=t['workload'],scenario=t['scenario'],status='PASS',same_behavior_on_observed_case=equivalent,old_metrics=m,new_metrics=new,old_CSV_sha256=sha(Path(str(prefix)+'.csv')),new_CSV_sha256=t['CSV_sha256'],command=r['command'],host_cpu_seconds=r['host_cpu_seconds'])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,cases))
write(OUT/'reports/G3_MAINTENANCE_ABLATION.json',dict(status='PASS_SAME_K_SAME_RELEARN_ABLATION',cases=results,trials=len(results),same_behavior_cases=sum(r['same_behavior_on_observed_case'] for r in results),old_binary_sha256=sha(ROOT/'build/periodic_scheduled'),new_binary_sha256=c['binary_sha256'],physical_cost_measured=False,interpretation='Full-word reduction counts eliminated in incremental software implementation; synthesis may algebraically optimize both into same circuit. No area/energy/firstness claim.'))
print('PASS',len(results),'samekfull-delta/incremental ablation; equivalentcases',sum(r['same_behavior_on_observed_case'] for r in results))
