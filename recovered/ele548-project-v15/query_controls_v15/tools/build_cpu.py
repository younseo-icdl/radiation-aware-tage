#!/usr/bin/env python3
"""Isolated four-object gem5 producer. Does not execute CPU simulation."""
from pathlib import Path
import argparse,concurrent.futures,json,sys
sys.dont_write_bytecode=True
import prepare as m
BASE=m.BASE
def load(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--attempt',required=True);a=p.parse_args()
    m.budget(extra_MiB=54,extra_seconds=200);m.preserve()
    query=BASE/'reports/query_gate_A1.json';early=BASE/'reports/early_gate_A2.json'
    assert load(query)['result']['normal_controls']==23052 and load(early)['result']['metadata_SBU']==848
    old=load(m.V14/'reports/MEASURED_BUILD_PLAN_B1.lock.json')
    for r in old['old_link_objects']+old['old_static_libraries']:assert m.sha(r['path'])==r['sha256']
    overlay=BASE/'gem5_overlay/src';gem=m.V9/'third_party/gem5-native-v9r2'
    for name in ['cpu/o3/bac.hh','cpu/pred/bpred_unit.hh']:
        text=(overlay/name).read_text().replace('namespace bp::v15 { struct RecoveryBridge; }\n\n','').replace('\n    friend struct ::bp::v15::RecoveryBridge;','')
        assert text==(gem/'src'/name).read_text(),'BPU_BAC_LAYOUT_CHANGED'
    flags=['-I'+str(overlay),*old['flags']]
    output=BASE/'runtime'/('gem5_build_'+a.attempt);output.mkdir(exist_ok=False)
    source_lock=m.freeze('CPU_'+a.attempt)
    plan=BASE/'reports'/('CPU_BUILD_PLAN_'+a.attempt+'.lock.json')
    m.put(plan,{'status':'FROZEN_BEFORE_NEW_BUILD_NOT_CPU_TESTED','source_lock':source_lock,'query_gate':m.ref(query),'early_gate':m.ref(early),'old_build_plan':m.ref(m.V14/'reports/MEASURED_BUILD_PLAN_B1.lock.json'),'consumers':old['consumers'],'flags':flags,'old_link_objects':old['old_link_objects'],'old_static_libraries':old['old_static_libraries'],'CPU_new':0,'resources':m.budget()})
    def compile_one(pair):
        i,item=pair;source=Path(item['source']);relative=source.relative_to(gem/'src') if source.is_relative_to(gem/'src') else None
        if relative is not None and (overlay/relative).exists():source=overlay/relative
        obj=output/(str(i)+'_'+Path(item['object']).name);dep=output/(str(i)+'.d')
        run=m.invoke('cpu_compile_'+str(i)+'_'+a.attempt,[m.CC,*flags,'-MMD','-MF',dep,'-c',source,'-o',obj])
        return {'replace':item['object'],'object':m.ref(obj),'dependency':m.ref(dep),'execution':run}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:objects=list(pool.map(compile_one,enumerate(old['consumers'])))
    replacement={r['replace']:Path(r['object']['path']) for r in objects}
    assert len(replacement)==4
    inputs=[replacement.get(r['path'],Path(r['path'])) for r in old['old_link_objects']]
    assert len(inputs)==1516
    binary=output/'gem5.query_early.opt'
    link=m.invoke('cpu_link_'+a.attempt,[m.CC,'-o',binary,'-rdynamic','-O3','-Wl,--as-needed','-Wl,--no-keep-memory',*inputs,'-Wl,--start-group',*[r['path'] for r in old['old_static_libraries']],'-Wl,--end-group','-L/opt/miniconda3/lib','-lpython3.13','-lpthread','-lz','-lrt','-ldl'])
    info=m.invoke('cpu_buildinfo_'+a.attempt,['/usr/bin/env','LD_LIBRARY_PATH=/opt/miniconda3/lib',binary,'--build-info'])
    assert 'gem5 version 25.1.0.1' in Path(info['stdout']['path']).read_text()
    deps={}
    for p in output.glob('*.d'):
        for name in p.read_text().replace('\\\n',' ').split(':',1)[1].split():deps[name]=m.ref(name)
    for r in old['old_link_objects']+old['old_static_libraries']:assert m.sha(r['path'])==r['sha256']
    m.preserve()
    m.put(BASE/'reports'/('CPU_BUILD_'+a.attempt+'.json'),{'status':'PASS_NEW_BINARY_BUILD_NOT_CPU_EXECUTED','binary':m.ref(binary),'plan':m.ref(plan),'objects':objects,'old_objects_reused':1512,'actual_dependencies':list(deps.values()),'link':link,'version':info,'CPU_new':0,'resources':m.budget()})
    print('PASS_NEW_BINARY_BUILD_NOT_CPU_EXECUTED',m.ref(binary))
if __name__=='__main__':main()
