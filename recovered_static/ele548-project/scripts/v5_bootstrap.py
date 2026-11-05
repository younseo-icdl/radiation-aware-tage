from v5_common import *
import subprocess

for p in ['reports','configs','sources','inputs','literature']:(OUT/p).mkdir(exist_ok=True)
paths=set(subprocess.check_output(['git','ls-files'],text=True,cwd=ROOT).splitlines())
paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'postv3/runtime').rglob('*') if p.is_file())
paths.add('reports/BP_SEU_PostV3_Completed_20261014.zip')
baseline=OUT/'configs/PRESERVED_BASELINE.json'
if not baseline.exists():
    write(baseline,dict(branch='research/postv3-promotion',commit='6f57ea5eb2a993cfa3bb7ead5b673613f4db122f',
        hashes={p:sha(ROOT/p) for p in sorted(paths) if not p.startswith('rate_state_v5/') and (ROOT/p).is_file()}))
limits=json.loads((ROOT/'rate_state_v5/handoff/BP_SEU_Rate_State_Research_Handoff_v5/configs/research_limits.json').read_text())
write(OUT/'configs/limits.lock.json',limits)
write(OUT/'configs/protocol.lock.json',dict(status='PREDECLARED_BEFORE_NEW_PREDICTOR',
    clock_Hz=2_000_000_000,normal_budget_percent=2,minimum_gain_pp=.05,regression_warning_pp=.05,
    residual_budget_pp=2,tap_family_cap=2,initial_taps=8,one_refinement_taps=16,
    short_history_max=32,initial_cpp_owners=8,initial_cpu_stratum_owners=8,
    development_inputs='continuation_v3/runtime/configs/design_inputs.lock.json',
    evaluation_inputs='NEW_V5_NAMESPACE_REQUIRED',event_seed_development=3155480000,event_seed_evaluation=3255480000,
    baseline_scope='fixed S*346 for protection; representation has architecture-specific manifest',
    resource_tracks=['same-interface isolation','architecture-specific finite lookup L/II'],
    rates=dict(rho_diagnostic=[.01,.1,1,10],legacy_targeted_events_per_cycle=1e-6),
    final_owner_count=20,programs=['qsort_small','dijkstra_small','sha1']))
item=dict(name='checksum',binary='build/checksum_freestanding',input='continuation_v3/runtime/inputs/checksum/ignored.dat',
    binary_sha256=sha(ROOT/'build/checksum_freestanding'),input_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/ignored.dat'),
    native_stdout_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/native.stdout'))
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words']
jobs=[task(item,'P0','S0','zero','V5_REGRESSION',extra=['--resource-mode','SHARED2']),
      task(item,'N1','S0','SBU','V5_REGRESSION',f"400000 {scope[0]['site_ids'][0]}\n",scheme='P_ED',policy='N1',k=64,C=1,extra=['--resource-mode','SHARED2'])]
if not (OUT/'reports/S0_REGRESSION.json').exists():execute(jobs,'S0_REGRESSION',old=True)
old=json.loads((ROOT/'postv3/runtime/reports/CPU_GATE.json').read_text())['tasks']
for new in json.loads((OUT/'reports/S0_REGRESSION.json').read_text())['tasks']:
    ref=next(r for r in old if r['id']==new['id'] and r['scenario']==new['scenario'])
    for k in ['cycles','instructions']:assert new[k]==ref[k],k
    for k in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:assert new['seu'][k]==ref['seu'][k],k
write(OUT/'reports/S0_ACCEPTANCE.json',dict(status='PASS',old_producer_exact_cycle_state_rng_equality=True,
    latest_live_commit='6f57ea5eb2a993cfa3bb7ead5b673613f4db122f',package_implementation_commit='583fa74a78c19fb112642ae440a890a3d558223c',
    difference='Live final reports newer than package implementation pointer; same postv3 producer and inputs.'))
note('S0','TESTED_RESULT','Old producer clean and one fault match frozen evidence exactly','Preserve; proceed to both tracks','Exact direct-fold gate and rate anchor audit')
