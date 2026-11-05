"""Bounded authorized pipeline round; no daemon and no old job mutation."""
from pathlib import Path
import subprocess,time,json,datetime,sys
ROOT=Path(__file__).resolve().parents[1];R=ROOT/'rate_state_v5_pipeline/runtime';PY=ROOT/'.venv/bin/python'
deadline=time.monotonic()+12*3600
build1=R/'reports/BUILD_1.time'
while not build1.exists() or not build1.stat().st_size:
 assert time.monotonic()<deadline,'BOUNDED_BUILD_WAIT_EXPIRED'
 print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'Waiting for immutable BUILD1 to finish; no process interrupted',flush=True)
 time.sleep(55)
assert 'scons: done building targets.' in (R/'reports/BUILD_1.log').read_text(errors='replace'),'BUILD1_FAILED_RETAINED'
with (R/'reports/BUILD_2.log').open('w') as f:
 result=subprocess.run(['bash',ROOT/'setup/build_pipeline_v6.sh','2'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=7200)
assert result.returncode==0,'BUILD2_FAILED_RETAINED'
commands=[['pipeline_v6_gate.py','--phase','base'],['pipeline_v6_gate.py','--phase','fault'],['pipeline_v6_gate.py','--phase','freeze'],
 ['pipeline_v6_campaign.py','--phase','clean'],['pipeline_v6_campaign.py','--phase','pilot'],['pipeline_v6_campaign.py','--phase','freeze'],
 ['pipeline_v6_campaign.py','--phase','evaluation_clean'],['pipeline_v6_campaign.py','--phase','evaluation_fault'],['pipeline_v6_analyze.py']]
for index,args in enumerate(commands):
 assert time.monotonic()<deadline,'BOUNDED_PIPELINE_ROUND_WAIT_EXPIRED'
 dest=R/'reports'/f'DISPATCH_{index:02d}_{args[0]}.log';assert not dest.exists()
 print(datetime.datetime.now(datetime.timezone.utc).isoformat(),'RUN',' '.join(args),flush=True)
 with dest.open('w') as f:
  result=subprocess.run([PY,ROOT/'scripts'/args[0],*args[1:]],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=21600)
 if result.returncode:
  (R/'reports/DISPATCH_BLOCKER.json').write_text(json.dumps(dict(status='FAILED_STAGE_RETAINED',command=args,returncode=result.returncode,log=str(dest.relative_to(ROOT)),next='Inspect actual failure; at most two concrete fixes; do not rerun completed CPU prefixes or alter old producers.'),indent=2)+'\n')
  raise RuntimeError(('PIPELINE_STAGE_FAILED',args,str(dest)))
print('PIPELINE_CPU_CAMPAIGN_AND_ANALYSIS_COMPLETE; final integrity audit/package still required',flush=True)
