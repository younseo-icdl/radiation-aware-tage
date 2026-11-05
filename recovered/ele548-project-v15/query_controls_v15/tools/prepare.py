#!/usr/bin/env python3
"""Bounded v15 preparation; old producers read-only; no CPU simulation."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
V14=Path('/home/youns/workspace/ele548-project-v14/o3_finite_v14');V9=Path('/home/youns/workspace/ele548-project-v9')
CC=Path('/opt/rh/gcc-toolset-11/root/usr/bin/g++')
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def put(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def seconds(p):
 a=Path(p).read_text().strip().splitlines()[-1].split();return float(a[0])+float(a[1])
def budget(extra_MiB=0,extra_seconds=0):
 s=importlib.util.spec_from_file_location('old_resources',V14/'tools/resources_followon.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);old=m.snapshot()
 assert old['new_CPU']==24 and old['outstanding_reservations']==0
 assert not list((BASE/'runtime').glob('**/run_starts/*.json')),'NO_NEW_CPU_AUTHORIZATION'
 used=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time'))
 size=int(subprocess.check_output(['du','-sk',str(ROOT)],text=True).split()[0])/1024
 assert old['preparation_recorded_coreh']+(used+extra_seconds)/3600<.25
 assert old['recent_recorded_coreh']+(used+extra_seconds)/3600<5 and old['v9_onward_recorded_coreh']+(used+extra_seconds)/3600<16 and old['global_recorded_coreh']+(used+extra_seconds)/3600<108
 assert old['preparation_MiB']+size+extra_MiB<240 and old['recent_MiB']+size+extra_MiB<320
 assert old['all6_GiB']+(size+extra_MiB)/1024<8 and old['all6_GiB']+(size+extra_MiB)/1024+20.54370880126953<34 and shutil.disk_usage(ROOT).free>=10*1024**3
 return {'CPU_global':3511,'CPU_cap':3513,'CPU_new':0,'reserve2':'failed-stage regression only','preparation_coreh':old['preparation_recorded_coreh']+used/3600,'recent_coreh':old['recent_recorded_coreh']+used/3600,'v9_onward_coreh':old['v9_onward_recorded_coreh']+used/3600,'global_coreh':old['global_recorded_coreh']+used/3600,'v15_MiB':size,'preparation_MiB':old['preparation_MiB']+size,'recent_MiB':old['recent_MiB']+size,'all7_GiB':old['all6_GiB']+size/1024}
def preserve():
 for p in json.loads((BASE/'reports/PRESERVATION.lock.json').read_text())['preserved']:assert sha(p['path'])==p['sha256'],p['path']
def freeze(label):
 out=BASE/'runtime/frozen';out.mkdir(exist_ok=True);files=[]
 for folder in ['src','tests','tools','gem5_overlay']:
  for p in sorted((BASE/folder).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:
    item=ref(p);dst=out/(item['sha256']+p.suffix)
    if not dst.exists():dst.write_bytes(p.read_bytes())
    files.append(dict(item,verified_bytes=str(dst)))
 lock=BASE/'reports'/(label+'.source.lock.json');put(lock,{'files':files,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'CPU_new':0});return ref(lock)
def invoke(label,args,limit=150):
 d=BASE/'runtime'/label;d.mkdir(exist_ok=False)
 with (d/'stdout').open('x') as out,(d/'stderr').open('x') as err:
  p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(limit),*map(str,args)],stdout=out,stderr=err,cwd=ROOT,timeout=limit+15)
 row={'command':list(map(str,args)),'exit_code':p.returncode,'stdout':ref(d/'stdout'),'stderr':ref(d/'stderr'),'time':ref(d/'job.time')};put(d/'EXECUTION.json',row)
 assert p.returncode==0,('FAILED_STAGE_RETAINED',label);return row
def gate(name,attempt,arguments=()):
 budget(extra_seconds=150,extra_MiB=3);preserve();label=name+'_'+attempt;lock=freeze(label)
 source=BASE/'tests'/(name+'.cpp');binary=BASE/'runtime'/label
 flags=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(V9/'src'),'-I'+str(V9/'src/standalone'),'-I'+str(V9/'third_party/gem5-native-v9r2/src')]
 deps=invoke(label+'_dependencies',[CC,*flags,'-MM',source]);raw=Path(deps['stdout']['path']).read_text().replace('\\\n',' ').split(':',1)[1].split();put(BASE/'reports'/(label+'.dependencies.json'),{'files':[ref(p) for p in raw]})
 build=invoke(label+'_build',[CC,*flags,'-static-libstdc++','-static-libgcc',source,BASE/'runtime/tage_base.cc','-o',binary])
 run=invoke(label+'_run',[binary,*arguments]);data=json.loads(Path(run['stdout']['path']).read_text());preserve()
 put(BASE/'reports'/(label+'.json'),{'result':data,'source_lock':lock,'binary':ref(binary),'build':build,'run':run,'resources':budget()});print(json.dumps(data))
if __name__=='__main__':print(json.dumps(budget(),indent=2))
