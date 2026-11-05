"""Clean scheduling diagnostic only; SHAM never enters protection rankings."""
from postv3_common import *
assert json.loads((OUT/'reports/CPU_GATE_ACCEPTANCE.json').read_text())['status']=='PASS'
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
sham=dict(id='SHAM_WAIT',scheme='P0',policy='LEGACY',k=64,C=1)
vs=[P0]+variants+[sham]
jobs=[]
for item in inputs:
    for v in vs:
        # Only P0/N1/P3/SHAM need detailed aligned branch provenance.
        extra=['--audit','--audit-limit','20000'] if v['id'] in ['P0','N1','P_3STAGE','SHAM_WAIT'] else []
        if v['id']=='SHAM_WAIT':extra+=['--sham-wait','--schedule','']
        jobs.append(task(v,item,'CLEAN','zero','POSTV3_CLEAN',extra=extra))
execute(jobs,'CLEAN',workers=2)
