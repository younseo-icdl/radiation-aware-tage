#!/usr/bin/env python3
"""Source component port/latency controls, no CPU launch or radiation rate."""
from pathlib import Path
import argparse,csv,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--attempt',choices=['A1','A2','A3'],default='A1');a=ap.parse_args();m.budget()
 gate=BASE/'reports/SERVICE_GATE_C2.json';g=json.loads(gate.read_text());assert g['status']=='PASS_FINITE_SOURCE_COMPONENT_NOT_CPU_QUALIFICATION'
 lock=json.loads(Path(g['source_lock']['path']).read_text());binding=next(x for x in lock['new_sources'] if x['path'].endswith('/src/service.hpp'));assert m.sha(binding['path'])==binding['sha256']
 plan=BASE/'reports'/('BENCH_PLAN_'+a.attempt+'.lock.json');m.put(plan,{'status':'FROZEN_BEFORE_COMPONENT_BENCH','source_gate':m.ref(gate),'sources':[m.ref(BASE/'src/service.hpp'),m.ref(BASE/'tests/service_bench.cpp'),m.ref(Path(__file__))],
 'matrix':'24 new cross-latency cases, REC/OW only; reuse direct cells because update_L is unused' if a.attempt!='A1' else '36 matched-latency cases',
 'N':128,'event_rng':'NONE','same_logical_command_order':True,'source_model_not_CPU':True,'no_new_faults_or_CPU':True})
 common=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src')]
 binary=BASE/'runtime'/('service_bench_'+a.attempt);build=m.invoke('bench_build_'+a.attempt,[m.CC,*common,'-static-libstdc++','-static-libgcc',BASE/'tests/service_bench.cpp',BASE/'runtime/tage_base.cc','-o',binary])
 output=BASE/'runtime'/('service_bench_'+a.attempt+'.csv');run=m.invoke('bench_run_'+a.attempt,[binary,output,*(['--cross'] if a.attempt!='A1' else [])]);result=json.loads((BASE/'runtime'/('bench_run_'+a.attempt)/'stdout').read_text());rows=list(csv.DictReader(output.open()));assert len(rows)==(36 if a.attempt=='A1' else 24)
 for r in rows:assert int(r['accepted'])==int(r['completed'])==int(r['logical_operations']) and int(r['model_cycles'])>0
 m.put(BASE/'reports'/('COMPONENT_BENCH_'+a.attempt+'.json'),{'status':result['status'],'result':result,'plan':m.ref(plan),'rows':m.ref(output),'build':build,'run':run,'resources':m.budget(),
 'interpretation':'Actual component cycles with finite buffers/ports/stage operations; no O3 cycles/IPC or real dependent next-PC stream, no physical clock qualification or energy estimate'})
 print(json.dumps(result))
if __name__=='__main__':main()
