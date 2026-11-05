import json,statistics
from continuation_common import *
x=json.loads((OUT/'reports/G4_CPU_DESIGN_V2.json').read_text());assert x['status']=='PASS'
clean=[r for r in x['tasks'] if r['scenario']=='zero'];by={(r['program'],r['id']):r for r in clean}
rejected={};finalists=[]
for variant in ['N1','H1','N1_U1']:
 overhead={prog:100*(by[prog,variant]['cycles']/by[prog,'P0']['cycles']-1) for prog in ['qsort_small','dijkstra_small']}
 if max(overhead.values())>2:rejected[variant]=dict(reason='frozen2pct maximum clean engineering budget exceeded on development program',clean_overhead_pct=overhead)
 elif variant in ['N1','H1']:finalists.append(variant)
variants=[r for r in json.loads((OUT/'configs/cpu_design.runs.lock.json').read_text())['variants'] if r['id'] in ['P0','P_ED','P_ECC','P_TMR']+finalists]
#10owners is a preregistered bounded confirmatory input/owner holdout, not a p95 guarantee.
write(OUT/'configs/cpu_policy_freeze.lock.json',dict(status='FROZEN_BEFORE_NEW_INPUT_POLICY_EVALUATION',variants=variants,finalists=finalists,rejected_development=rejected,owners_per_scenario=10,scenarios=['SBU_SINGLE','CHARM_6T'],input_lock_sha256=sha(OUT/'configs/holdout_inputs.lock.json'),design_sha256=sha(OUT/'reports/G4_CPU_DESIGN_V2.json'),source_lock_sha256=sha(OUT/'configs/gem5_source.lock.json'),design_fault_seed_base=1815480000,holdout_fault_seed_base=1915480000,selection='Gate-valid plus maximum clean overhead2pct; baseline4mandatory even ifoverbudget; no tuning after holdout',lower_budgets_pct=[.25,.5,1,2],residual_budgets_pct=[.5,1,2,5],no_field_scope_reselection=True,hardware_authorized=False))
decision('G5','Freeze before new inputs and owners; do not rescue a slow candidate by tuning on holdout.', ['G4_CPU_DESIGN_V2.json','CPU_DESIGN_SUMMARY.json','cpu_policy_freeze.lock.json'],f'Finalists{finalists}; rejected development{list(rejected)};10owners x2scenarios x3newinputs plus baselines.', 'Run measured-budget holdout; preserve performance losers/helpful/latent/no-event results.')
print('FROZEN',finalists,rejected)
