from v5_r5_common import *
item=dict(name='checksum',binary='build/checksum_freestanding',input='continuation_v3/runtime/inputs/checksum/ignored.dat',binary_sha256=sha(ROOT/'build/checksum_freestanding'),input_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/ignored.dat'),native_stdout_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/native.stdout'))
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'];raw=next(w['site_ids'][0] for w in scope if len(w['site_ids'])==130)
ids=['FINITE0','PARITY64','ECC64_RMW','TMR','NATIVE','NATIVE_PORT1','DIRECT_ISO','DIRECT_J0','BATCH_DIRECT','BATCH_UNDO1','BATCH_READ1','BATCH_READ2','BATCH_STRAT16']
jobs=[make(item,ident,'CPU_GATE','zero','R5_GATE',extra=['--audit','--audit-limit','2000']) for ident in ids]
for ident in ['BATCH_DIRECT','BATCH_STRAT16']:
 for scenario,sites in [('SBU',[raw]),('K2',[raw,raw+1])]:jobs.append(make(item,ident,'CPU_GATE',scenario,'R5_GATE','400000 '+';'.join(map(str,sites))+'\n'))
old_manifest=json.loads((OLD/'reports/CPU_gate_R4/checksum.zero.V5_GATE_R4.DIRECT_L1II1/logical_manifest.json').read_text())
head=next(s['id'] for s in old_manifest['additional_sites'] if s['structure']=='journal_head' and s['bit']==0)
for scenario,sites in [('HEAD_RAW_FORWARD',[head,raw]),('HEAD_RAW_REVERSE',[raw,head])]:jobs.append(make(item,'BATCH_DIRECT','CPU_GATE',scenario,'R5_GATE','400000 '+';'.join(map(str,sites))+'\n'))
rows=execute(jobs,'CPU_GATE',workers=2)
forward=next(r for r in rows if r['scenario']=='HEAD_RAW_FORWARD');reverse=next(r for r in rows if r['scenario']=='HEAD_RAW_REVERSE')
for key in ['cycles','instructions']:assert forward[key]==reverse[key],('ATOMIC_HEAD_ORDER',key)
assert forward['seu']['canonical_base_state_hash']==reverse['seu']['canonical_base_state_hash'],'ATOMIC_HEAD_STATE_ORDER'

old=json.loads((OLD/'reports/CPU_GATE_R4.json').read_text())['tasks'];mapping={'FINITE0':'P0','PARITY64':'N1','ECC64_RMW':'ECC_K64_RMW','TMR':'P_TMR','NATIVE':'recurrent','DIRECT_ISO':'direct'}
for row in rows:
 if row['scenario']!='zero' or row['id'] not in mapping:continue
 ref=next(x for x in old if x['id']==mapping[row['id']] and x['scenario']=='zero')
 for k in ['cycles','instructions']:assert row[k]==ref[k],(row['id'],k)
 for k in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:assert row['seu'][k]==ref['seu'][k],(row['id'],k)
for row in rows:
 if row['id'].startswith('BATCH'):
  assert row['seu']['journal_merge_undo']==1 and row['seu']['coalesced_undo_operations']>0
  assert row['seu']['journal_accepted']==row['seu']['journal_completed']+row['seu']['journal_pending']+row['seu']['journal_cancelled']
write(OUT/'reports/CPU_GATE_ACCEPTANCE.json',dict(status='PASS',actual_runs=len(rows),R4_unchanged_controls_exact=True,
 native_outputs=True,finite_conservation=True,BPU_batch_hook_observed=True,mid_service_cpp_source_and_queue_SEU=True,
 no_physical_port_or_timing_claim=True))
producer=json.loads((OUT/'configs/BUILT_PRODUCER.pending.json').read_text());producer.update(status='CPU_GATE_PASS',gate_sha256=sha(OUT/'reports/CPU_GATE_ACCEPTANCE.json'));write(OUT/'configs/PRODUCER.lock.json',producer)
print('PASS R5 native/conservation gates and R4 exact compatibility')
