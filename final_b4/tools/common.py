from pathlib import Path
import datetime,json,subprocess,sys
sys.dont_write_bytecode=True
import resources as r
BASE=r.BASE;CC='/opt/rh/gcc-toolset-11/root/usr/bin/g++'
V9=Path('/home/youns/workspace/ele548-project-v9');V15=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
def freeze(label):
 files=[];dest=BASE/'runtime/frozen';dest.mkdir(exist_ok=True)
 for folder in ('src','tests','tools','gem5_overlay'):
  for p in sorted((BASE/folder).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts:
    item=r.ref(p);d=dest/(item['sha256']+p.suffix)
    if not d.exists():d.write_bytes(p.read_bytes())
    item['verified_bytes']=str(d);files.append(item)
 out=BASE/'reports'/(label+'.source.lock.json');r.put(out,{'files':files,'CPU_new':r.snapshot()['CPU_new']});return r.ref(out)
def invoke(label,args,limit=300,extra_MiB=4):
 r.snapshot(limit,extra_MiB);d=BASE/'runtime'/label;d.mkdir(exist_ok=False)
 with (d/'stdout').open('x') as out,(d/'stderr').open('x') as err:
  p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(limit),*map(str,args)],stdout=out,stderr=err,cwd=BASE,timeout=limit+15)
 row={'command':list(map(str,args)),'exit_code':p.returncode,'stdout':r.ref(d/'stdout'),'stderr':r.ref(d/'stderr'),'time':r.ref(d/'job.time')};r.put(d/'EXECUTION.json',row)
 assert p.returncode==0,('FAILED_STAGE_RETAINED',label);return row
def compile_gate(name,attempt):
 label=name+'_'+attempt;lock=freeze(label);source=BASE/'tests'/(name+'.cpp');binary=BASE/'runtime'/label
 flags=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(V9/'src'),'-I'+str(V9/'src/standalone'),'-I'+str(V9/'third_party/gem5-native-v9r2/src')]
 build=invoke(label+'_build',[CC,*flags,'-static-libstdc++','-static-libgcc',source,V15/'runtime/tage_base.cc','-o',binary],limit=300)
 run=invoke(label+'_run',[binary],limit=300);result=json.loads(Path(run['stdout']['path']).read_text());r.put(BASE/'reports'/(label+'.json'),{'result':result,'source':lock,'binary':r.ref(binary),'build':build,'run':run,'resources':r.snapshot()});print(json.dumps(result))
