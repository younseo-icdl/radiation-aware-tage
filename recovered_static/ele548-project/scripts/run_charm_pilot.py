#!/usr/bin/env python3
"""Bounded CHARM summary-informed P0 pilot; geometry/time are assumptions."""
import csv,hashlib,json,subprocess,time,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]
results=[]
for cell,seed in [('6t',548200),('8t',548300)]:
 source=root/f'data/curated/charm_{cell}_tableII.json';profile=json.loads(source.read_text());w=profile['multiplicity_counts']
 output=root/f'reports/charm_{cell}_60trials.csv';log=root/f'reports/charm_{cell}_60trials.log'
 command=[str(root/'build/pilot'),'5',str(seed),str(output),str(w['1']),str(w['2']),f'M1_CHARM_{cell.upper()}']
 start=time.perf_counter()
 with log.open('w') as f:r=subprocess.run(command,cwd=root,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(f'pilot failure: {cell}; see {log}')
 rows=list(csv.DictReader(output.open()));assert len(rows)==60
 for row in rows:
  ids=list(map(int,row['event_site_ids'].split(';')));assert len(ids)==int(row['multiplicity'])==len(set(ids));assert row['status']=='PASS'
  assert int(row['net'])==int(row['harm'])-int(row['help'])
 grouped=[]
 for workload in ['SHORT-INT-1','SHORT-FP-1']:
  for field in ['bimodal','ctr','tag','u','raw_path','folded']:
   v=[x for x in rows if x['workload']==workload and x['field']==field]
   grouped.append({'workload':workload,'field':field,'trials':len(v),'K2_trials':sum(int(x['multiplicity'])==2 for x in v),'harm':sum(int(x['harm']) for x in v),'help':sum(int(x['help']) for x in v),'net':sum(int(x['net']) for x in v)})
 results.append({'model':f'M1_CHARM_{cell.upper()}','profile':str(source.relative_to(root)),'profile_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_counts':w,'source_K2_probability':int(w['2'])/(int(w['1'])+int(w['2'])),'trials':60,'K2_trials_observed':sum(int(x['multiplicity'])==2 for x in rows),'wall_seconds':time.perf_counter()-start,'max_RSS_KiB':max(int(x['peak_rss_kib']) for x in rows),'mean_trial_seconds':statistics.mean(float(x['trial_wall_seconds']) for x in rows),'CSV':str(output.relative_to(root)),'CSV_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'by_workload_field':grouped})
report={'status':'PASS_BOUNDED_P0_MODEL_INTEGRATION_SMOKE','models':results,'assumptions':['K distribution comes from source TableII, separately per cell type','one event per trial; time uniform conditional ordinal, no measured target rate','K unique consecutive IDs in within-field logical flattening; no physical adjacency calibration','sample valid anchors; endpoints have different bit hit probability for K2; no clipping/wrapping','non-spec trace replay; no gem5 radiation campaign','5 trials/field/workload insufficient for ranking or scope freeze'],'S_star':'UNFROZEN'}
(root/'reports/CHARM_INJECTION_PILOT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({m['model']:{k:m[k] for k in ['trials','K2_trials_observed','wall_seconds','max_RSS_KiB']} for m in results},indent=2))
