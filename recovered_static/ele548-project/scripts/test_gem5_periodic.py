#!/usr/bin/env python3
"""Small checksum gate for isolated periodic producer, never overwrite E3 gates."""
import concurrent.futures
import csv
import json
import os
import subprocess
from pathlib import Path
from run_o3_public_baseline import stats
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]

def main():
    binary=ROOT/'third_party/gem5-periodic/build/X86_STAGE0/gem5.opt'
    selection=json.loads((ROOT/'sources/periodic_policy_selection.lock.json').read_text());k=selection['selected_interval']
    old=json.loads((ROOT/'reports/E3_INTEGRATION_GATE.json').read_text());assert sha(ROOT/'third_party/gem5-e3/build/X86_STAGE0/gem5.opt')==old['binary_sha256']
    baseline=next(r for r in old['cases'] if r['case']=='clean_P0')
    with (ROOT/'reports/e3_integration/gate/clean_P0/prediction_reads.csv').open() as f:tick=int(list(csv.DictReader(f))[90]['tick'])
    out=ROOT/'reports/periodic_extension/cpu_gate';out.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    specs=[('legacy_'+s,s,0,0,[]) for s in ['P0','P_ED','P_ECC','P_TMR']]
    specs += [('periodic_clean_k1','P_ED',1,0,[]),('periodic_clean','P_ED',k,0,[]),('periodic_clean_C1','P_ED',k,1,[])]
    specs += [('raw','P_ED',k,1,[(tick,[65054])]),('folded','P_ED',k,1,[(tick,[65170])]),('parity','P_ED',k,1,[(tick,[65370])]),('counter','P_ED',k,1,[(tick,[65434])]),('even','P_ED',k,0,[(tick,[65170,65171])]),('cancel','P_ED',k,0,[(tick,[65170]),(tick,[65170])])]
    def run(spec):
        label,scheme,interval,check,events=spec;d=out/label;d.mkdir(exist_ok=True)
        schedule=d/'schedule.ticks';schedule.write_text(''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
        cmd=[str(binary),'--outdir='+str(d),str(ROOT/'gem5/o3_periodic.py'),'--binary',str(ROOT/'build/checksum_freestanding'),'--scheme',scheme,'--inspection-interval',str(interval),'--check-cycles',str(check),'--repair-cycles','0' if scheme=='P0' else '4','--schedule',str(schedule),'--read-log']
        with (d/'gem5.log').open('w') as f:p=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
        r=dict(case=label,scheme=scheme,interval=interval,check=check,command=cmd,output=str(d.relative_to(ROOT)),exit_code=p.returncode)
        if p.returncode:return dict(r,status='FAIL_EXECUTION')
        assert (d/'program.stdout').read_text().strip()=='checksum=1321703870693' and not (d/'program.stderr').read_bytes()
        assert 'Exit cause: exiting with last active thread context code: 0' in (d/'gem5.log').read_text()
        st=stats(d/'stats.txt');seu=json.loads((d/'seu.json').read_text());m=json.loads((d/'logical_manifest.json').read_text())
        assert m['total_bits']==({'P0':65370,'P_ED':65434,'P_ECC':65532,'P_TMR':66062}[scheme]+(8 if interval else 0))
        assert seu['applied_events']==len(events) and seu['applied_flips']==sum(len(ids) for _,ids in events)
        with (d/'events.csv').open() as f:actual=list(csv.DictReader(f))
        for e,(t,ids) in zip(actual,events):assert int(e['tick'])==t and list(map(int,e['site_ids'].split(';')))==ids and e['XOR_verified']=='1'
        if label.startswith('legacy_') or label in ['periodic_clean_k1','periodic_clean','cancel']:
            assert int(st['system.cpu.numCycles'])==baseline['cycles']
            for key in ['canonical_base_state_hash','predictor_rng_draws','predictor_rng_hash']:assert seu[key]==baseline['seu'][key]
        if label in ['raw','folded','parity']:assert seu['detected']>0 and seu['reset_refill']>0 and seu['refill_updates']>0
        if label in ['even','cancel']:assert seu['detected']==0
        if interval and check:assert seu['response_hold_cycles']>0 and seu['periodic_inspections']>0 and seu['delta_parity_operations']>0
        if interval:assert len([s for s in m['additional_sites'] if s['structure']=='inspection_progress'])==8
        return dict(r,status='PASS',cycles=int(st['system.cpu.numCycles']),seu=seu,stats_sha256=sha(d/'stats.txt'),seu_sha256=sha(d/'seu.json'),manifest_sha256=sha(d/'logical_manifest.json'))
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for r in pool.map(run,specs):rows.append(r);print(json.dumps({'case':r['case'],'status':r['status']}),flush=True)
    assert all(r['status']=='PASS' for r in rows)
    record={'status':'PASS_ISOLATED_PERIODIC_REAL_O3_GATE','cases':rows,'trials':len(rows),'binary_sha256':sha(binary),'source_lock_sha256':sha(ROOT/'sources/gem5_periodic_source.lock.json'),'selection_sha256':sha(ROOT/'sources/periodic_policy_selection.lock.json'),'baseline_binary_preserved_sha256':old['binary_sha256'],'scope_sha256':selection['same_scope_sha256'],'scope':'synthetic checksum functional/timing/provenance gate, not representative performance'}
    (ROOT/'reports/PERIODIC_CPU_GATE.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS 13 checksum cases: frozen-baseline equivalence, cadence, raw/fold/parity/counter/even/cancel, actual holds/refill')
if __name__=='__main__':main()
