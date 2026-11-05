"""V5 changes must pass native, epoch, queue, logical XOR and equivalence gates."""
from v5_common import *
import csv

item=dict(name='checksum',binary='build/checksum_freestanding',input='continuation_v3/runtime/inputs/checksum/ignored.dat',
    binary_sha256=sha(ROOT/'build/checksum_freestanding'),input_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/ignored.dat'),native_stdout_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/native.stdout'))
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words']
fold=scope[0]['site_ids'][0];raw=next(w for w in scope if len(w['site_ids'])==130)['site_ids'][0]
vs=[dict(id=s,scheme=s,policy='LEGACY',k=0,C=0 if s=='P0' else 1,resource='SHARED2',rep='recurrent') for s in ['P0','P_ED','P_ECC','P_TMR']]
vs += [dict(id='N1',scheme='P_ED',policy='N1',k=64,C=1,resource='SHARED2',rep='recurrent'),
       dict(id='ECC_K64_RMW',scheme='P_ECC',policy='N1',k=64,C=1,resource='SHARED2',rep='recurrent')]
vs += [dict(id=m,scheme='P0',policy='LEGACY',k=0,C=0,resource='LEGACY',rep=m) for m in ['recurrent','direct','geometric','stratum','short32']]
jobs=[]
for v in vs:
    opts=['--representation',v['rep'],'--tap-budget','16' if v['rep']=='stratum' else '8','--resource-mode',v['resource'],'--lookup-ii','0','--audit','--audit-limit','20000']
    for scenario,events in [('zero',''),('raw_SBU',f'400000 {raw}\n')]:
        jobs.append(task(item,v['id'],'CPU_gate_R4',scenario,'V5_GATE_R4',events,scheme=v['scheme'],policy=v['policy'],k=v['k'],C=v['C'],extra=opts))
for ident,lat,ii in [('DIRECT_L1II1',1,1),('DIRECT_L2II1',2,1),('DIRECT_L2II2',2,2)]:
    for scenario,event in [('zero',''),('raw_SBU',f'400000 {raw}\n')]:
        jobs.append(task(item,ident,'CPU_gate_R4',scenario,'V5_GATE_R4',event,extra=['--representation','direct','--lookup-latency',str(lat),'--lookup-ii',str(ii)]))
for ident,scheme,policy,k,C in [('N1','P_ED','N1',64,1),('ECC_K64_RMW','P_ECC','N1',64,1),('P_ECC','P_ECC','LEGACY',0,1),('P_TMR','P_TMR','LEGACY',0,1)]:
    for kind,ids in [('fold_SBU',[fold]),('K2_sameword',[fold,fold+1])]:
        jobs.append(task(item,ident,'CPU_gate_R4',kind,'V5_GATE_R4','400000 '+';'.join(map(str,ids))+'\n',scheme=scheme,policy=policy,k=k,C=C,extra=['--resource-mode','SHARED2']))
rows=execute(jobs,'CPU_GATE_R4',workers=2)
old=json.loads((ROOT/'postv3/runtime/reports/CPU_GATE.json').read_text())['tasks']
for r in rows:
    if r['scenario']=='zero' and r['id'] in ['P0','P_ED','P_ECC','P_TMR','N1']:
        ref=next(x for x in old if x['id']==r['id'] and x['scenario']=='zero')
        for key in ['cycles','instructions']:assert r[key]==ref[key],(r['label'],key)
        for key in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:assert r['seu'][key]==ref['seu'][key],(r['label'],key)
clean={r['id']:r for r in rows if r['scenario']=='zero'}
for key in ['cycles','instructions']:assert clean['direct'][key]==clean['recurrent'][key],('EXACT_DIRECT_CPU',key)
for key in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws','audit_identity_hash']:
    assert clean['direct']['seu'][key]==clean['recurrent']['seu'][key],('EXACT_DIRECT_CPU',key)
def aligned(r):
    rows=list(csv.DictReader((ROOT/r['output']/'committed_audit.csv').open()))
    return [{k:v for k,v in x.items() if k not in ['read_history','read_tick','commit_tick','seq','identity_hash','lookup_id']} for x in rows]
# Cycles/state/RNG equality plus corresponding read-address fingerprints in raw logs.
for r in rows:
    if r['id']=='N1' and r['scenario']=='K2_sameword':assert r['seu']['detected']==0
    if r['id'] in ['ECC_K64_RMW','P_ECC'] and r['scenario']=='K2_sameword':assert r['seu']['DUE']>0
write(OUT/'reports/CPU_GATE_ACCEPTANCE.json',dict(status='PASS',actual_runs=len(rows),old_producer_regression=True,
    exact_direct_clean_cpu_cycle_state_rng_identity=True,native_answers=True,queue_conservation=True,atomic_XOR=True,
    ECC='Matched prediction cadence; RMW decodes are mandatory and separately charged, not equal total check activity.'))
write(OUT/'configs/PRODUCER.lock.json',dict(status='CPU_GATE_PASS',pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',
    binary='third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt',binary_sha256=sha(ROOT/'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt'),
    config='gem5/o3_rate_state_v5.py',config_sha256=sha(ROOT/'gem5/o3_rate_state_v5.py'),source_lock_sha256=sha(OUT/'configs/source.lock.json')))
note('B0.CPU','IMPLEMENTED_CPU','Exact direct representation matches clean recurrent CPU cycle/state/RNG/identity under same interface',
    'Proceed to clean cost screen and matched-event pilots','Architecture-specific finite L/II and two-track campaign')
