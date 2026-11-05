#!/usr/bin/env python3
"""Bounded shared-source gates. No CPU/EDA invocation."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
V9=Path('/home/youns/workspace/ele548-project-v9');V10=Path('/home/youns/workspace/ele548-project-v10');V11=Path('/home/youns/workspace/ele548-project-v11');V12=Path('/home/youns/workspace/ele548-project-v12');V13=Path('/home/youns/workspace/ele548-project-v13')
CC=Path('/opt/rh/gcc-toolset-11/root/usr/bin/g++')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def seconds(p):
 v=p.read_text().strip().splitlines()[-1].split();return float(v[0])+float(v[1])
def budget_previous():
 sizes={str(p):int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0]) for p in [V9,V10,V11,V12,V13,ROOT]}
 prep=sum(sizes[str(p)] for p in [V12,V13,ROOT]);recent=prep+sizes[str(V11)];total=sum(sizes.values())/1048576
 assert prep<112*1024 and recent<192*1024 and total<8 and total+20.54370880126953<34 and shutil.disk_usage(ROOT).free>=10*1024**3
 old=sum(seconds(p) for p in (V11/'overwrite_v11/runtime').rglob('*.time'))
 prior=sum(seconds(p) for root in [V12/'finite_source_v12/runtime',V13/'undo_packet_v13/runtime'] for p in root.rglob('*.time'));new=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time'))
 assert prior+new<900 and old+prior+new<9000 and 11.171808333333335+(old+prior+new)/3600<16 and 76.57026388888889+(old+prior+new)/3600<108
 return {'new_coreh':new/3600,'v12_v13_v14_coreh':(prior+new)/3600,'v11_and_later_coreh':(old+prior+new)/3600,'all6_GiB':total,'preparation_MiB':prep/1024,'v11_and_later_MiB':recent/1024,'CPU_new':0,'CPU_global':3487,'CPU_cap':3487}
def budget():
 if (BASE/'reports/BUDGET_AMENDMENT_3513.lock.json').exists():
  import importlib.util
  spec=importlib.util.spec_from_file_location('authorized_resources',BASE/'tools/resources.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod.snapshot()
 return budget_previous()
def invoke(label,args,limit=120):
 d=BASE/'runtime'/label;d.mkdir(exist_ok=False)
 with (d/'stdout').open('x') as out,(d/'stderr').open('x') as err:
  p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(limit),*map(str,args)],stdout=out,stderr=err,cwd=ROOT,timeout=limit+15)
 r={'command':list(map(str,args)),'exit_code':p.returncode,'stdout':ref(d/'stdout'),'stderr':ref(d/'stderr'),'time':ref(d/'job.time')};put(d/'EXECUTION.json',r);assert p.returncode==0,('FAILED_STAGE_RETAINED',label);return r
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--attempt',default='A1');ap.add_argument('--source-dir',choices=['src','measured_src'],default='src');a=ap.parse_args();budget()
 for x in json.loads((BASE/'reports/PRESERVATION.lock.json').read_text())['preserved']:assert sha(x['path'])==x['sha256']
 source=V9/'third_party/gem5-native-v9r2/src/cpu/pred/tage_base.cc';generated=BASE/'runtime/tage_base.cc';old=V13/'undo_packet_v13/runtime/tage_base.cc'
 if generated.exists():assert generated.read_bytes()==old.read_bytes()
 else:generated.write_bytes(old.read_bytes())
 lock=BASE/'reports'/('SOURCE_'+a.attempt+'.lock.json');put(lock,{'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_files':[ref(p) for folder in ['src','measured_src','tests','tools'] for p in sorted((BASE/folder).rglob('*')) if p.is_file()],'pinned_TAGE_source':ref(source),'generated':ref(generated),'new_CPU':0,'resources':budget()})
 flags=['-O2','-g0','-std=c++17','-I'+str(BASE/a.source_dir),'-I'+str(V9/'src'),'-I'+str(V9/'src/standalone'),'-I'+str(V9/'third_party/gem5-native-v9r2/src')]
 test=BASE/'tests/controller_gate.cpp';dep=invoke('dependencies_'+a.attempt,[CC,*flags,'-MM',test]);raw=Path(dep['stdout']['path']).read_text().replace('\\\n',' ');put(BASE/'reports'/('DEPENDENCIES_'+a.attempt+'.json'),{'files':[ref(p) for p in raw.split(':',1)[1].split()]})
 binary=BASE/'runtime'/('controller_gate_'+a.attempt);build=invoke('build_'+a.attempt,[CC,*flags,'-static-libstdc++','-static-libgcc',test,generated,'-o',binary]);manifest=BASE/'runtime'/('manifest_'+a.attempt+'.json');run=invoke('run_'+a.attempt,[binary,manifest]);data=json.loads(Path(run['stdout']['path']).read_text())
 put(BASE/'reports'/('CONTROLLER_GATE_'+a.attempt+'.json'),{'result':data,'source_lock':ref(lock),'binary':ref(binary),'manifest':ref(manifest),'build':build,'run':run,'resources':budget()});print(json.dumps({'result':data,'resources':budget()}))
if __name__=='__main__':main()
