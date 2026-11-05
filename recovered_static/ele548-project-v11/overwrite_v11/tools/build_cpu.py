#!/usr/bin/env python3
"""Bounded new incremental binary; never writes any old link input/source."""
from pathlib import Path
import argparse,importlib.util,json,os,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
spec=importlib.util.spec_from_file_location('v11_bounded_tools',BASE/'tools/prepare_gate.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['A1','A2','A3'],default='A1');parser.add_argument('--resume-built',action='store_true');args=parser.parse_args()
    m.budget();lock_path=BASE/'reports'/('CPU_OVERLAY_A3.lock.json' if args.attempt=='A3' else 'CPU_OVERLAY.lock.json');lock=json.loads(lock_path.read_text())
    assert lock['status']=='PREPARED_OVERWRITE_CPU_OVERLAY_NOT_BUILT_OR_EXECUTED'
    for key in ['old_header','old_source','old_config','old_binary','scons_database']:
        assert m.sha(lock[key]['path'])==lock[key]['sha256']
    for item in lock['new_files']+lock['mixin_sources']+lock['immutable_link_objects']+lock['static_libraries']:
        assert m.sha(item['path'])==item['sha256'],item['path']
    output=BASE/('runtime/cpu_build_'+args.attempt)
    if args.resume_built:assert args.attempt=='A3' and output.is_dir()
    else:output.mkdir(exist_ok=False)
    old=m.OLD/'third_party/gem5-native-v9r2';oldbuild=old/'build/X86_PIPELINE'
    overlay=BASE/'gem5_overlay/src'
    flags=['-O3','-g0','-std=c++17','-fno-strict-aliasing','-DTRACING_ON=1','-fPIC',
           '-I'+str(overlay),'-I'+str(oldbuild),'-I'+str(old/'src'),'-I'+str(old),
           '-I'+str(old/'src/cpu/pred'),'-I'+str(old/'ext/pybind11/include'),'-I/opt/miniconda3/include/python3.13']
    # Include roots from the original cached, verified header dependency set.
    # The first attempt's missing magic_enum include is retained as a failure.
    external=set()
    for item in lock['abi_consumers']:
        for name in item['implicit']:
            p=Path(name)
            if p.is_relative_to(old/'ext'):
                for parent in p.parents:
                    if parent==old:break
                    external.add(parent)
    flags.extend('-I'+str(p) for p in sorted(external,key=lambda p:(-len(p.parts),str(p))))
    records=[];replacements={}
    for i,item in enumerate(lock['abi_consumers']):
        source=Path(item['source'])
        if source.name=='research_native_v9r2_tage.cc':source=overlay/'cpu/pred'/source.name
        target=output/(str(i)+'_'+Path(item['object']).name)
        dep=output/(str(i)+'.d')
        command=[m.COMPILER,*flags,'-MMD','-MF',dep,'-c',source,'-o',target]
        if args.resume_built:
            result=json.loads((BASE/('runtime/cpu_compile_'+str(i)+'_'+args.attempt)/'EXECUTION.json').read_text())
            assert result['exit_code']==0 and result['command']==list(map(str,command)) and target.is_file()
        else:result=m.invoke('cpu_compile_'+str(i)+'_'+args.attempt,command)
        records.append(result);replacements[item['object']]=target
    # Command files contain arguments, never shell-interpolated commands.
    # New binary only; all other object/library paths are immutable inputs.
    objects=[replacements.get(item['path'],Path(item['path'])) for item in lock['immutable_link_objects']]
    libraries=[Path(item['path']) for item in lock['static_libraries']]
    binary=output/'gem5.overwrite.opt'
    link=[m.COMPILER,'-o',binary,'-rdynamic','-O3','-Wl,--as-needed','-Wl,--no-keep-memory',
          *objects,'-Wl,--start-group',*libraries,'-Wl,--end-group',
          '-L/opt/miniconda3/lib','-lpython3.13','-lpthread','-lz','-lrt','-ldl']
    if args.resume_built:
        result=json.loads((BASE/('runtime/cpu_link_'+args.attempt)/'EXECUTION.json').read_text())
        assert result['exit_code']==0 and result['command']==list(map(str,link)) and binary.is_file()
    else:result=m.invoke('cpu_link_'+args.attempt,link)
    records.append(result)
    # Library lookup is local to this invocation; never edits shell startup or
    # the original binary's RPATH. --version does not simulate a CPU trial.
    library='/opt/miniconda3/lib'
    if args.resume_built:
        version=json.loads((BASE/'runtime/cpu_buildinfo_A1/EXECUTION.json').read_text())
        assert version['exit_code']==0 and version['command']==list(map(str,['/usr/bin/env','LD_LIBRARY_PATH='+library,binary,'--build-info']))
        info=BASE/'runtime/cpu_buildinfo_A1/stdout'
    else:
        version=m.invoke('cpu_buildinfo_'+args.attempt,['/usr/bin/env','LD_LIBRARY_PATH='+library,binary,'--build-info'])
        info=BASE/('runtime/cpu_buildinfo_'+args.attempt)/'stdout'
    assert 'gem5 version 25.1.0.1' in info.read_text()
    for item in lock['immutable_link_objects']+lock['static_libraries']+[lock['old_binary']]:
        assert m.sha(item['path'])==item['sha256'],'OLD_INPUT_CHANGED_DURING_BUILD'
    dependencies=[]
    for dep in output.glob('*.d'):
        text=dep.read_text().replace('\\\n',' ')
        for name in text.split(':',1)[1].split():
            p=Path(name);dependencies.append(m.ref(p))
    record={'status':'PASS_NEW_INCREMENTAL_GEM5_BINARY_BUILT_NOT_CPU_REGRESSION_TESTED',
            'overlay_lock':m.ref(lock_path),'tool':m.ref(Path(__file__)),'binary':m.ref(binary),
            'new_objects':[m.ref(p) for p in replacements.values()],
            'old_objects_reused_unchanged':len(objects)-len(replacements),'new_objects_compiled':len(replacements),
            'library_inputs':lock['static_libraries'],'compiler':str(m.COMPILER),'flags':flags,
            'commands':records,'version':version,'dependency_files':[m.ref(p) for p in output.glob('*.d')],
            'actual_included_files':list({i['path']:i for i in dependencies}.values()),
            'resources':m.budget(),'new_cpu_simulations':0,
            'scope':'Manual incremental opt rebuild with opt tracing/asserts retained; not original SCons command or full rebuild. ABI header consumers3 selected from original verified dependency database. No CPU performance claim.'}
    m.write(BASE/'reports/CPU_BUILD.lock.json',record)
    print(json.dumps({'status':record['status'],'binary':record['binary'],'resources':record['resources']},indent=2))
if __name__=='__main__':main()
