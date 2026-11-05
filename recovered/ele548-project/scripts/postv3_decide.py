"""Apply the declared development screen; never force a new architecture."""
import collections
import statistics
from postv3_common import *
analysis=json.loads((OUT/'reports/G2_ANALYSIS.json').read_text())
rules=json.loads((OUT/'configs/round.lock.json').read_text())['candidate_screen_predeclared_before_G2']
results=[]
for name in ['P_ALL130','P_2_EARLY','P_2_LATE']:
    rows=[r for r in analysis['pairs'] if r['variant']==name]
    per=collections.defaultdict(list)
    for row in rows:per[row['program'],row['scenario']].append(row)
    mean=statistics.mean(statistics.mean(r['gain_vs_N1_pp'] for r in rr) for rr in per.values())
    worst=min(statistics.mean(r['gain_vs_N1_pp'] for r in rr) for rr in per.values())
    residual=max(statistics.mean(r['fault_residual_pp'] for r in rr) for rr in per.values())
    clean=max(r['clean_delta_pct'] for r in rows)
    qualifies=(mean>=rules['minimum_equal_program_mean_gain_vs_N1_pp'] and
        worst>=-rules['maximum_program_scenario_mean_regression_pp'] and
        residual<=rules['residual_mean_budget_pp'] and clean<=rules['normal_overhead_budget_pct'])
    results.append(dict(variant=name,mean_gain_vs_N1_pp=mean,worst_program_scenario_gain_pp=worst,
        worst_mean_residual_pp=residual,maximum_clean_overhead_pct=clean,qualifies_for_new_evaluation=qualifies))
selected=sorted([r for r in results if r['qualifies_for_new_evaluation']],key=lambda r:-r['mean_gain_vs_N1_pp'])[:2]
status='NEW_EVALUATION_REQUIRED' if selected else 'REJECT_GROUPED_EXTENSIONS_RETAIN_N1_REFERENCE'
write(OUT/'reports/G2_DECISION.json',dict(status=status,screen=rules,results=results,
    selected=[r['variant'] for r in selected],not_equivalence_proof=True,
    G3='not justified by small CPU benefit unless phase evidence demonstrates a substantial avoidable bottleneck',
    G4='directed blind-spot tests retained; detector comparison is a separate axis, not silently mixed into grouping'))
print(status)
for row in results:print(row)
