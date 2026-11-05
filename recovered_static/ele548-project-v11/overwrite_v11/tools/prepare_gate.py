#!/usr/bin/env python3
"""Bounded standalone build/gate; never changes old producer or launches gem5."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'overwrite_v11'
OLD=Path('/home/youns/workspace/ele548-project-v9')
V10=Path('/home/youns/workspace/ele548-project-v10')
OUT=BASE/'runtime';REPORTS=BASE/'reports'
COMPILER=Path('/opt/rh/gcc-toolset-11/root/usr/bin/g++')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def budget():
    def kib(p):return int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0])
    total=(kib(OLD)+kib(V10)+kib(ROOT))/1048576
    assert kib(ROOT)<192*1024 and total<8 and total+20.54370880126953<34
    assert shutil.disk_usage(ROOT).free>=10*1024**3
    total_seconds=0
    for p in OUT.rglob('*.time'):
        fields=p.read_text().strip().splitlines()[-1].split()
        total_seconds+=float(fields[0])+float(fields[1])
    assert total_seconds<3600 and 11.171808333333335+total_seconds/3600<16
    return {'v11_mib':kib(ROOT)/1024,'v9_v10_v11_gib':total,'recorded_v11_coreh':total_seconds/3600,'cpu_simulations_dispatched':0}
def invoke(label,command):
    folder=OUT/label;folder.mkdir(exist_ok=False)
    command=[str(x) for x in command]
    with (folder/'stdout').open('x') as out,(folder/'stderr').open('x') as err:
        p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(folder/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3','120',*command],stdout=out,stderr=err,cwd=ROOT,timeout=140)
    r={'label':label,'command':command,'exit_code':p.returncode,'stdout':ref(folder/'stdout'),'stderr':ref(folder/'stderr'),'time':ref(folder/'job.time')}
    write(folder/'EXECUTION.json',r)
    assert p.returncode==0,('FAILED_STAGE_RETAINED',label)
    return r
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',choices=['A1','A2'],default='A1');args=parser.parse_args()
    budget();OUT.mkdir(exist_ok=True);REPORTS.mkdir(exist_ok=True)
    previous=json.loads((V10/'native_lifetime_next/reports/FINAL_GATES.json').read_text())
    assert previous['status']=='PASS_ACTUAL108_FINAL_EVIDENCE_NOT_HARDWARE_QUALIFICATION' and previous['actual_global_cpu']==3469
    sources=[OLD/'third_party/gem5-native-v9r2/src/cpu/pred/tage_base.cc',OLD/'third_party/gem5-native-v9r2/src/cpu/pred/tage_base.hh']
    # Validate actual R2 source hashes using its original producer lock.
    lock=json.loads((OLD/'rate_state_v9/r2/runtime/configs/source.lock.json').read_text())
    source=sources[0].read_text();start=source.index('TAGEBase::TAGEBaseStats::TAGEBaseStats(')
    brace=source.index('{',start);end=source.index('\n}',brace)+2
    replacement='''TAGEBase::TAGEBaseStats::TAGEBaseStats(statistics::Group *parent, unsigned nHistoryTables)
    : statistics::Group(parent) {
    longestMatchProvider.init(nHistoryTables + 1);
    altMatchProvider.init(nHistoryTables + 1);
}'''
    generated=OUT/'tage_base.cc'
    generated_text=source[:start]+replacement+source[end:]
    if generated.exists():assert generated.read_text()==generated_text,'GENERATED_UPSTREAM_CHANGED'
    else:
        with generated.open('x') as f:f.write(generated_text)
    bindings=[ref(p) for p in sources]
    for p in sorted((OLD/'src/standalone').rglob('*')):
        if p.is_file():bindings.append(ref(p))
    for directory in ['predictor','rate_state_v9','rate_state_v9_support','protection']:
        for p in sorted((OLD/'src'/directory).glob('*.hpp')):bindings.append(ref(p))
    # The R2 lock may bind selected source families rather than every reused
    # standalone shim; every actual include is also captured by compiler -MMD.
    for item in bindings:
        matches=[]
        for group in ['files','source_files','patched_files']:
            entries=lock.get(group,{})
            if isinstance(entries,dict):
                for key,value in entries.items():
                    if str(item['path']).endswith(key) and isinstance(value,str):matches.append(value)
        if matches:assert item['sha256'] in matches,('R2_SOURCE_CHANGED',item['path'])
    source_lock=REPORTS/('SOURCE.lock.json' if args.attempt=='A1' else 'SOURCE_A2.lock.json')
    write(source_lock,{'status':'PINNED_R2_WITH_LOCAL_FUNCTIONAL_OVERWRITE','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_r2_lock':ref(OLD/'rate_state_v9/r2/runtime/configs/source.lock.json'),'original_sources':bindings,'standalone_generated':ref(generated),'standalone_only_substitution':'statistics constructor','compiler':str(COMPILER),'prior_final_gate':ref(V10/'native_lifetime_next/reports/FINAL_GATES.json'),'new_sources':[ref(p) for p in sorted((BASE/'src').glob('*'))],'tool':ref(Path(__file__))})
    common=['-O2','-std=c++17','-I'+str(BASE/'src'),'-I'+str(OLD/'src'),'-I'+str(OLD/'src/standalone'),'-I'+str(OLD/'third_party/gem5-native-v9r2/src')]
    dependencies=invoke('dependencies_'+args.attempt,[COMPILER,*common,'-MM',BASE/'src/correctness.cpp'])
    text=(OUT/('dependencies_'+args.attempt)/'stdout').read_text().replace('\\\n',' ')
    paths=[Path(token) for token in text.split(':',1)[1].split()]
    write(REPORTS/('COMPILER_DEPENDENCIES_'+args.attempt+'.json'),{'status':'ACTUAL_NON_SYSTEM_INCLUDE_SHA','files':[ref(p) for p in paths],'command':dependencies})
    executable=OUT/('correctness' if args.attempt=='A1' else 'correctness_A2')
    build=invoke('build_'+args.attempt,[COMPILER,*common,'-static-libstdc++','-static-libgcc',BASE/'src/correctness.cpp',generated,'-o',executable])
    gate=invoke('gate_'+args.attempt,[executable])
    result=json.loads((OUT/('gate_'+args.attempt)/'stdout').read_text())
    assert result['status']=='PASS_FULL_PREDICTOR_CPP_FUNCTIONAL_NOT_CPU_TIMING'
    write(REPORTS/'CPP_GATE.json',{'status':result['status'],'result':result,'build':build,'execution':gate,'source_lock':ref(source_lock),'compiler_dependencies':ref(REPORTS/('COMPILER_DEPENDENCIES_'+args.attempt+'.json')),'resources':budget(),'cpu_simulations_dispatched':0})
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
