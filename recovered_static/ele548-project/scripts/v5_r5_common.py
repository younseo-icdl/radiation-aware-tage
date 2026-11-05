"""R5 evidence is isolated; immutable R4 is only a named reference."""
import v5_common as base
from v5_common import ROOT,sha,write,timed,used_cpu
OUT=ROOT/'rate_state_v5/runtime_r5'
OLD=ROOT/'rate_state_v5/runtime'
base.OUT=OUT;base.common.OUT=OUT;base.cpu.OUT=OUT
execute,note=base.execute,base.note
from v5_variants import V,make,task
import json
V.update({
 'BATCH_DIRECT':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--representation','direct','--journal-service','--journal-merge-undo','--undo-batch-latency','2','--lookup-ii','1']),
 'BATCH_READ1':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--representation','direct','--journal-service','--journal-merge-undo','--undo-batch-latency','2','--lookup-ii','1','--lookup-latency','1']),
 'BATCH_READ2':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--representation','direct','--journal-service','--journal-merge-undo','--undo-batch-latency','2','--lookup-ii','1','--lookup-latency','2']),
 'BATCH_UNDO1':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--representation','direct','--journal-service','--journal-merge-undo','--undo-batch-latency','1','--lookup-ii','1']),
 'BATCH_STRAT16':dict(scheme='P0',policy='LEGACY',k=0,C=0,opts=['--representation','stratum','--tap-budget','16','--journal-service','--journal-merge-undo','--undo-batch-latency','2','--lookup-ii','1']),
})
def clean_rows():return json.loads((OUT/'reports/CLEAN.json').read_text())['tasks']
def clean_row(program,ident):return next(r for r in clean_rows() if r['program']==program and r['id']==ident)
