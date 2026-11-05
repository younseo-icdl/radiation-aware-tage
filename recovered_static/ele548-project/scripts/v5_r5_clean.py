from v5_r5_common import *
assert json.loads((OUT/'reports/CPU_GATE_ACCEPTANCE.json').read_text())['status']=='PASS'
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
ids=['NATIVE','NATIVE_PORT1','FINITE0','PARITY64','ECC64_RMW','SHORT32','BATCH_DIRECT','BATCH_UNDO1','BATCH_READ1','BATCH_READ2','BATCH_STRAT16']
write(OUT/'configs/variants.lock.json',dict(status='FROZEN_BEFORE_CLEAN',variants={k:V[k] for k in ids},
 primary='Batch rewindL2, appendL1/II1/depth64, lookup0/II1; UNDO1 optimistic sensitivity only. No further design/tap refinement.',
 original_common_native_reference='NATIVE unchanged; PORT1 secondary matched bandwidth control. Do not switch denominator after seeing results.'))
rows=execute([make(item,ident,'CLEAN','zero','R5_CLEAN') for item in inputs for ident in ids],'CLEAN',workers=8,pilot_first_batch=2)
old=json.loads((OLD/'reports/CLEAN.json').read_text())['tasks']
for r in rows:
 if r['id'] not in ['NATIVE','NATIVE_PORT1','FINITE0','PARITY64','ECC64_RMW','SHORT32']:continue
 ref=next(x for x in old if x['program']==r['program'] and x['id']==r['id'])
 for k in ['cycles','instructions']:assert r[k]==ref[k],('R4_FULL_PROGRAM_CHANGED',r['program'],r['id'],k)
 for k in ['canonical_base_state_hash','predictor_rng_hash']:assert r['seu'][k]==ref['seu'][k],('R4_STATE_CHANGED',k)
write(OUT/'reports/CLEAN_COMPATIBILITY.json',dict(status='PASS',programs=3,baseline_variants=6,exact_cycle_state_rng=True))
