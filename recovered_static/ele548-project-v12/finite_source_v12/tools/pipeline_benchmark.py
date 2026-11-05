#!/usr/bin/env python3
"""L1/L2 end-to-end ready query controls and single/multiple admission."""
from pathlib import Path
import csv,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 m.budget();gate=BASE/'reports/SERVICE_GATE_D1.json';g=json.loads(gate.read_text());lock=json.loads(Path(g['source_lock']['path']).read_text())
 item=next(x for x in lock['new_sources'] if x['path'].endswith('/src/service.hpp'));assert m.sha(item['path'])==item['sha256']
 plan=BASE/'reports/PIPELINE_BENCH_PLAN.lock.json';m.put(plan,{'status':'FROZEN_BEFORE_66_COMPONENT_CASES','source_gate':m.ref(gate),'sources':[m.ref(BASE/'src/service.hpp'),m.ref(BASE/'tests/pipeline_bench.cpp'),m.ref(Path(__file__))],
 'cases':66,'N':128,'matrix':'60 unique active resource/pattern cells +6 single-pending admission controls; direct unused update_L aliases not rerun',
 'ready_query_latency':'Actual accept to response L1/L2, II1; operand unavailable/full/repair waits separately counted',
 'scope':'C++ fold/source component; no CPU next-PC/provider/table or fault campaign','CPU_trials':0})
 common=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src')]
 binary=BASE/'runtime/pipeline_bench';build=m.invoke('pipeline_bench_build',[m.CC,*common,'-static-libstdc++','-static-libgcc',BASE/'tests/pipeline_bench.cpp',BASE/'runtime/tage_base.cc','-o',binary]);output=BASE/'runtime/pipeline_bench.csv'
 run=m.invoke('pipeline_bench_run',[binary,output]);result=json.loads((BASE/'runtime/pipeline_bench_run/stdout').read_text());rows=list(csv.DictReader(output.open()));assert len(rows)==result['cases']==66
 for r in rows:
  assert int(r['accepted'])==int(r['completed'])==int(r['logical_operations'])
  if r['pattern'] in ['READ_ONLY_INDEPENDENT','READ_ONLY_SINGLE_PENDING']:assert r['minimum_query_latency']==r['maximum_query_latency']==r['lookup_L']
 m.put(BASE/'reports/PIPELINE_BENCH.json',{'status':'PASS_66_END_TO_END_LATENCY_AND_PORT_COMPONENT_CASES_NOT_CPU_PERFORMANCE','result':result,'plan':m.ref(plan),'rows':m.ref(output),'build':build,'run':run,'resources':m.budget()});print(json.dumps(result))
if __name__=='__main__':main()
