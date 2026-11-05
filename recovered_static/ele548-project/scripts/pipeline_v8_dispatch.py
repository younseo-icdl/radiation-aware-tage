"""Bounded V8 orchestration after a root-launched build; never starts a build."""
from pathlib import Path
import argparse,datetime,json,subprocess,time
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'rate_state_v5_pipeline_v8/runtime';PY=ROOT/'.venv/bin/python'
def main():
 p=argparse.ArgumentParser();p.add_argument('--wait-build',action='store_true');p.add_argument('--finish-reports',action='store_true');a=p.parse_args();deadline=time.monotonic()+12*3600
 while True:
  request=OUT/'configs/BUILD_EXPECTED.json'
  if request.exists():
   d=json.loads(request.read_text());i=d['build_id'];log=OUT/'reports'/f'BUILD_{i}.log';timing=OUT/'reports'/f'BUILD_{i}.time'
   if timing.exists() and timing.stat().st_size:
    assert log.exists() and 'scons: done building targets.' in log.read_text(errors='replace'),'DECLARED_BUILD_FAILED_RETAINED';break
  assert a.wait_build,'No completed declared build; root must launch it first'
  assert time.monotonic()<deadline,'BOUNDED_BUILD_WAIT_EXPIRED'
  print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'Waiting for root-launched declared V8 build',flush=True);time.sleep(55)
 commands=[['pipeline_v8_bind_build.py'],['pipeline_v8_campaign.py','--phase','declare'],['pipeline_v8_gate.py','--phase','base'],['pipeline_v8_gate.py','--phase','fault'],['pipeline_v8_gate.py','--phase','source_clean'],['pipeline_v8_gate.py','--phase','source'],['pipeline_v8_gate.py','--phase','freeze'],['pipeline_v8_campaign.py','--phase','clean'],['pipeline_v8_campaign.py','--phase','pilot'],['pipeline_v8_campaign.py','--phase','freeze'],['pipeline_v8_campaign.py','--phase','evaluation_clean'],['pipeline_v8_campaign.py','--phase','replication'],['pipeline_v8_campaign.py','--phase','old_failure_replay'],['pipeline_v8_campaign.py','--phase','source_failure_replay'],['pipeline_v8_campaign.py','--phase','holdout'],['pipeline_v8_campaign.py','--phase','journal_clean'],['pipeline_v8_campaign.py','--phase','journal_holdout'],['pipeline_v8_analyze.py']]
 if a.finish_reports:commands += [['pipeline_v8_final_audit.py'],['pipeline_v8_package.py']]
 for index,args in enumerate(commands):
  assert time.monotonic()<deadline,'BOUNDED_V8_DISPATCH_DEADLINE'
  log=OUT/'reports'/f'DISPATCH_{index:02d}_{args[0]}.log';assert not log.exists(),'IMMUTABLE_DISPATCH_ATTEMPT'
  print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'RUN',' '.join(args),flush=True)
  with log.open('w') as f:r=subprocess.run([PY,ROOT/'scripts'/args[0],*args[1:]],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=21600)
  if r.returncode:
   (OUT/'reports/DISPATCH_BLOCKER.json').write_text(json.dumps(dict(status='FAILED_STAGE_RETAINED',command=args,returncode=r.returncode,log=str(log.relative_to(ROOT)),next='Inspect actual failure; preserve prefix/producer, no completed task rerun or outcome tuning. At most two concrete fixes with a new source/binary namespace when required.'),indent=2)+'\n');raise RuntimeError(('V8_STAGE_FAILED_RETAINED',args))
 print('V8 bounded command list complete; final integrity/package only if explicitly selected',flush=True)
if __name__=='__main__':main()
