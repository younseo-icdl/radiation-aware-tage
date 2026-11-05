"""Concrete finite-resource CPU acceptance gate, separate from campaign plans."""
import json,subprocess
import v3_cpu_common as runner
from v3_cpu_common import *
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt'
runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
inputs=json.loads((OUT/'configs/design_inputs.lock.json').read_text())['programs']
small=OUT/'inputs/checksum';small.mkdir(exist_ok=True);p=small/'ignored.dat';p.write_text('')
bin=ROOT/'build/checksum_freestanding';native=subprocess.run([bin,p],capture_output=True);assert native.returncode==0 and not native.stderr
stdout=small/'native.stdout';stdout.write_bytes(native.stdout)
item=dict(name='checksum',binary=str(bin.relative_to(ROOT)),binary_sha256=sha(bin),input=str(p.relative_to(ROOT)),input_sha256=sha(p),native_stdout_sha256=sha(stdout))
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());raw=scope['payload_words'][21]['site_ids'][2];fold=scope['payload_words'][18]['site_ids'][2]
cases=[]
for name,scheme,policy,k,mode,split in [('P0','P0','LEGACY',0,'SHARED2',False),('ED','P_ED','LEGACY',0,'SHARED2',False),('ECC','P_ECC','LEGACY',0,'SHARED2',False),('TMR','P_TMR','LEGACY',0,'SHARED2',False),('N1','P_ED','N1',64,'SHARED2',False),('P','P_ED','STAGED',64,'SHARED2',False),('D1','P_ED','H1',32,'SHARED1',True),('D2','P_ED','H1',32,'SPLIT2',True),('Dshared2','P_ED','H1',32,'SHARED2',True),('H1combined','P_ED','H1',32,'SHARED2',False)]:
 for label,events in [('zero',''),('raw',f'400000 {raw}\n'),('fold',f'400000 {fold}\n')]:
  cases.append(dict(phase='B_CPU_gate',program='checksum',input=item,id=name,scheme=scheme,policy=policy,k=k,C=0 if scheme=='P0' else 1,U=0,owner='V3_GATE_'+name+'_'+label,scenario=label,label=name+'.'+label,events_text=events,additional_args=['--resource-mode',mode,'--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if split else [])))
results=[]
for t in cases:
 r=runner.run_cpu(t);results.append(r);write(OUT/'reports/B_CPU_GATE.json',dict(status='RUNNING',planned=len(cases),completed=len(results),tasks=results,binary_sha256=sha(runner.BINARY)))
 print(r['label'],r['status'],r.get('failure'),flush=True)
 if r['status']!='PASS':
  write(OUT/'reports/B_CPU_GATE.json',dict(status='FAIL_RETAINED',planned=len(cases),completed=len(results),tasks=results,binary_sha256=sha(runner.BINARY)))
  raise SystemExit('CPU gate failed; inspect first failure before campaigning')
 for key in ['hot','shadow']:
  s=r['seu'];assert s[key+'_accepted']==s[key+'_completed']+s[key+'_cancelled']+s[key+'_pending']
write(OUT/'reports/B_CPU_GATE.json',dict(status='PASS',planned=len(cases),completed=len(results),tasks=results,binary_sha256=sha(runner.BINARY),conservation_checked=True,publication='Functional mutations run only at finite service completion; no issue-atomic history debt in endpoint mode'))
print('PASS finite-resource real CPU gates',len(cases))
