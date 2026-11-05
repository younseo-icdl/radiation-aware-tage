"""Compile the current V7 functional gates in a private, immutable attempt."""
from pathlib import Path
import argparse,datetime,hashlib,json,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rate_state_v5_pipeline_v7/runtime'
TARGET=ROOT/'third_party/gem5-rate-pipeline-v7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--attempt',default='R1');a=p.parse_args()
 assert a.attempt.isalnum(),'simple attempt label required'
 run=OUT/'gates'/a.attempt;assert not run.exists(),'Gate attempt already exists'
 run.mkdir(parents=True)
 old=ROOT/'rate_state_v5_pipeline/runtime/sources/standalone'
 binding=json.loads((old/'SOURCE_BINDING.json').read_text())
 for name,key in [('tage_base.cc','source_sha256'),('tage_base.hh','header_sha256')]:
  assert sha(TARGET/'src/cpu/pred'/name)==binding[key],('PINNED_TAGE_INPUT_CHANGED',name)
 assert sha(old/'tage_base.cc')==binding['generated_sha256']
 private=run/'standalone';private.mkdir();shutil.copy2(old/'tage_base.cc',private/'tage_base.cc')
 commands=[]
 def invoke(label,args,compiler=False):
  command=(['bash','-c','source /opt/rh/gcc-toolset-11/enable\nexec g++ "$@"','v7_cpp',*map(str,args)] if compiler else list(map(str,args)))
  timed=['/usr/bin/time','-f','%U %S %M','-o',str(run/(label+'.time')),*command]
  commands.append(timed)
  with (run/(label+'.log')).open('w') as f:r=subprocess.run(timed,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  if r.returncode:
   write(run/'FAILED.json',dict(status='FAILED_GATE_RETAINED',label=label,exit_code=r.returncode,commands=commands))
   raise RuntimeError(('CPP_GATE_FAILED_RETAINED',label,str(run/(label+'.log'))))
  return (run/(label+'.log')).read_text()
 obj=private/'tage_base.o'
 invoke('standalone_build',['-O2','-std=c++17','-Isrc/standalone','-I'+str(TARGET/'src'),'-c',private/'tage_base.cc','-o',obj],True)
 shared=['-O2','-std=c++17','-Isrc','-Isrc/standalone','-I'+str(TARGET/'src')]
 cases=[('TRANSPORT_GATE','pipeline_gate','PASS_FINITE_TRANSPORT'),
        ('DIFFERENTIAL_GATE','differential_gate','PASS_ACTUAL_TAGE_DIFFERENTIAL_AND_STAGE_SEU'),
        ('INDEPENDENT_TAGE_GATE','independent_tage_gate','PASS_ACTUAL_TAGE_INDEPENDENT_L2_II1')]
 reports=[]
 for report,name,status in cases:
  exe=run/name;source=ROOT/'src/rate_pipeline_v7'/(name+'.cpp')
  args=shared+[str(source)]+([] if name=='pipeline_gate' else [str(obj)])+['-o',str(exe)]
  invoke(name+'_build',args,True);stdout=invoke(name+'_run',[exe])
  assert ('PASS' in stdout),'gate did not report success'
  hashes={str(q.relative_to(ROOT)):sha(q) for q in (ROOT/'src/rate_pipeline_v7').rglob('*') if q.is_file()}
  for q in [ROOT/'src/protection/word.hpp',TARGET/'src/cpu/pred/tage_base.hh',TARGET/'src/cpu/pred/tage_base.cc',private/'tage_base.cc',obj,exe,run/(name+'_run.log'),run/(name+'_build.log')]:hashes[str(q.relative_to(ROOT))]=sha(q)
  result=dict(status=status,actual_stdout=stdout,hashes=hashes,attempt=a.attempt,
   commands=commands[:],source_binding=dict(original_pinned=binding,private_source=str((private/'tage_base.cc').relative_to(ROOT)),substitution='Existing stats-only standalone constructor substitution; original virtual TAGE hooks and algorithm unchanged'),
   scope='New V7 functional gate, not CPU overlap or physical PPA; metadata safety is a separate required gate.')
  if name=='independent_tage_gate':result['actual_counts']=json.loads(stdout.strip().splitlines()[-1])
  reports.append((report,result))
 for report,data in reports:write(OUT/'reports'/(report+'.json'),data)
 write(run/'COMPLETE.json',dict(status='PASS_ALL_THREE_FUNCTIONAL_GATES',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),commands=commands))
 print('PASS new transport, actual TAGE differential L1/L2, independent provider-stage overlap; separate metadata safety required')
if __name__=='__main__':main()
