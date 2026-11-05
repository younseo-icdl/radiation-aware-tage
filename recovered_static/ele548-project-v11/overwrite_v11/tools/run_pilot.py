#!/usr/bin/env python3
"""Frozen fixed-site development diagnostic; no CPU or radiation-rate claims."""
from pathlib import Path
import argparse,csv,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
spec=importlib.util.spec_from_file_location('v11_bounded_tools',BASE/'tools/prepare_gate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['A1','A2'],default='A1');args=parser.parse_args()
    m.budget();gate=BASE/'reports/CPP_GATE.json';g=json.loads(gate.read_text())
    assert g['status']=='PASS_FULL_PREDICTOR_CPP_FUNCTIONAL_NOT_CPU_TIMING'
    source=json.loads(Path(g['source_lock']['path']).read_text())
    for item in source['new_sources']:assert m.sha(item['path'])==item['sha256']
    old=Path('/home/youns/workspace/ele548-project')
    inventory=old/'reports/E1_WORKLOAD_WINDOWS.json';data=json.loads(inventory.read_text())
    names=['SHORT-INT-1','LONG-SPEC2K6-00'];inputs=[]
    for name in names:
        item=next(w for w in data['workloads'] if w['workload']==name)['split_files']['design']
        path=old/item['path'];assert m.sha(path)==item['sha256'];inputs.append(path)
    plan={'status':'FROZEN_BEFORE_CPP_PILOT_BUILD_AND_EXECUTION','gate':m.ref(gate),'input_inventory':m.ref(inventory),
          'inputs':[m.ref(p) for p in inputs],'names':names,'raw_ages':[0,16,64,129],'fold_bit_positions':[0,49,99,199],
          'event_offsets_controls':[0,127,511,999],'warmup_controls':20000,'post_event_controls':10000,
          'event_owners':16,'planned_rows':112,'expected_structurally_removed_rows':8,
          'methods':['P0','P_ED_FREQUENT','P_ED_PERIODIC64','P_ECC','P_TMR','DIRECT','OVERWRITE'],
          'event_rng':'NONE_FIXED_PREDECLARED_ROLE_DIAGNOSTIC_NOT_RANDOM_SAMPLE','predictor_rng_seed':548,
          'rate':'NOT_A_RATE_CAMPAIGN','CPU_trials':0,'selection':'Previously exposed E1 design traces; not holdout',
          'pilot_source':m.ref(BASE/'src/pilot.cpp'),'tool':m.ref(Path(__file__))}
    plan_path=BASE/'reports'/('PILOT_PLAN.lock.json' if args.attempt=='A1' else 'PILOT_PLAN_A2.lock.json')
    if args.attempt=='A2':
        original=json.loads((BASE/'reports/PILOT_PLAN.lock.json').read_text())
        for key in ['names','raw_ages','fold_bit_positions','event_offsets_controls','warmup_controls','post_event_controls','event_owners','planned_rows','methods','event_rng','predictor_rng_seed']:
            assert plan[key]==original[key],('FIX_CHANGED_EXPERIMENT',key)
        plan['prior_failed_build_plan']=m.ref(BASE/'reports/PILOT_PLAN.lock.json')
        plan['fix']='Missing iostream include only; fixed-site diagnostic cases unchanged before any fault replay'
    m.write(plan_path,plan)
    common=['-O2','-std=c++17','-I'+str(BASE/'src'),'-I'+str(m.OLD/'src'),'-I'+str(m.OLD/'src/standalone'),'-I'+str(m.OLD/'third_party/gem5-native-v9r2/src')]
    deps=m.invoke('pilot_dependencies_'+args.attempt,[m.COMPILER,*common,'-MM',BASE/'src/pilot.cpp'])
    text=(BASE/('runtime/pilot_dependencies_'+args.attempt)/'stdout').read_text().replace('\\\n',' ')
    m.write(BASE/('reports/PILOT_DEPENDENCIES_'+args.attempt+'.json'),{'files':[m.ref(Path(t)) for t in text.split(':',1)[1].split()],'command':deps})
    executable=BASE/'runtime'/('pilot' if args.attempt=='A1' else 'pilot_A2')
    build=m.invoke('pilot_build_'+args.attempt,[m.COMPILER,*common,'-static-libstdc++','-static-libgcc',BASE/'src/pilot.cpp',BASE/'runtime/tage_base.cc','-o',executable])
    output=BASE/'runtime/pilot.csv';assert not output.exists()
    execute=m.invoke('pilot_run_'+args.attempt,[executable,*inputs,output])
    result=json.loads((BASE/('runtime/pilot_run_'+args.attempt)/'stdout').read_text())
    assert result['status']=='PASS_REAL_TRACE_DEVELOPMENT_CPP_PILOT_NOT_CPU_PERFORMANCE'
    rows=list(csv.DictReader(output.open()));assert len(rows)==112
    assert all(None not in r and all(v is not None for v in r.values()) for r in rows),'CSV_SCHEMA_MISMATCH'
    removed=[r for r in rows if r['status']=='STRUCTURALLY_REMOVED_NOT_EXPOSED']
    actual=[r for r in rows if r['status']=='PASS_REAL_TRACE_CPP_NOT_CPU_CYCLES']
    assert len(actual)==104 and len(removed)==8
    for r in removed:assert r['mode']=='DIRECT' and r['field']=='FOLD' and all(r[k]=='' for k in ['fault_misses','delta_misses','delta_MPKI'])
    for r in actual:
        assert int(r['delta_misses'])==int(r['fault_misses'])-int(r['clean_misses'])
        expected=1000*int(r['delta_misses'])/int(r['instruction_records'])
        assert abs(float(r['delta_MPKI'])-expected)<1e-12
    m.write(BASE/'reports/PILOT_RESULT.json',{'status':result['status'],'actual':result,'plan':m.ref(plan_path),'rows':m.ref(output),'build':build,'execution':execute,'resources':m.budget(),'cpu_simulations_dispatched':0})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
