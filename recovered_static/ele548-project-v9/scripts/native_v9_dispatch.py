"""One dispatcher; waits for root-launched private build, never starts/rebuilds it."""
from pathlib import Path
import datetime,json,subprocess,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'rate_state_v9/runtime';PY=ROOT/'.venv/bin/python'
def main():
 deadline=time.monotonic()+12*3600
 while True:
  timing=OUT/'reports/BUILD_1.time';log=OUT/'reports/BUILD_1.log'
  if timing.exists() and timing.stat().st_size:
   assert 'scons: done building targets.' in log.read_text(errors='replace'),'NEW_BUILD_FAILED_RETAINED';break
  assert time.monotonic()<deadline,'BUILD_WAIT_EXPIRED'
  print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'Waiting for actual root-launched V9 build',flush=True);time.sleep(50)
 commands=[['native_v9_gate.py','--phase',phase] for phase in ['bind','normal','sbu','due','freeze']]+[['native_v9_campaign.py','--phase',phase] for phase in ['clean','development']]+[['native_v9_analyze.py']]
 for index,args in enumerate(commands):
  assert time.monotonic()<deadline,'DISPATCH_DEADLINE';log=OUT/'reports'/f'DISPATCH_{index:02d}.log';assert not log.exists(),'IMMUTABLE_DISPATCH'
  print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'RUN',args,flush=True)
  with log.open('w') as stream:r=subprocess.run([PY,ROOT/'scripts'/args[0],*args[1:]],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=6*3600)
  if r.returncode:
   (OUT/'reports/DISPATCH_BLOCKER.json').write_text(json.dumps(dict(status='FAILED_STAGE_RETAINED',command=args,exit_code=r.returncode,log=str(log.relative_to(ROOT)),next='Inspect retained actualfailure; do not rerun frozen tasks or mutate producer; stop affected track, continue independent analysis/RTL'),indent=2)+'\n');raise RuntimeError(('V9_AFFECTED_STAGE_FAILED',args))
 print('V9 first declared108 CPU + analysis completed; independent finalconfirmation is separately frozen',flush=True)
if __name__=='__main__':main()
