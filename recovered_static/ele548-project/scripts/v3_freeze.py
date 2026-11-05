import json
from v3_common import *
x=json.loads((OUT/'reports/CPU_DESIGN.json').read_text());assert x['status'] in ['PASS','FAIL_RETAINED'];summary=json.loads((OUT/'reports/CPU_DESIGN_SUMMARY.json').read_text())
whole=json.loads((OUT/'reports/B_WHOLE_DESIGN.json').read_text());assert whole['status'] in ['PASS','FAIL_RETAINED']
direct=json.loads((OUT/'reports/B_DIRECTED.json').read_text());assert direct['status'] in ['PASS','FAIL_RETAINED']
resource=json.loads((OUT/'reports/B_RESOURCE.json').read_text());assert resource['status'] in ['PASS','FAIL_RETAINED']
adversarial=json.loads((OUT/'reports/B_ADVERSARIAL.json').read_text());assert adversarial['status'] in ['PASS','FAIL_RETAINED']
assert adversarial['guaranteed_envelope_failures']==0,'In-envelope recovery failure requires a new development fix, not a holdout'
producer=json.loads((OUT/'configs/FINAL_PRODUCER.lock.json').read_text());assert producer['status']=='CPU_GATE_PASS_BEFORE_EVALUATION'
clean={(r['program'],r['id']):r for r in x['tasks'] if r['scenario']=='zero' and r['status']=='PASS'};base={program:r for (program,v),r in clean.items() if v=='P0'}
all_variants=json.loads((OUT/'configs/CPU_design.runs.lock.json').read_text())['variants'];final=[];rejected={}
for v in all_variants:
 if v['id']=='H1_COMBINED':continue
 if v['id'] not in ['V3_D','V3_P']:final.append(v);continue
 rr=[r for r in x['tasks'] if r['id']==v['id']];fails=[r for r in rr if r['status']!='PASS']+[r for r in whole['tasks'] if r['id']==v['id'] and r['status']!='PASS']+[r for r in direct['tasks'] if r['id']==('P' if v['id']=='V3_P' else 'Dshared2') and r['status']!='PASS']+[r for r in resource['tasks'] if r['id']==v['id'] and r['status']!='PASS'];overheads={r['program']:100*(r['cycles']/base[r['program']]['cycles']-1) for r in rr if r['scenario']=='zero' and r['status']=='PASS'}
 if fails or len(overheads)!=3 or max(overheads.values())>2:
  rejected[v['id']]=dict(reason='correctness/protocol gate or predeclared maximum normal overhead2pct',failures=len(fails),clean_overhead_pct=overheads)
 else:final.append(v)
write(OUT/'configs/CANDIDATE_SPEC.lock.json',dict(status='FROZEN_BEFORE_NEW_EVALUATION',variants=final,new_finalists=[v['id'] for v in final if v['id'].startswith('V3_')],rejected_development=rejected,development_sha256=sha(OUT/'reports/CPU_DESIGN.json'),producer=producer,source_lock_sha256=producer['source_lock_sha256'],input_lock_sha256=sha(OUT/'configs/evaluation_inputs.lock.json'),endpoint=dict(resource_mode='SHARED2',latency=1,II=1,hot_queue_depth=64,shadow_queue_depth=8,operands='read at service completion; no early publish',retirement='real pre-ROB retirement operand/queue credit hook'),selection_budget_pct=2,no_tuning_after_freeze=True,hardware_authorized=False))
write(OUT/'configs/NEW_HOLDOUT.lock.json',dict(status='FROZEN_BEFORE_POLICY_EVALUATION',programs=json.loads((OUT/'configs/evaluation_inputs.lock.json').read_text())['programs'],owner_seed_base=2515480000,owners_per_program_scenario=10,scenarios=['SBU_SINGLE','CHARM_6T','CERN_P29_INTERLEAVED'],old_holdout_seen=True,new_program_population=False))
decision('G6','Freeze gate-valid affordable variants before new input evaluation.', ['reports/CPU_DESIGN.json','reports/CPU_DESIGN_SUMMARY.json','configs/CANDIDATE_SPEC.lock.json'], {'finalists':[v['id'] for v in final],'rejected':rejected}, 'Run all fixed evaluation owners; do not tune using these outcomes.',expense='fixed10owners/program/scenario, no silent sample reduction')
print('Frozen',len(final),'schemes; rejected',list(rejected))
