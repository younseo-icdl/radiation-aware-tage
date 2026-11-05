import argparse,json,csv,collections,statistics,math
from continuation_common import *
from continuation_statistics import *
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['design','holdout'],required=True);a=p.parse_args();phase=a.phase
path=OUT/f'reports/G{4 if phase=="design" else 5}_CPU_{phase.upper()}_V2.json';x=json.loads(path.read_text());assert x['status']=='PASS','incomplete or failed campaign cannot produce qualified summary'
rows=x['tasks'];assert len(rows)==x['planned']==x['completed'];by={(r['program'],r['scenario'],r['trial'],r['id']):r for r in rows};assert len(by)==len(rows)
for r in rows:
 assert r['status']=='PASS'
 for name,h in r['hashes'].items():assert sha(ROOT/r['output']/name)==h
 assert sha(ROOT/r['output']/'schedule.ticks')==r['schedule_sha256']
clean={(r['program'],r['id']):r for r in rows if r['scenario']=='zero'};pairs=[]
for D in rows:
 if D['scenario']=='zero':continue
 B=by[(D['program'],D['scenario'],D['trial'],'P0')];assert audit_pair(B,D)
 A=clean[(D['program'],'P0')];C=clean[(D['program'],D['id'])];assert A['instructions']==B['instructions']==C['instructions']==D['instructions']
 pair=dict(program=D['program'],input_sha256=D['input_sha256'],phase=phase,scenario=D['scenario'],variant=D['id'],owner=D['owner'],schedule_sha256=D['schedule_sha256'],**abcd(A['cycles'],B['cycles'],C['cycles'],D['cycles']),events_B=B['seu']['applied_events'],events_D=D['seu']['applied_events'],no_event_D=D['seu']['applied_events']==0,phi_mismatch_words=D['seu']['fold_phi_mismatch_words'],state_hash_diff_from_own_clean=D['seu']['canonical_base_state_hash']!=C['seu']['canonical_base_state_hash'],zero_observed_task_loss=D['cycles']==C['cycles'],source_D=D['output'],status_A=A['status'],status_B=B['status'],status_C=C['status'],status_D=D['status'],oracle=False)
 if D['scenario']=='SBU_SINGLE':
  events=list(csv.DictReader((ROOT/D['output']/'events.csv').open()));repairs=list(csv.DictReader((ROOT/D['output']/'events.csv.repairs.csv').open()));tick=int(events[0]['tick']) if events else None
  detected=next((int(rr['tick']) for rr in repairs if tick is not None and int(rr['tick'])>=tick),None)
  pair.update(detector_delay_cycles=(detected-tick)/500 if detected is not None else None,detector_censored=detected is None)
 pairs.append(pair)
keys=sorted({(p['variant'],p['scenario']) for p in pairs});summary=[]
for variant,scenario in keys:
 rs=[p for p in pairs if p['variant']==variant and p['scenario']==scenario];programs=sorted({r['program'] for r in rs});metrics={}
 for metric in ['net_cycles','net_pp','clean_overhead_pct','residual_loss_pp','total_slowdown_pct','fault_unprotected_pct']:
  metrics[metric]=fixed_program_bootstrap({prog:[r[metric] for r in rs if r['program']==prog] for prog in programs})
 perprogram={prog:{m:fixed_program_bootstrap({prog:[r[m] for r in rs if r['program']==prog]}) for m in ['net_pp','clean_overhead_pct','residual_loss_pp','total_slowdown_pct']} for prog in programs}
 delays=[p.get('detector_delay_cycles') for p in rs if p.get('detector_delay_cycles') is not None]
 summary.append(dict(variant=variant,scenario=scenario,valid_pairs=len(rs),metrics=metrics,per_program=perprogram,no_event_pairs=sum(p['no_event_D'] for p in rs),helpful_task_faults=sum(p['D']<p['C'] for p in rs),zero_task_loss=sum(p['D']==p['C'] for p in rs),phi_mismatch_runs=sum(p['phi_mismatch_words']>0 for p in rs),prediction_state_divergence_runs=sum(p['state_hash_diff_from_own_clean'] for p in rs),latent_phi_with_zero_task_loss=sum(p['zero_observed_task_loss'] and p['phi_mismatch_words']>0 for p in rs),detector_delay_observed_n=len(delays),detector_delay_p95=float(np.percentile(delays,95)) if delays else None,detector_censored=sum(p.get('detector_censored',False) for p in rs),task_extra_cycles_p95=float(np.percentile([p['D']-p['C'] for p in rs],95)),max_task_extra_cycles=max(p['D']-p['C'] for p in rs)))
write(OUT/f'reports/CPU_{phase.upper()}_PAIRS.json',dict(status='PASS_AUDITED_PAIRED_RAW_CYCLES',pairs=pairs,campaign_sha256=sha(path)))
if pairs:
 with (OUT/f'reports/CPU_{phase.upper()}_PAIRS.csv').open('w') as f:
  fields=sorted(set().union(*(r.keys() for r in pairs)));w=csv.DictWriter(f,fields);w.writeheader();w.writerows(pairs)
write(OUT/f'reports/CPU_{phase.upper()}_SUMMARY.json',dict(status='PASS_FIXED_SCOPE_PAIRED_ANALYSIS',summary=summary,clean_rows=[dict(program=r['program'],variant=r['id'],cycles=r['cycles'],bits=r['total_bits'],maintenance=r['U'],max_backlog=r['seu'].get('max_maintenance_backlog_cycles'),source=r['output']) for r in rows if r['scenario']=='zero'],executed=len(rows),observed_failures=0,prior_development_failures='resourcev1 four clean failures preserved separately; no fault trials before abort',failure_upper_per_policy=zero_failure_upper(len({r['owner'] for r in pairs if r['variant']=='P0'})),population='fixed inputs and program set; independent fault owner sampling only',performance_conditioning='all planned runs complete/native-correct; never infer rates across untested programs',cycles_are_measured_in_gem5=True,RTL_PPA_measured=False))
print('PASS paired summary',phase,len(pairs),'pairs')
