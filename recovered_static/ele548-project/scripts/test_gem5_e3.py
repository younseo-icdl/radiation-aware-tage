#!/usr/bin/env python3
"""Bounded real-O3 protocol/injection gate, before representative CPU campaigns."""
import concurrent.futures
import csv
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from run_o3_public_baseline import stats
ROOT=Path(__file__).resolve().parents[1]
ACTIVE={}
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
SCHEMES=['P0','P_ED','P_ECC','P_TMR']
def main():
    binary=ROOT/'third_party/gem5-e3/build/X86_STAGE0/gem5.opt';output=ROOT/'reports/e3_integration/gate';output.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    cases=[]
    ACTIVE.update(cases=cases,binary=str(binary))
    def run(label,scheme,events=(),check=0,repair=0):
        d=output/label;d.mkdir(exist_ok=True);schedule=d/'schedule.ticks'
        schedule.write_text(''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
        command=[str(binary),'--outdir='+str(d),str(ROOT/'gem5/o3_seu.py'),'--binary',str(ROOT/'build/checksum_freestanding'),
            '--scheme',scheme,'--check-cycles',str(check),'--repair-cycles',str(repair),'--read-log']
        if events:command+=['--schedule',str(schedule)]
        record={'case':label,'scheme':scheme,'command':command,'event_schedule':str(schedule.relative_to(ROOT)),'schedule_sha256':sha(schedule),'log':str((d/'gem5.log').relative_to(ROOT))}
        start=time.perf_counter()
        with (d/'gem5.log').open('w') as f:
            try:p=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
            except subprocess.TimeoutExpired:return dict(record,status='FAIL_TIMEOUT',wall_seconds=time.perf_counter()-start)
        record.update(exit_code=p.returncode,wall_seconds=time.perf_counter()-start)
        if p.returncode:return dict(record,status='FAIL_EXECUTION')
        try:
            assert (d/'program.stdout').read_text().strip()=='checksum=1321703870693' and not (d/'program.stderr').read_bytes()
            assert 'Exit cause: exiting with last active thread context code: 0' in (d/'gem5.log').read_text()
            seu=json.loads((d/'seu.json').read_text());s=stats(d/'stats.txt');manifest=json.loads((d/'logical_manifest.json').read_text())
            expected={'P0':65370,'P_ED':65434,'P_ECC':65532,'P_TMR':66062};assert manifest['total_bits']==expected[scheme]
            assert seu['applied_events']==len(events) and seu['applied_flips']==sum(len(ids) for _,ids in events)
            with (d/'events.csv').open() as f:
                applied=list(csv.DictReader(f))
            assert len(applied)==len(events)
            for e,(tick,ids) in zip(applied,events):
                assert int(e['tick'])==tick and list(map(int,e['site_ids'].split(';')))==list(ids) and e['XOR_verified']=='1'
                assert all(a!=b for a,b in zip(e['before_bits'],e['after_bits']))
            record.update(status='PASS',cycles=int(s['system.cpu.numCycles']),instructions=int(s['system.cpu.commitStats0.numInsts']),
                IPC=s['system.cpu.ipc'],conditional_mispredictions=int(s['system.cpu.branchPred.mispredicted_0::DirectCond']+s['system.cpu.branchPred.mispredicted_0::IndirectCond']),
                seu=seu,stats_sha256=sha(d/'stats.txt'),seu_sha256=sha(d/'seu.json'),manifest_sha256=sha(d/'logical_manifest.json'))
            if repair:
                with (d/'events.csv.repairs.csv').open() as f:repair_rows=list(csv.DictReader(f))
                assert len(repair_rows)==seu['repair_batches']
                previous=0
                for rr in repair_rows:
                    busy=max(previous,int(rr['tick']))+500*repair
                    assert int(rr['repair_busy_until'])==busy
                    previous=busy
                assert sum(seu['repairs_by_origin'])==len(repair_rows)
        except Exception as error:record.update(status='FAIL_VALIDATION',error=str(error))
        return record
    def execute(tasks):
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            batch=list(pool.map(lambda t:run(**t),tasks))
        cases.extend(batch)
        report('RUNNING_REAL_O3_GATE')
        for r in batch:print(json.dumps({k:r.get(k) for k in ['case','status','cycles','wall_seconds']},ensure_ascii=False),flush=True)
        if any(r['status']!='PASS' for r in batch):
            report('FAIL_REAL_O3_GATE');raise SystemExit(1)
        return batch
    def report(status):
        result={'status':status,'cases':cases,'binary_sha256':sha(binary),'source_lock_sha256':sha(ROOT/'sources/gem5_e3_source.lock.json'),
            'config_sha256':sha(ROOT/'gem5/o3_seu.py'),'trials':len(cases),'representative_CPU_campaign':False,
            'scope':'bounded synthetic checksum protocol gate, not representative radiation performance',
            'explicit_exclusions':'in-flight generation/fallback metadata, pending response/instruction and simulator timing tags; common CPU queues/BTB/RAS/architecture; shared combinational SET',
            'latency':'check-read latency; storage writeback begins at detection; every origin repair batch serializes response-port R cycles; independent backend update lane continues; consumption RMW check has zero added clean latency in this assumed interface'}
        (ROOT/'reports/E3_INTEGRATION_GATE.json').write_text(json.dumps(result,indent=2)+'\n')
    clean=execute([{'label':'clean_'+s,'scheme':s} for s in SCHEMES]);p0=clean[0];pristine=stats(ROOT/'reports/gem5_o3_opt_checksum/stats.txt')
    assert p0['cycles']==pristine['system.cpu.numCycles'] and p0['instructions']==pristine['system.cpu.commitStats0.numInsts']
    assert p0['conditional_mispredictions']==pristine['system.cpu.branchPred.mispredicted_0::DirectCond']+pristine['system.cpu.branchPred.mispredicted_0::IndirectCond']
    for r in clean:
        assert [r[k] for k in ['cycles','instructions','conditional_mispredictions']]==[p0[k] for k in ['cycles','instructions','conditional_mispredictions']]
        for key in ['canonical_base_state_hash','predictor_rng_draws','predictor_rng_hash']:assert r['seu'][key]==p0['seu'][key],key
        assert r['seu']['detected']==r['seu']['response_hold_cycles']==r['seu']['drain_hold_cycles']==0
    with (output/'clean_P0/prediction_reads.csv').open() as f:reads=list(csv.DictReader(f))
    tick=int(reads[90]['tick']);raw=65054;fold=65170
    singles=execute([{'label':f'{field}_single_{s}','scheme':s,'events':[(tick,[id])]} for field,id in [('raw',raw),('fold',fold)] for s in SCHEMES])
    for r in singles:
        assert r['seu']['lookups_at_fault_tick']>0
        if r['scheme'] in ['P_ECC','P_TMR']:
            assert r['seu']['corrected']>0 and r['cycles']==p0['cycles'] and r['seu']['canonical_base_state_hash']==p0['seu']['canonical_base_state_hash']
        if r['scheme']=='P_ED':assert r['seu']['reset_refill']>0 and r['seu']['refill_updates']>=130 and r['seu']['drains_completed']>0 and r['seu']['stale_restores_suppressed']>0
    codec=execute([
        {'label':'ED_parity_cell','scheme':'P_ED','events':[(tick,[65370])]},
        {'label':'ECC_check_cell','scheme':'P_ECC','events':[(tick,[65370])]},
        {'label':'TMR_replica_cell','scheme':'P_TMR','events':[(tick,[65370])]},
        {'label':'ED_even_pair','scheme':'P_ED','events':[(tick,[fold,fold+1])]},
        {'label':'ECC_DUE','scheme':'P_ECC','events':[(tick,[fold,fold+1])]},
        {'label':'ECC_triple_miscorrection','scheme':'P_ECC','events':[(tick,[fold,65370,65371])]},
        {'label':'TMR_two_copies_same_bit','scheme':'P_TMR','events':[(tick,[fold,65370])]},
        {'label':'TMR_two_copies_different_bits','scheme':'P_TMR','events':[(tick,[fold,65371])]},
        {'label':'TMR_three_copies_same_bit','scheme':'P_TMR','events':[(tick,[fold,65370,65716])]},
        {'label':'same_tick_two_distinct_events','scheme':'P0','events':[(tick,[fold]),(tick,[fold])]},
        {'label':'ED_recovery_flag','scheme':'P_ED','events':[(tick,[65433])]},
        {'label':'ECC_epoch_control','scheme':'P_ECC','events':[(tick,[65530])]},
        {'label':'ECC_refill_control','scheme':'P_ECC','events':[(tick,[65491])]}
    ])
    by={r['case']:r for r in codec}
    assert by['ED_even_pair']['seu']['detected']==0
    assert by['ECC_DUE']['seu']['DUE']>0 and by['ECC_DUE']['seu']['refill_updates']>=130
    assert by['ECC_triple_miscorrection']['seu']['corrected']>0 # apparent decoder correction; not oracle success
    assert by['TMR_three_copies_same_bit']['seu']['detected']==0
    assert by['TMR_two_copies_different_bits']['seu']['canonical_base_state_hash']==p0['seu']['canonical_base_state_hash']
    assert by['same_tick_two_distinct_events']['seu']['canonical_base_state_hash']==p0['seu']['canonical_base_state_hash']
    timing=execute([{'label':'latency_clean_'+s,'scheme':s,'check':1,'repair':4} for s in SCHEMES[1:]])
    for r in timing:assert r['cycles']>p0['cycles'] and r['seu']['response_hold_cycles']>0 and r['seu']['cancelled_responses']>0
    # Time of a real checked read at Lcheck=1: inject before that CPU tick and
    # hold the response for repair. A second arrival during the busy interval
    # is tested without stopping the independent event clock.
    with (output/'latency_clean_P_ECC/prediction_reads.csv').open() as f:latreads=list(csv.DictReader(f))
    late_tick=int(latreads[90]['tick'])
    timed=execute([{'label':'latency_repair_ECC','scheme':'P_ECC','check':1,'repair':4,'events':[(late_tick,[fold])]},
                   {'label':'event_during_repair_ECC','scheme':'P_ECC','check':1,'repair':4,'events':[(late_tick,[fold]),(late_tick+500,[fold+1])]},
                   {'label':'repeat_three_ED','scheme':'P_ED','events':[(tick,[raw]),(tick+500000,[fold]),(tick+1000000,[raw+1])]},
                   {'label':'signed_counter_bit','scheme':'P0','events':[(tick,[10242])]}])
    assert timed[0]['seu']['corrected']>0 and timed[1]['seu']['applied_events']==2 and timed[1]['seu']['corrected']>=2
    assert timed[1]['seu']['repair_batches']>=2
    assert timed[2]['seu']['reset_refill']>=2
    backend=execute([{'label':f'backend_repair_probe_{i}','scheme':'P_ECC','check':1,'repair':4,'events':[(late_tick+500*i,[fold])]} for i in [1,2,3,4,5,6]])
    assert any(sum(r['seu']['repairs_by_origin'][2:])>0 for r in backend), 'no real backend-origin repair observed'
    assert all(r['seu']['repair_batches']>=1 and r['seu']['response_hold_cycles']>0 for r in backend)
    report('PASS_REAL_O3_LOGICAL_INJECTION_SPECULATION_AND_RESPONSE_HOLD_GATE')
    print('PASS E3 bounded real CPU gate; representative faulty performance campaign remains separate',flush=True)
if __name__=='__main__':
    try:main()
    except Exception as error:
        (ROOT/'reports/E3_INTEGRATION_GATE.json').write_text(json.dumps({'status':'FAIL_INVARIANT','error':str(error),'cases':ACTIVE.get('cases',[])},indent=2)+'\n')
        raise
