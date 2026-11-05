#!/usr/bin/env python3
"""Retest independent throughput with current measured source, never CPU."""
from pathlib import Path
import argparse, importlib.util, json, sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);a=p.parse_args();m.budget()
    name='throughput_'+a.attempt;test=BASE/'tests/throughput_gate.cpp';binary=BASE/'runtime'/name
    flags=['-O2','-g0','-std=c++17','-I'+str(BASE/'measured_src'),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src')]
    dep=m.invoke(name+'_dependencies',[m.CC,*flags,'-MM',test])
    files=Path(dep['stdout']['path']).read_text().replace('\\\n',' ').split(':',1)[1].split()
    plan=BASE/'reports'/(name+'.lock.json')
    m.put(plan,{'source':[m.ref(p) for p in files], 'upstream_standalone_TAGE':m.ref(BASE/'runtime/tage_base.cc'),'tool':m.ref(Path(__file__)),'CPU_new':0})
    build=m.invoke(name+'_build',[m.CC,*flags,'-static-libstdc++','-static-libgcc',test,BASE/'runtime/tage_base.cc','-o',binary])
    run=m.invoke(name+'_run',[binary]);result=json.loads(Path(run['stdout']['path']).read_text())
    m.put(BASE/'reports'/(name+'.json'),{'result':result,'plan':m.ref(plan),'binary':m.ref(binary),'build':build,'run':run,'resources':m.budget()})
    print(json.dumps(result))
if __name__=='__main__':main()
