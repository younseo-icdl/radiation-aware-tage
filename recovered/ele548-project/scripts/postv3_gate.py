"""Exact corrected-C compatibility then directed grouped-recovery acceptance."""
from postv3_common import *
item=dict(name='checksum',binary='build/checksum_freestanding',input='continuation_v3/runtime/inputs/checksum/ignored.dat',
          binary_sha256=sha(ROOT/'build/checksum_freestanding'),
          input_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/ignored.dat'),
          native_stdout_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/native.stdout'))
base=[dict(id=s,scheme=s,policy='LEGACY',k=0,C=0 if s=='P0' else 1) for s in ['P0','P_ED','P_ECC','P_TMR']]
allvariants=base+variants
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words']
site=scope[0]['site_ids'][0];second=scope[0]['site_ids'][1]
jobs=[]
for v in allvariants:
    for scenario,event in [('zero',''),('SBU',f'400000 {site}\n')]:
        jobs.append(task(v,item,'CPU_gate',scenario,'POSTV3_GATE',event))
for v in variants:
    jobs.append(task(v,item,'CPU_gate','K2_sameword','POSTV3_GATE',f'400000 {site};{second}\n'))
old_manifest=json.loads((ROOT/'continuation_v3/runtime/reports/B_CPU_gate/P.zero/logical_manifest.json').read_text())
meta=[s['id'] for s in old_manifest['additional_sites'] if s['structure']=='staged_control']
parity=next(s['id'] for s in old_manifest['additional_sites'] if s['structure']=='parity')
for v in variants:
    if v['policy']!='STAGED':continue
    for scenario,event in [
        ('K2_diffword',f"400000 {site};{scope[1]['site_ids'][0]}\n"),
        ('code_SBU',f'400000 {parity}\n'),
        ('metadata_SBU',f'400000 {meta[0]}\n'),
        ('metadata_DUE',f'400000 {meta[0]};{meta[1]}\n')]:
        jobs.append(task(v,item,'CPU_gate',scenario,'POSTV3_GATE',event))
rows=execute(jobs,'CPU_GATE')
old=json.loads((ROOT/'continuation_v3/runtime/reports/C_CPU_GATE.json').read_text())['tasks']
mapping={'P_ED':'ED','P_ECC':'ECC','P_TMR':'TMR','P_3STAGE':'P','N1':'N1','P0':'P0'}
for row in rows:
    if row['scenario']!='zero' or row['id'] not in mapping:continue
    ref=next(t for t in old if t['id']==mapping[row['id']] and t['scenario']=='zero')
    for key in ['cycles','instructions']:assert row[key]==ref[key],('CORRECTED_C_CHANGED',row['id'],key)
    for key in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:
        assert row['seu'][key]==ref['seu'][key],('CORRECTED_C_STATE_CHANGED',row['id'],key)
for r in rows:
    if r['id'].startswith('P_') and r['scheme']=='P_ED' and r['scenario']=='K2_sameword':assert r['seu']['detected']==0
    if r['scenario'] in ['K2_diffword','code_SBU','metadata_SBU','metadata_DUE']:
        assert r['seu']['detected']>0,('DIRECTED_NOT_DETECTED',r['label'])
write(OUT/'reports/CPU_GATE_ACCEPTANCE.json',dict(status='PASS',new_actual_runs=len(rows),
    corrected_C_clean_bit_rng_cycle_equality=True,mandatory_baselines_retained=True,safe_grouping=True))
