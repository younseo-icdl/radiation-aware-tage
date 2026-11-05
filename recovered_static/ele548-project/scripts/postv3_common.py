"""Minimal reuse of native-checked O3 runner in a separate evidence namespace."""
import concurrent.futures
import json
from pathlib import Path
import v3_common as common
import v3_cpu_common as runner

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'postv3/runtime'
common.OUT=OUT
runner.OUT=OUT
runner.BINARY=ROOT/'third_party/gem5-postv3/build/X86_STAGE0/gem5.opt'
runner.CONFIG=ROOT/'gem5/o3_postv3.py'
sha,write,timed,used_cpu=common.sha,common.write,common.timed,common.used_cpu
RESOURCE=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']
variants=[dict(id='N1',scheme='P_ED',policy='N1',k=64,C=1),
          *[dict(id=n,scheme='P_ED',policy='STAGED',k=64,C=1,group=g)
            for n,g in [('P_ALL130',0),('P_3STAGE',3),('P_2_EARLY',1),('P_2_LATE',2)]]]
P0=dict(id='P0',scheme='P0',policy='LEGACY',k=0,C=0)

def task(variant,item,phase,scenario,owner,events='',extra=None,**kw):
    v=variant.copy();group=v.pop('group',3)
    return dict(v,input=item,phase=phase,program=item['name'],U=0,scenario=scenario,
        label=item['name']+'.'+scenario+'.'+owner+'.'+v['id'],owner=owner,events_text=events,
        additional_args=RESOURCE+['--promotion-group',str(group)]+(extra or []),**kw)

def execute(tasks,name,workers=2):
    report=OUT/'reports'/f'{name}.json'
    assert not report.exists(),str(report)
    source=sha(OUT/'configs/source.lock.json')
    write(OUT/'configs'/f'{name}.lock.json',dict(status='FROZEN_BEFORE_EXECUTION',tasks=tasks,
        source_lock_sha256=source,binary_sha256=sha(runner.BINARY),config_sha256=sha(runner.CONFIG)))
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        for start in range(0,len(tasks),workers):
            assert used_cpu()<32*3600,'ROUND_CHECKPOINT_NO_MORE_DISPATCH'
            batch=list(pool.map(runner.run_cpu,tasks[start:start+workers]))
            for r in batch:
                r['diagnostic_clean_timing']=r['id']=='SHAM_WAIT';rows.append(r)
                write(report,dict(status='RUNNING',planned=len(tasks),completed=len(rows),tasks=rows))
                print(name,len(rows),r['label'],r['status'],r.get('failure'),flush=True)
            if any(r['status']!='PASS' for r in batch):
                write(report,dict(status='FAIL_RETAINED',planned=len(tasks),completed=len(rows),
                    not_dispatched=len(tasks)-len(rows),tasks=rows))
                raise RuntimeError('Gate failure retained; no automatic campaign continuation')
    write(report,dict(status='PASS',planned=len(tasks),completed=len(rows),tasks=rows,
        source_lock_sha256=source,recorded_core_hours=used_cpu()/3600))
    return rows
