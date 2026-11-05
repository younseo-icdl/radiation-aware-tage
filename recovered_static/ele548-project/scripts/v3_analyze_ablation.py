import json,csv,statistics
from v3_common import *
lines=['# Cost and mechanism evidence','', 'All rows below refer to newly executed v3 evidence. Diagnostic cost removals are excluded from deployable performance comparisons.','', '|program|cost removal|cycles|source decodes|shadow decodes|rebuild steps|','|---|---|---:|---:|---:|---:|']
x=json.loads((OUT/'reports/A1_COST.json').read_text());assert x['status']=='PASS'
for r in x['tasks']:
 s=r['seu'];lines.append(f"|{r['program']}|{r['cost_remove']}|{r['cycles']}|{s['source_decodes']}|{s['shadow_decodes']}|{s['rebuild_steps']}|")
lines+=['', 'The source/spec removal includes the compound fold/source update service job. The historical debt model lacks individual decoder service endpoints, so these are overlapping upper bounds, not additive CPI attribution. Recovery-only removal has no clean benefit. All-cost-zero retains actual functions and matches pristine clean cycles.', '', '|event shape|recovery|mean additional misses|owners|', '|---|---|---:|---:|']
a=json.loads((OUT/'reports/A3_FUNCTIONAL_V2.json').read_text());assert a['status']=='PASS'
for shape in ['raw_SBU','fold_SBU']:
 for v in ['H1_RESET','H1_REBUILD']:
  rr=[r for r in a['tasks'] if r['shape']==shape and r['id']==v];lines.append(f"|{shape}|{v}|{statistics.mean(int(r['metrics']['net']) for r in rr):.4f}|{len(rr)}|")
lines+=['', 'The revised controlled reset preserves the same real-commit shadow maintenance. It reinitializes the prediction source/folds; rebuild instead restores from that verified shadow. Fold sites cover all seven banks. Events/input/owner/hash are frozen. Two historical traces remain development data; this is not new workload validation. The initial revision which discarded shadow history is retained separately and is not used as the matched-shadow result.', '']
path=OUT/'reports/A2_FACTORIAL.json'
if path.exists() and json.loads(path.read_text())['status']=='PASS':
 f=json.loads(path.read_text());lines+=['|program|backend|k|U|cycles|full reduction bits|incremental XOR inputs|','|---|---|---:|---:|---:|---:|---:|']
 for r in f['tasks']:
  s=r['seu'];lines.append(f"|{r['program']}|{'FULL' if r.get('full_delta') else 'INC'}|{r['k']}|{r['U']}|{r['cycles']}|{s['full_reduction_bits']}|{s['fold_delta_xor_inputs']}|")
 for program in sorted({r['program'] for r in f['tasks']}):
  for k in [1,64]:
   for u in [0,1]:
    rr=[r for r in f['tasks'] if r['program']==program and r['k']==k and r['U']==u]
    assert len(rr)==2
    assert rr[0]['cycles']==rr[1]['cycles'],'Backend effect on cycles requires analysis; do not call invariant'
 lines+=['', 'At fixed k and historical per-callback service charge, FULL and INC have identical measured cycles in these clean runs. Arithmetic/read counts differ; the cycle model does not distinguish their gate/energy cost. The k and service effects therefore cannot be attributed to incremental parity alone.']
(OUT/'COST_CAUSAL_REPORT.md').write_text('\n'.join(lines)+'\n')
print('Actual cost/controlled-recovery report updated')
