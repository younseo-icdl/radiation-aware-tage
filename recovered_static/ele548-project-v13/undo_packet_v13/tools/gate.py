#!/usr/bin/env python3
"""Exclusive bounded C++ gates; no gem5 CPU simulation or EDA."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
V9=Path('/home/youns/workspace/ele548-project-v9');V10=Path('/home/youns/workspace/ele548-project-v10');V11=Path('/home/youns/workspace/ele548-project-v11');V12=Path('/home/youns/workspace/ele548-project-v12')
CC=Path('/opt/rh/gcc-toolset-11/root/usr/bin/g++')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def seconds(p):
 values=p.read_text().strip().splitlines()[-1].split();return float(values[0])+float(values[1])
def budget():
 sizes={str(p):int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0]) for p in [V9,V10,V11,V12,ROOT]}
 assert sizes[str(ROOT)]+sizes[str(V12)]<64*1024
 assert sizes[str(ROOT)]+sizes[str(V12)]+sizes[str(V11)]<192*1024
 total=sum(sizes.values())/1048576;assert total<8 and total+20.54370880126953<34 and shutil.disk_usage(ROOT).free>=10*1024**3
 new=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time'));prior=sum(seconds(p) for p in (V12/'finite_source_v12/runtime').rglob('*.time'))
 old=sum(seconds(p) for p in (V11/'overwrite_v11/runtime').rglob('*.time'))
 assert new+prior<900 and (old+prior+new)/3600<2.5 and 11.171808333333335+(old+prior+new)/3600<16 and 76.57026388888889+(old+prior+new)/3600<108
 return {'new_recorded_coreh':new/3600,'v12_v13_preparation_coreh':(new+prior)/3600,'v11_v12_v13_coreh':(old+prior+new)/3600,'all5_worktrees_GiB':total,'preparation_MiB':(sizes[str(ROOT)]+sizes[str(V12)])/1024,'CPU_new':0,'CPU_global_used':3487,'CPU_cap':3487}
def invoke(label,command):
 d=BASE/'runtime'/label;d.mkdir(exist_ok=False)
 with (d/'stdout').open('x') as out,(d/'stderr').open('x') as err:
  p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3','120',*map(str,command)],stdout=out,stderr=err,cwd=ROOT,timeout=135)
 r={'command':list(map(str,command)),'exit_code':p.returncode,'stdout':ref(d/'stdout'),'stderr':ref(d/'stderr'),'time':ref(d/'job.time')};put(d/'EXECUTION.json',r)
 assert p.returncode==0,('FAILED_STAGE_RETAINED',label);return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('stage',choices=['service','bulk','tage','pipeline','bridge','lookup','manifest','serial']);ap.add_argument('--attempt',default='A1');a=ap.parse_args();resources=budget()
 for x in json.loads((BASE/'reports/PRESERVATION.lock.json').read_text())['preserved']:assert sha(x['path'])==x['sha256']
 source=V9/'third_party/gem5-native-v9r2/src/cpu/pred/tage_base.cc';generated=BASE/'runtime/tage_base.cc'
 text=source.read_text();start=text.index('TAGEBase::TAGEBaseStats::TAGEBaseStats(');end=text.index('\n}',text.index('{',start))+2
 value=text[:start]+'TAGEBase::TAGEBaseStats::TAGEBaseStats(statistics::Group *parent, unsigned nHistoryTables) : statistics::Group(parent) {longestMatchProvider.init(nHistoryTables + 1);altMatchProvider.init(nHistoryTables + 1);}'+text[end:]
 if generated.exists():assert generated.read_text()==value
 else:generated.write_text(value)
 sources=[p for folder in ['src','tests','tools'] for p in sorted((BASE/folder).rglob('*')) if p.is_file()]
 label=a.stage+'_'+a.attempt;lock=BASE/'reports'/(label+'.source.lock.json');put(lock,{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_sources':[ref(p) for p in sources],'pinned_TAGE_source':ref(source),'generated':ref(generated),'new_CPU':0,'resources':resources})
 common=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(V9/'src'),'-I'+str(V9/'src/standalone'),'-I'+str(V9/'third_party/gem5-native-v9r2/src')]
 test=BASE/'tests'/({'service':'service_gate.cpp','bulk':'bulk_gate.cpp','tage':'tage_gate.cpp','pipeline':'pipeline_bench.cpp','bridge':'bridge_gate.cpp','lookup':'lookup_gate.cpp','manifest':'manifest_gate.cpp','serial':'serial_bench.cpp'}[a.stage])
 dep=invoke(label+'_dependencies',[CC,*common,'-MM',test]);raw=Path(dep['stdout']['path']).read_text().replace('\\\n',' ')
 put(BASE/'reports'/(label+'.dependencies.json'),{'files':[ref(Path(x)) for x in raw.split(':',1)[1].split()],'execution':dep})
 binary=BASE/'runtime'/label
 build=invoke(label+'_build',[CC,*common,'-static-libstdc++','-static-libgcc',test,generated,'-o',binary])
 args=[]
 if a.stage in ['service','manifest']:args=[BASE/'runtime'/(label+'.manifest.json')]
 if a.stage=='pipeline':args=[BASE/'runtime'/(label+'.csv')]
 if a.stage=='tage':args=[Path('/home/youns/workspace/ele548-project/workloads/derived/e1')/(n+'.design.bin') for n in ['SHORT-INT-1','LONG-SPEC2K6-00']]
 run=invoke(label+'_run',[binary,*args]);data=Path(run['stdout']['path']).read_text();parsed=json.loads(data)
 put(BASE/'reports'/(label+'.json'),{'result':parsed,'source_lock':ref(lock),'binary':ref(binary),'inputs':[ref(p) for p in args if p.is_file()],'build':build,'run':run,'resources':budget(),'CPU_new':0,'EDA_new':0});print(json.dumps({'stage':label,'result':parsed,'resources':budget()}))
if __name__=='__main__':main()
