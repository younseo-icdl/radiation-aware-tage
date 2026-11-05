#!/usr/bin/env python3
from pathlib import Path
import argparse,importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/prepare.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',default='A1');a=p.parse_args();m.budget();name='recovery_'+a.attempt;source=BASE/'tests/recovery_gate.cpp';binary=BASE/'runtime'/name
 plan=BASE/'reports'/(name+'.source.lock.json');m.put(plan,{'new_sources':[m.ref(p) for folder in ['src','tests'] for p in sorted((BASE/folder).glob('*')) if p.is_file()],'tool':m.ref(Path(__file__)),'CPU_new':0})
 flags=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src')]
 build=m.invoke(name+'_build',[m.CC,*flags,'-static-libstdc++','-static-libgcc',source,BASE/'runtime/tage_base.cc','-o',binary]);run=m.invoke(name+'_run',[binary]);data=json.loads(Path(run['stdout']['path']).read_text());m.put(BASE/'reports'/(name+'.json'),{'result':data,'plan':m.ref(plan),'binary':m.ref(binary),'build':build,'run':run,'resources':m.budget()});print(json.dumps(data))
if __name__=='__main__':main()
