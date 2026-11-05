#!/usr/bin/env python3
"""Read terminal CPU18 evidence. No simulation, retries or invented rows."""
from pathlib import Path
import datetime,hashlib,json,sys
from zoneinfo import ZoneInfo
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[2]
OUT=BASE/'runtime/cpu_trials'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def load(p):return json.loads(Path(p).read_text())
def put(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def verified(v):
 assert sha(v['path'])==v['sha256'],('REFERENCE_CHANGED',v['path'])
 return load(v['path'])
def percent(x,y):return 100*(x/y-1)
def main():
 final=BASE/'reports/CPU18_SERIAL_FINAL.json'
 if not final.exists():final=BASE/'reports/CPU18_FINAL.json'
 assert final.exists(),'LIVE_OR_INCOMPLETE_NO_FINAL_ANALYSIS'
 proposal=load(BASE/'reports/CPU18_PROPOSAL.lock.json');f=load(final);rows=f['tasks']
 tasks={t['label']:t for t in proposal['tasks']};assert len(tasks)==18
 assert len({r['label'] for r in rows})==len(rows)
 checked_files=0;failures=[];actual=[];index={}
 for row in rows:
  t=tasks[row['label']];path=OUT/t['label'];r=load(path/'EXECUTION.json');assert row==r
  for name,expected in r['hashes'].items():assert sha(path/name)==expected;checked_files+=1
  for key in ('program_binary','input','expected_stdout'):
   if t[key]:assert sha(t[key]['path'])==t[key]['sha256']
  valid=r['status'].startswith('PASS_')
  if not valid:failures.append({'label':r['label'],'failure':r.get('failure'),'execution':ref(path/'EXECUTION.json')})
  item={'label':r['label'],'program':r['program'],'representation':t['representation'],'query_L':t['query_L'],'update_L':1 if t['representation']=='direct' else t['update_L'],'early':t['early'],'valid':valid,'execution':ref(path/'EXECUTION.json'),'cycles':r.get('cycles'),'IPC':r.get('IPC'),'host_cpu_seconds':r.get('host_cpu_seconds'),'wall_seconds':r.get('wall_seconds')}
  if valid:
   s=r['seu'];assert s['conserved'] and s['applied_faults']==0
   assert s['lookup_accepted']==s['lookup_consumed']+s['lookup_cancelled']+s['lookup_pending']
   assert s['source_accepted']==s['source_completed']+s['source_cancelled']+s['source_pending']
   manifest=load(path/'logical_manifest.json')
   assert manifest['source_query_L']==t['query_L'] and manifest['source_update_L']==item['update_L']
   assert manifest['early_checkpoint_bits']==(848 if t['early'] else 0)
   end=0;metadata_bits=0
   for region in manifest['regions']:
    assert region['start']==end and region['bits']>0;end+=region['bits']
    if any(tag in region['name'] for tag in ('metadata','mirrored_SECDED','early_checkpoint_owner','early_deferred_cancel')):metadata_bits+=region['bits']
   assert end==manifest['total_logical_bits'] and manifest['II']==1
   geometry={k:manifest[k] for k in ('total_logical_bits','table_bits','source_query_L','source_update_L','provider_extra_L','II','early_checkpoint_bits','ingress_capacity','squash_reserved_commands')}
   geometry['explicitly_named_metadata_logical_bits']=metadata_bits
   item.update({'simInsts':r['simInsts'],'completed_requests_per_source_cycle':s['lookup_consumed']/s['source_cycles'],'accepted_requests_per_source_cycle':s['lookup_accepted']/s['source_cycles'],'max_lookup_pending':s['max_lookup_pending'],'max_source_pending':s['max_source_pending'],'seu':s,'manifest':ref(path/'logical_manifest.json'),'logical_geometry_not_PPA':geometry})
  actual.append(item);index[item['label']]=item
 comparisons=[]
 def compare(name,new,old,oldref):
  if not new['valid'] or not old['status'].startswith('PASS_'):return
  for key in ('committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash'):
   assert new['seu'][key]==old['seu'][key],('UNPAIRED_ARCHITECTURE',name,key)
  comparisons.append({'comparison':name,'program':new['program'],'new_label':new['label'],'new_execution':new['execution'],'reference_execution':oldref,'new_cycles':new['cycles'],'reference_cycles':old['cycles'],'cycles_change_pct':percent(new['cycles'],old['cycles']),'new_IPC':new['IPC'],'reference_IPC':old['IPC'],'committed_and_rng_matched':True,'scope':'deterministic clean development comparison, not independent owner/fault CI'})
 for label,new in index.items():
  if new['program'] in ('checksum','pipeline_micro'):continue
  t=tasks[label];base=verified(t['architectural_reference'])
  if t['variant']=='QUERY_REC_Q2U1':
   compare('query_L2_vs_L1_at_update_L1',new,base,t['architectural_reference'])
   oldpath=Path(t['architectural_reference']['path']).parent.parent/(t['program']+'.R1.recurrent.L2')/'EXECUTION.json'
   compare('update_L1_vs_L2_at_query_L2',new,load(oldpath),ref(oldpath))
  elif t['variant']=='EARLY_REC_Q1U1':compare('early_vs_serial_REC_Q1U1',new,base,t['architectural_reference'])
  elif t['variant']=='EARLY_DIRECT_Q1U1':
   oldpath=Path(t['architectural_reference']['path']).parent.parent/(t['program']+'.R1.direct.L1')/'EXECUTION.json'
   compare('early_vs_serial_DIRECT_Q1U1',new,load(oldpath),ref(oldpath))
 for program in ('qsort_small','dijkstra_small','sha1'):
  a=index.get(program+'.R1.EARLY_DIRECT_Q1U1');b=index.get(program+'.R1.EARLY_REC_Q1U1')
  if a and b and a['valid'] and b['valid']:
   r=load(b['execution']['path']);compare('early_DIRECT_vs_early_REC_Q1U1',a,r,b['execution'])
 for mode in ('recurrent','direct'):
  a=index.get('micro.'+mode+'.E1');b=index.get('micro.'+mode+'.E0')
  if a and b and a['valid'] and b['valid']:
   compare('synthetic_micro_early_vs_serial_Q2U1',a,load(b['execution']['path']),b['execution'])
 result={'status':f['status'],'at_America_New_York':datetime.datetime.now(ZoneInfo('America/New_York')).isoformat(),'proposal':ref(BASE/'reports/CPU18_PROPOSAL.lock.json'),'authorization':ref(BASE/'reports/CPU_AUTHORIZATION.lock.json'),'terminal':ref(final),'analyzer':ref(__file__),'executed':len(rows),'valid':sum(x['valid'] for x in actual),'failures':failures,'unrun':f['extra']['unrun'],'overlap_gate':verified(ref(BASE/'reports/CPU_OVERLAP_GATE.json'))['extra'],'raw_file_SHA_checks':checked_files,'new_rows':actual,'comparisons':comparisons,'resources':f['resources'],'interpretation_limits':['No new fault events: not A/B/C/D or B-D','Exposed R1 development inputs and seed548, no independent holdout CI','Micro is synthetic, not HW1/SPEC execution workload','Stall counters overlap and may count readiness calls; do not sum to causal CPI','Actual early overlap changes admission, callback and checkpoint timing together','Conditional next-PC/history dependencies and finite source/recovery fences remain','CPU consumer token routing/late-write port and BI storage fault scope remain excluded/unvalidated','S*346 P0/P_ED frequent/periodic/SECDED/TMR baselines preserved; no protection winner from this P0 cohort','C++ path-only v16 is not the producer of these CPU trials','No measured silicon timing/PPA/radiation qualification']}
 put(BASE/'reports/CPU18_ANALYSIS.json',result)
 print(json.dumps({'status':result['status'],'executed':len(rows),'valid':result['valid'],'comparisons':comparisons,'failures':failures},indent=2))
if __name__=='__main__':main()
