#!/usr/bin/env python3
"""Compile one NEW clock-adapter object against immutable actual gem5 headers.
No linking/SimObject registration/CPU simulation is performed or claimed.
"""
from pathlib import Path
import argparse,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--attempt',default='A2');a=ap.parse_args();m.budget();report=m.V11/'overwrite_v11/reports/CPU_BUILD.lock.json';old=json.loads(report.read_text());assert old['status']=='PASS_NEW_INCREMENTAL_GEM5_BINARY_BUILT_NOT_CPU_REGRESSION_TESTED'
 for x in json.loads((BASE/'reports/PRESERVATION.lock.json').read_text())['preserved']:assert m.sha(x['path'])==x['sha256']
 source=BASE/'gem5_overlay/src/cpu/pred/finite_source_v13_clock.cc';header=source.with_suffix('.hh');obj=BASE/'runtime'/('finite_source_v13_clock_'+a.attempt+'.o');dep=BASE/'runtime'/('clock_'+a.attempt+'.d')
 flags=['-I'+str(BASE/'gem5_overlay/src'),*old['flags']]
 plan=BASE/'reports'/('CLOCK_COMPILE_PLAN_'+a.attempt+'.lock.json');m.put(plan,{'status':'FROZEN_BEFORE_COMPILE','source':m.ref(source),'header':m.ref(header),'compile_flags_reference':m.ref(report),'new_source_files':[m.ref(p) for p in (BASE/'src').glob('*.hpp')],'new_CPU':0,'resources':m.budget()})
 r=m.invoke('clock_compile_'+a.attempt,[m.CC,*flags,'-MMD','-MF',dep,'-c',source,'-o',obj]);text=dep.read_text().replace('\\\n',' ')
 includes=[m.ref(p) for p in text.split(':',1)[1].split()]
 m.put(BASE/'reports'/('CLOCK_COMPILE_'+a.attempt+'.json'),{'status':'PASS_GEM5_CLOCK_ADAPTER_COMPILED_NOT_INSTANTIATED_OR_O3_VALIDATED','object':m.ref(obj),'plan':m.ref(plan),'execution':r,'actual_dependencies':includes,'flags':flags,'CPU_new':0,'resources':m.budget()});print('PASS_GEM5_CLOCK_ADAPTER_COMPILED_NOT_INSTANTIATED_OR_O3_VALIDATED')
if __name__=='__main__':main()
