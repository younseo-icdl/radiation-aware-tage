#!/usr/bin/env python3
"""Aggregate actual program-exit performance, retaining failed originals."""
from pathlib import Path
import datetime,hashlib,json,sys
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
import run as v
import resources_disk328 as r
B=v.BASE;V15=v.V15;OUT=r.scope['OUT']
def ref(p):return v.m.ref(p)
def load(p):return v.load(p)
def first(row):return row.get('program_exit_seu',row['seu'])
def main():
 assert load(B/'reports/REGRESSIONS_A1.json')['status']=='PASS_TWO_TERMINAL_REGRESSIONS'
 assert load(B/'reports/REMAINING_B2.json')['status']=='PASS_SIX_REMAINING_PROGRAMS_REVALIDATED_NO_RERUN'
 proposal=load(V15/'reports/CPU18_PROPOSAL.lock.json');selected=[];failures=[];checks=0
 for t in proposal['tasks']:
  original=OUT/t['label']/'EXECUTION.json';row=load(original);original_ref=ref(original)
  if not row['status'].startswith('PASS_'):
   failures.append({'label':row['label'],'status':row['status'],'cycles':row['cycles'],'failure':row.get('failure'),'execution':original_ref})
   path=OUT/(t['label']+'.terminal_A1')/'EXECUTION.json';row=load(path)
  else:path=original
  assert row['status'].startswith('PASS_')
  for name,digest in row['hashes'].items():assert v.m.sha(path.parent/name)==digest;checks+=1
  s=first(row);manifest=load(path.parent/'logical_manifest.json')
  end=0
  for region in manifest['regions']:assert region['start']==end;end+=region['bits']
  assert end==manifest['total_logical_bits'] and s['conserved'] and s['applied_faults']==0
  geometry={k:manifest[k] for k in ('total_logical_bits','table_bits','source_query_L','source_update_L','provider_extra_L','II','early_checkpoint_bits')}
  item={'planned_label':t['label'],'execution_label':row['label'],'execution':ref(path),'original_execution':original_ref,'program':t['program'],'query_L':t['query_L'],'update_L':1 if t['representation']=='direct' else t['update_L'],'representation':t['representation'],'early':t['early'],'cycles':row['cycles'],'IPC':row['IPC'],'simInsts':row['simInsts'],'program_exit_seu':s,'completion_seu':row['seu'],'logical_geometry_not_PPA':geometry,'completed_requests_per_program_source_cycle':s['lookup_consumed']/s['source_cycles'],'accepted_requests_per_program_source_cycle':s['lookup_accepted']/s['source_cycles'],'first_exit_completed_or_early_predictions_per_source_cycle':s['lookups']/s['source_cycles'],'host_cpu_seconds':row['host_cpu_seconds'],'post_exit_source_cycles':row.get('termination',{}).get('source_cycles_observed'), 'post_exit_scope':'actual helper completion only; full CPU/BPU context switch not qualified'}
  selected.append(item)
 for old in load(B/'reports/PRECHECK_A1.json')['old_failed_files_preserved']:assert v.m.sha(old['path'])==old['sha256']
 index={x['planned_label']:x for x in selected};comparisons=[]
 def compare(name,new,old,reference):
  s=new['program_exit_seu'];q=first(old)
  for k in ('committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash'):assert s[k]==q[k],(name,k)
  comparisons.append({'comparison':name,'program':new['program'],'new':new['execution'],'reference':reference,'cycles':new['cycles'],'reference_cycles':old['cycles'],'cycles_change_pct':100*(new['cycles']/old['cycles']-1),'IPC':new['IPC'],'reference_IPC':old['IPC'],'matched_committed_path_and_RNG':True})
 for program in ('qsort_small','dijkstra_small','sha1'):
  stem=program+'.R1.';tasks=[t for t in proposal['tasks'] if t['label'].startswith(stem)]
  reference=next(t['architectural_reference'] for t in tasks);old=load(reference['path'])
  compare('query_L2_vs_L1_at_update1',index[stem+'QUERY_REC_Q2U1'],old,reference)
  compare('early_REC_vs_serial_REC_Q1U1',index[stem+'EARLY_REC_Q1U1'],old,reference)
  oldpath=Path(reference['path']).parent.parent/(program+'.R1.direct.L1')/'EXECUTION.json'
  compare('early_DIRECT_vs_serial_DIRECT_Q1U1',index[stem+'EARLY_DIRECT_Q1U1'],load(oldpath),ref(oldpath))
  oldpath=Path(reference['path']).parent.parent/(program+'.R1.recurrent.L2')/'EXECUTION.json'
  compare('update1_vs_update2_at_query2',index[stem+'QUERY_REC_Q2U1'],load(oldpath),ref(oldpath))
  other=index[stem+'EARLY_REC_Q1U1'];compare('early_DIRECT_vs_early_REC_Q1U1',index[stem+'EARLY_DIRECT_Q1U1'],load(other['execution']['path']),other['execution'])
 for mode in ('recurrent','direct'):
  new=index['micro.'+mode+'.E1'];old=index['micro.'+mode+'.E0'];compare('synthetic_early_vs_serial_Q2U1',new,load(old['execution']['path']),old['execution'])
 result={'status':'PASS_18_PLANNED_CONDITIONS_USING20_EXECUTIONS_TWO_ORIGINAL_FAILURES_PRESERVED','at_America_New_York':datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(),'original_proposal':ref(V15/'reports/CPU18_PROPOSAL.lock.json'),'CPU_authorization':ref(V15/'reports/CPU_AUTHORIZATION.lock.json'),'disk_authorization':ref(B/'reports/DISK_AUTHORIZATION_328.lock.json'),'analyzer':ref(__file__),'actual_executions':20,'selected_valid_conditions':len(selected),'retained_failed_originals':failures,'raw_file_SHA_checks':checks,'selected':selected,'comparisons':comparisons,'resources':r.snapshot(),'limitations':['No injected faults, no A/B/C/D or B-D','Same exposed R1 development inputs and deterministic seed548; no independent evaluation CI','Synthetic micro throughput is distinct from real branch stream','Counters named stalls/waits may count overlapping calls, not a CPI decomposition','Early includes finite-owner checkpoint and admission changes, not isolated raw pipeline timing','Metadata parallel decode/encode stage fit is assumed, no actual RTL/PPA','Consumer token routing/CPU-owned BI fault scope and full context-switch drain remain unqualified','Mandatory S*346 P0/P_ED frequent/periodic/SECDED/TMR preserved; not yet ported to this new common finite model','No new source-informed fault campaign or changed RNG/rate/time/censoring','No RTL/Cadence/SPICE/TCAD execution']}
 assert len(selected)==18 and len(failures)==2 and result['resources']['CPU_global']==3531
 result['retained_dispatch_reporting_failure']=ref(B/'runtime/remaining_B1/stderr')
 result['record_recovery_no_new_simulation']=ref(B/'reports/REMAINING_B2.json')
 result['limitations'].append('B1 reporting wrapper omitted seconds export; all six closed raw outputs were revalidated by B2 without rerun. Six host affinity/wall durations were not persisted and are not reconstructed.')
 v.m.put(B/'reports/FINAL_ANALYSIS.json',result)
 print(json.dumps({'status':result['status'],'comparisons':comparisons,'post_exit_cycles':[(x['planned_label'],x['post_exit_source_cycles']) for x in selected if x['post_exit_source_cycles'] is not None],'resources':result['resources']},indent=2))
if __name__=='__main__':main()
