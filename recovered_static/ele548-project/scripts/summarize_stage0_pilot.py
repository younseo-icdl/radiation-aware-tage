#!/usr/bin/env python3
import csv,json,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((root/'reports/pilot_240trials.csv').open()))
summary=[]
for w in sorted({r['workload'] for r in rows}):
 for field in ['bimodal','ctr','tag','u','raw_path','folded']:
  rs=[r for r in rows if r['workload']==w and r['field']==field]
  summary.append({'workload':w,'field':field,'trials':len(rs),'trials_with_prediction_divergence':sum(int(r['prediction_divergences'])>0 for r in rs),'harm':sum(int(r['harm']) for r in rs),'help':sum(int(r['help']) for r in rs),'net':sum(int(r['net']) for r in rs),'max_trial_harm':max(int(r['harm']) for r in rs),'residual_nonzero_trials':sum(int(r['end_differing_logical_bits'])>0 for r in rs),'mean_trial_seconds':statistics.mean(float(r['trial_wall_seconds']) for r in rs)})
result={'status':'PASS_BOUNDED_PILOT_NOT_E1_CAMPAIGN','model':'M0 conditional SBU','total_trials':len(rows),'failures':sum(r['status']!='PASS' for r in rows),'mean_trial_seconds':statistics.mean(float(r['trial_wall_seconds']) for r in rows),'by_workload_field':summary,'interpretation':'Inactive sites retained; harm and help preserved. Last divergence is not confirmed recovery. End residual is paired-state difference, not necessarily original physical fault persistence. Design scope remains UNFROZEN.'}
(root/'reports/pilot_summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
