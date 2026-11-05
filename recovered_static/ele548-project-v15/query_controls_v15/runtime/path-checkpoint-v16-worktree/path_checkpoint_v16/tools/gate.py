#!/usr/bin/env python3
"""C++ preparation only. The immutable parent charges this nested worktree."""
from pathlib import Path
import datetime,hashlib,importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parent
PARENT=Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
V9=Path('/home/youns/workspace/ele548-project-v9')
CC=Path('/opt/rh/gcc-toolset-11/root/usr/bin/g++')
spec=importlib.util.spec_from_file_location('v15_prepare_readonly',PARENT/'tools/prepare.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
sha=parent.sha;ref=parent.ref;put=parent.put
def preserve():
 parent.preserve()
 for item in json.loads((BASE/'reports/PRESERVATION.lock.json').read_text())['preserved']:
  assert sha(item['path'])==item['sha256'],item['path']
def freeze(label):
 out=BASE/'runtime/frozen';out.mkdir(exist_ok=True);items=[]
 for directory in ('src','tests','tools'):
  for path in sorted((BASE/directory).rglob('*')):
   if path.is_file() and '__pycache__' not in path.parts:
    item=ref(path);dst=out/(item['sha256']+path.suffix)
    if not dst.exists():dst.write_bytes(path.read_bytes())
    items.append(dict(item,verified_bytes=str(dst)))
 items.append(ref(BASE/'runtime/tage_base.cc'))
 lock=BASE/'reports'/(label+'.source.lock.json')
 put(lock,{'files':items,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_CPU':0})
 return ref(lock)
def invoke(label,args,limit=150,extra_MiB=.1):
 parent.budget(extra_seconds=limit,extra_MiB=extra_MiB)
 d=BASE/'runtime'/label;d.mkdir(exist_ok=False)
 with (d/'stdout').open('x') as out,(d/'stderr').open('x') as err:
  result=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'job.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(limit),*map(str,args)],stdout=out,stderr=err,cwd=ROOT,timeout=limit+15)
 row={'command':list(map(str,args)),'exit_code':result.returncode,'stdout':ref(d/'stdout'),'stderr':ref(d/'stderr'),'time':ref(d/'job.time')}
 put(d/'EXECUTION.json',row)
 assert result.returncode==0,('FAILED_STAGE_RETAINED',label)
 return row
def gate(attempt):
 parent.budget(extra_seconds=150,extra_MiB=2);preserve()
 label='protocol_'+attempt;lock=freeze(label)
 src=BASE/'tests/protocol.cpp';binary=BASE/'runtime'/label
 flags=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(V9/'src'),'-I'+str(V9/'src/standalone'),'-I'+str(V9/'third_party/gem5-native-v9r2/src')]
 dependencies=invoke(label+'_dependencies',[CC,*flags,'-MM',src],10)
 paths=Path(dependencies['stdout']['path']).read_text().replace('\\\n',' ').split(':',1)[1].split()
 put(BASE/'reports'/(label+'.dependencies.json'),{'files':[ref(p) for p in paths]})
 build=invoke(label+'_build',[CC,*flags,'-static-libstdc++','-static-libgcc',src,BASE/'runtime/tage_base.cc','-o',binary],extra_MiB=2)
 run=invoke(label+'_run',[binary])
 result=json.loads(Path(run['stdout']['path']).read_text())
 old=json.loads((PARENT/'reports/early_gate_A3.json').read_text())['result']
 oldkeys=('mode','query_L','update_L','conditional','early')
 for row in result['timing_cases']:
  if row['path_only']:continue
  match=[p for p in old['timing_cases'] if all(p[k]==row[k] for k in oldkeys)]
  assert len(match)==1
  assert all(row[k]==v for k,v in match[0].items()),('BACKWARD_TIMING_MISMATCH',row)
 preserve()
 put(BASE/'reports'/(label+'.json'),{'result':result,'source_lock':lock,'binary':ref(binary),'dependencies':ref(BASE/'reports'/(label+'.dependencies.json')),'build':build,'run':run,'backward_timing_cases':24,'resources':parent.budget()})
 print(json.dumps(result,indent=2))
if __name__=='__main__':
 if len(sys.argv)==2:gate(sys.argv[1])
 else:print(json.dumps(parent.budget(),indent=2))
