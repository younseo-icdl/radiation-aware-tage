import argparse,csv,json,statistics
from v3_common import *
from continuation_statistics import abcd,fixed_program_bootstrap
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['design','evaluation'],required=True);phase=p.parse_args().phase
path=OUT/f'reports/CPU_{phase.upper()}.json';campaign=json.loads(path.read_text());assert campaign['status'] in ['PASS','FAIL_RETAINED']
rows=campaign['tasks'];assert len(rows)==campaign['completed']==campaign['planned'];by={(r['program'],r['scenario'],r['trial'],r['id']):r for r in rows};assert len(by)==len(rows)
for r in rows:
 if r['status']=='PASS':
  for name,h in r['hashes'].items():assert sha(ROOT/r['output']/name)==h
clean={(r['program'],r['id']):r for r in rows if r['scenario']=='zero'};pairs=[];failed=[]
for D in rows:
 if D['scenario']=='zero':continue
 B=by[(D['program'],D['scenario'],D['trial'],'P0')];A=clean[D['program'],'P0'];C=clean[D['program'],D['id']]
 if any(r['status']!='PASS' for r in [A,B,C,D]):failed.append(dict(program=D['program'],owner=D['owner'],variant=D['id'],scenario=D['scenario'],statuses=[r['status'] for r in [A,B,C,D]]));continue
 assert D['owner']==B['owner'] and D['input_sha256']==B['input_sha256'] and D['schedule_sha256']==B['schedule_sha256']
 assert A['instructions']==B['instructions']==C['instructions']==D['instructions']
 assert not any(r.get('oracle') for r in [A,B,C,D])
 s=D['seu'];pairs.append(dict(program=D['program'],scenario=D['scenario'],variant=D['id'],owner=D['owner'],**abcd(A['cycles'],B['cycles'],C['cycles'],D['cycles']),events_B=B['seu']['applied_events'],events_D=s['applied_events'],phi_mismatch=s['fold_phi_mismatch_words'],state_diff=s['canonical_base_state_hash']!=C['seu']['canonical_base_state_hash'],D_IPC=D['IPC'],C_IPC=C['IPC'],source_D=D['output']))
summary=[]
for variant,scenario in sorted({(r['variant'],r['scenario']) for r in pairs}):
 rr=[r for r in pairs if r['variant']==variant and r['scenario']==scenario];programs=sorted({r['program'] for r in rr});metrics={}
 for metric in ['net_pp','net_cycles','clean_overhead_pct','residual_loss_pp','total_slowdown_pct']:
  metrics[metric]=fixed_program_bootstrap({program:[r[metric] for r in rr if r['program']==program] for program in programs},iterations=10000,seed=8171026)
 per_program={program:{metric:fixed_program_bootstrap({program:[r[metric] for r in rr if r['program']==program]},iterations=10000,seed=8171026) for metric in ['net_pp','clean_overhead_pct','residual_loss_pp','total_slowdown_pct']} for program in programs}
 summary.append(dict(variant=variant,scenario=scenario,valid_owner_pairs=len(rr),metrics=metrics,per_program=per_program,helpful=sum(r['D']<r['C'] for r in rr),zero=sum(r['D']==r['C'] for r in rr),noevent=sum(r['events_D']==0 for r in rr),latent_phi=sum(r['phi_mismatch']>0 for r in rr),state_diff=sum(r['state_diff'] for r in rr)))
write(OUT/f'reports/CPU_{phase.upper()}_SUMMARY.json',dict(status='AUDITED_FIXED_INPUT_OWNER_ANALYSIS',summary=summary,successful_pairs=len(pairs),failed_pairs=failed,planned_runs=len(rows),executed_runs=len(rows),failures=sum(r['status']!='PASS' for r in rows),clean_rows=[dict(program=r['program'],variant=r['id'],cycles=r['cycles'],IPC=r['IPC'],total_bits=r['total_bits']) for r in rows if r['scenario']=='zero' and r['status']=='PASS'],bootstrap_resamples=10000,fault_rate_calibrated=False,physical_PPA=False))
write(OUT/f'reports/CPU_{phase.upper()}_PAIRS.json',dict(pairs=pairs,failed=failed,campaign_sha256=sha(path)))
with (OUT/f'CPU_RESULTS_{phase}.csv').open('w') as f:
 fields=sorted(set().union(*(r.keys() for r in pairs)));w=csv.DictWriter(f,fields);w.writeheader();w.writerows(pairs)
print('Paired CPU analysis',phase,len(pairs),'valid;',len(failed),'failed pairs retained')
