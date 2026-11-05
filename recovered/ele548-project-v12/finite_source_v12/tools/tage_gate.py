#!/usr/bin/env python3
"""Native TAGE functional bridge gate, no gem5/O3 or CPU throughput claim."""
from pathlib import Path
import argparse,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded_gate',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',choices=['A1','A2','A3','B1','B2','B3','C1','C2','C3','D1','D2','D3'],default='D1');p.add_argument('--service-attempt',choices=['A3','B1','B2','B3','C1','C2','C3','D1','D2','D3'],default='D1');a=p.parse_args();m.budget()
 gate=BASE/'reports'/('SERVICE_GATE_'+a.service_attempt+'.json');d=json.loads(gate.read_text());assert d['status']=='PASS_FINITE_SOURCE_COMPONENT_NOT_CPU_QUALIFICATION'
 source=json.loads(Path(d['source_lock']['path']).read_text());assert any(i['path'].endswith('/src/service.hpp') and m.sha(i['path'])==i['sha256'] for i in source['new_sources'])
 traces=[Path('/home/youns/workspace/ele548-project/workloads/derived/e1')/(n+'.design.bin') for n in ['SHORT-INT-1','LONG-SPEC2K6-00']]
 plan=BASE/'reports'/('TAGE_PLAN_'+a.attempt+'.lock.json');m.put(plan,{'status':'FROZEN_BEFORE_FUNCTIONAL_NATIVE_TAGE_GATE','service_gate':m.ref(gate),'traces':[m.ref(x) for x in traces],'source_files':[m.ref(x) for x in [BASE/'src/service.hpp',BASE/'tests/tage_harness.hpp',BASE/'tests/tage_gate.cpp',Path(__file__)]],
 'counts':{'synthetic':60000,'real_controls':36000,'spec_controls':48000,'explicit_undos':46500},'scope':'Functional equivalence, host observation helpers not a free hardware port; no CPU timing claim','new_CPU':0})
 common=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src')]
 dep=m.invoke('tage_dependencies_'+a.attempt,[m.CC,*common,'-MM',BASE/'tests/tage_gate.cpp']);text=(BASE/'runtime'/('tage_dependencies_'+a.attempt)/'stdout').read_text().replace('\\\n',' ')
 m.put(BASE/'reports'/('TAGE_DEPENDENCIES_'+a.attempt+'.json'),{'files':[m.ref(Path(x)) for x in text.split(':',1)[1].split()],'execution':dep})
 binary=BASE/'runtime'/('tage_gate_'+a.attempt)
 build=m.invoke('tage_build_'+a.attempt,[m.CC,*common,'-static-libstdc++','-static-libgcc',BASE/'tests/tage_gate.cpp',BASE/'runtime/tage_base.cc','-o',binary])
 run=m.invoke('tage_run_'+a.attempt,[binary,*traces]);result=json.loads((BASE/'runtime'/('tage_run_'+a.attempt)/'stdout').read_text());assert result['status']=='PASS_PINNED_TAGE_FINITE_SOURCE_FUNCTIONAL_HARNESS_NOT_GEM5_TIMING'
 m.put(BASE/'reports'/('TAGE_GATE_'+a.attempt+'.json'),{'status':result['status'],'result':result,'plan':m.ref(plan),'build':build,'run':run,'binary':m.ref(binary),'resources':m.budget()});print(json.dumps(result))
if __name__=='__main__':main()
