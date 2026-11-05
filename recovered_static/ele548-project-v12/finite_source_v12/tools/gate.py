#!/usr/bin/env python3
"""Bounded source component build/test; launches no gem5/EDA."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
V11=Path('/home/youns/workspace/ele548-project-v11');V10=Path('/home/youns/workspace/ele548-project-v10');V9=Path('/home/youns/workspace/ele548-project-v9')
CC=Path('/opt/rh/gcc-toolset-11/root/usr/bin/g++')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def seconds(p):
 values=p.read_text().strip().splitlines()[-1].split();return float(values[0])+float(values[1])
def budget():
 def kib(p):return int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0])
 sizes={str(p):kib(p) for p in [V9,V10,V11,ROOT]}
 assert sizes[str(ROOT)]<64*1024 and sizes[str(ROOT)]+sizes[str(V11)]<192*1024
 total=sum(sizes.values())/1048576;assert total<8 and total+20.54370880126953<34 and shutil.disk_usage(ROOT).free>=10*1024**3
 used=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time'))
 old=sum(seconds(p) for p in (V11/'overwrite_v11/runtime').rglob('*.time'))
 assert used<900 and (old+used)/3600<2.5 and 11.171808333333335+(old+used)/3600<16 and 76.57026388888889+(old+used)/3600<108
 return {'new_recorded_coreh':used/3600,'v11_v12_recorded_coreh':(old+used)/3600,'all4_worktrees_GiB':total,'CPU_new':0,'CPU_cap':3487}
def invoke(label,command):
 d=BASE/'runtime'/label;d.mkdir(exist_ok=False)
 with (d/'stdout').open('x') as out,(d/'stderr').open('x') as err:
  p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3','120',*[str(v) for v in command]],stdout=out,stderr=err,cwd=ROOT,timeout=135)
 r={'command':[str(v) for v in command],'exit_code':p.returncode,'stdout':ref(d/'stdout'),'stderr':ref(d/'stderr'),'time':ref(d/'job.time')};put(d/'EXECUTION.json',r)
 assert p.returncode==0,('FAILED_STAGE_RETAINED',label);return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--attempt',choices=['A1','A2','A3','B1','B2','B3','C1','C2','C3','D1','D2','D3'],default='D1');a=ap.parse_args();budget()
 (BASE/'runtime').mkdir(exist_ok=True);(BASE/'reports').mkdir(exist_ok=True)
 gate=V11/'overwrite_v11/reports/FAULT12_FINAL_GATES.json';old=json.loads(gate.read_text());assert old['actual_global_CPU']==3487 and old['valid_ABCD_pairs']==12
 preservation=json.loads((V11/'overwrite_v11/reports/PRESERVATION.json').read_text())
 for item in preservation['preserved']:assert sha(item['path'])==item['sha256']
 source=V9/'third_party/gem5-native-v9r2/src/cpu/pred/tage_base.cc';generated=BASE/'runtime/tage_base.cc'
 text=source.read_text();start=text.index('TAGEBase::TAGEBaseStats::TAGEBaseStats(');end=text.index('\n}',text.index('{',start))+2
 replacement='TAGEBase::TAGEBaseStats::TAGEBaseStats(statistics::Group *parent, unsigned nHistoryTables) : statistics::Group(parent) {longestMatchProvider.init(nHistoryTables + 1);altMatchProvider.init(nHistoryTables + 1);}'
 value=text[:start]+replacement+text[end:]
 if generated.exists():assert generated.read_text()==value
 else:generated.write_text(value)
 sources=[p for directory in ['src','tests','tools'] for p in sorted((BASE/directory).glob('*')) if p.is_file()]
 lock=BASE/'reports'/('SOURCE_'+a.attempt+'.lock.json');put(lock,{'status':'FROZEN_BEFORE_COMPONENT_GATE','at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_sources':[ref(p) for p in sources],'prior_gate':ref(gate),'pinned_TAGE_source':ref(source),'generated':ref(generated),'no_CPU_or_EDA':True,'resources':budget()})
 common=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(V9/'src'),'-I'+str(V9/'src/standalone'),'-I'+str(V9/'third_party/gem5-native-v9r2/src')]
 dep=invoke('dependencies_'+a.attempt,[CC,*common,'-MM',BASE/'tests/service_gate.cpp']);raw=(BASE/'runtime'/('dependencies_'+a.attempt)/'stdout').read_text().replace('\\\n',' ')
 put(BASE/'reports'/('DEPENDENCIES_'+a.attempt+'.json'),{'files':[ref(Path(x)) for x in raw.split(':',1)[1].split()],'execution':dep})
 binary=BASE/'runtime'/('service_gate_'+a.attempt)
 build=invoke('build_'+a.attempt,[CC,*common,'-static-libstdc++','-static-libgcc',BASE/'tests/service_gate.cpp',generated,'-o',binary])
 manifest=BASE/'runtime'/('manifest_'+a.attempt+'.json');run=invoke('run_'+a.attempt,[binary,manifest]);result=json.loads((BASE/'runtime'/('run_'+a.attempt)/'stdout').read_text())
 assert result['status']=='PASS_FINITE_SOURCE_COMPONENT_NOT_CPU_QUALIFICATION'
 report='SERVICE_GATE.json' if a.attempt=='A1' else 'SERVICE_GATE_'+a.attempt+'.json'
 put(BASE/'reports'/report,{'status':result['status'],'result':result,'source_lock':ref(lock),'binary':ref(binary),'build':build,'run':run,'manifest':ref(manifest),'resources':budget(),'new_CPU':0,'new_EDA':0});print(json.dumps(result))
if __name__=='__main__':main()
