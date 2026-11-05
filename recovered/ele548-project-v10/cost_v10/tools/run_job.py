"""Own isolated local EDA/test job, immutable log and actual GNUtime record."""
import argparse,datetime,hashlib,json,os,shlex,subprocess
from pathlib import Path
from budget import ROOT,BASE,check
p=argparse.ArgumentParser();p.add_argument('--tool',choices=['genus','xrun']);p.add_argument('--name',required=True);p.add_argument('--tcl');p.add_argument('--top');p.add_argument('--sv',nargs='*');p.add_argument('--plusarg',action='append',default=[]);p.add_argument('--timeout',type=int,default=900);args=p.parse_args()
assert args.name.replace('_','').isalnum(),'SIMPLE_JOB_NAME_REQUIRED'
run=BASE/'runtime'/args.name;assert not run.exists(),'IMMUTABLE_RUN';check();run.mkdir()
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['V10_RUN']=str(run)
if args.top:env['V10_TOP']=args.top
if args.tool=='genus':
    command=['genus','-batch','-files',str(ROOT/args.tcl),'-log',str(run/'genus.log'),'-overwrite']
else:
    command=['xrun','-64bit','-sv','-timescale','1ns/1ps',*map(str,args.sv),'-top',args.top,'-xmlibdirname',str(run/'xcelium.d'),'-logfile',str(run/'xrun.log'),*args.plusarg]
shell='cadence-activate && unsetenv DISPLAY && '+shlex.join(command)
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
with (run/'console.log').open('x') as f:
    job=subprocess.Popen(['/usr/bin/time','-v','-o',str(run/'job.time'),'csh','-c',shell],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
    try:rc=job.wait(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        import signal
        os.killpg(job.pid,signal.SIGTERM);job.wait();rc=-999
record=dict(status='EXECUTED_CHECK_STAGE_ACCEPTANCE_SEPARATELY',exit_code=rc,started_at_utc=started,ended_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=command,tool=args.tool,name=args.name,pid=job.pid,resource_before_next_stage=check())
(run/'EXECUTION.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2));raise SystemExit(0 if rc==0 else 2)
