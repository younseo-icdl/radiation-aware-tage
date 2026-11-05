"""Continue only the frozen RAW130 scope after R1 WHOLE metadata failure.

No stopped report, source, producer, input or event tape is overwritten.
"""
import concurrent.futures, datetime, json, re, shutil
from pathlib import Path
import native_v9_common as c
from native_v9_confirm import verify_bound, SOURCE_NAME

ROOT,BASE=c.ROOT,c.OUT
OUT=ROOT/'rate_state_v9/source_continuation/runtime'

def total_markers():
    return list((BASE/'reports/run_starts').glob('*.json'))+list((OUT/'reports/run_starts').glob('*.json'))

def budget(width=0):
    assert 3009+len(total_markers())+width<=3200,'GLOBAL_CPU_CAP'
    assert len(list((OUT/'reports/run_starts').glob('*.json')))+width<=20,'SOURCE_CONTINUATION_20_CAP'
    assert not list((ROOT/'rate_state_v9').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT'
    assert c.used_seconds()<12*3600 and c.used_seconds()/3600+65.39845555555556<108,'COREH_CAP'
    assert c.disk_gib()<8 and c.disk_gib()+20.54370880126953<34,'DISK_CAP'
    assert shutil.disk_usage(ROOT).free>=10*1024**3,'FREE10GIB'

def run(t):
    with c.slot():
        start=datetime.datetime.now(datetime.timezone.utc).isoformat();marker=OUT/'reports/run_starts'/(t['label']+'.json');assert not marker.exists()
        c.write(marker,dict(phase=t['phase'],label=t['label'],started_at=start))
        r=c.cpu.run_cpu(t);r.update(started_at=start,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        if r['status']=='PASS':
            log=(ROOT/r['output']/'gem5.log').read_text()
            if re.search(r'instruction .*unimplemented|ignoring syscall|unimplemented syscall',log,re.I):r.update(status='FAIL_VALIDATION',failure='UNSUPPORTED_ISA_OR_SYSCALL')
            s=r['seu']
            if s['end_tick']>t['tape_horizon_ticks']:r.update(status='FAIL_VALIDATION',failure='TAPE_HORIZON_EXCEEDED')
            assert s['scheduled_events']==s['applied_events']+s['unapplied_future_events']
        if r['status']!='PASS':r['cycles']=None
        return r

def main():
    verify_bound();stopped=c.load(BASE/'reports/HOLDOUT_FAULT.json');assert stopped['status']=='STOPPED_RETAINED'
    original=c.load(BASE/'configs/HOLDOUT_FAULT.lock.json')['tasks'];completed={r['label'] for r in stopped['tasks']}
    tasks=[]
    for t in original:
        if t['label'] not in completed and t['scenario']==SOURCE_NAME:
            task=dict(t);task['phase']='SOURCE_CONTINUATION';tasks.append(task)
    assert len(tasks)==20
    for folder in ['configs','reports']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    lock=OUT/'configs/SCOPE_AMENDMENT.lock.json';assert not lock.exists(),'IMMUTABLE_SOURCE_CONTINUATION'
    budget(20)
    c.write(lock,dict(status='DECLARED_BEFORE_INDEPENDENT_SCOPE_CONTINUATION',reason='WHOLE pending.active bit is outside conditional RAW130 source event scope. No source/predictor/config/binary/input/RNG/tape changes.',count=20,global_before=3166,global_after_if_all_started=3186,global_cap=3200,stopped_report=c.ref(BASE/'reports/HOLDOUT_FAULT.json'),original_task_lock=c.ref(BASE/'configs/HOLDOUT_FAULT.lock.json'),producer=c.ref(BASE/'configs/PRODUCER.lock.json'),helpers={str(Path(__file__).relative_to(ROOT)):c.sha(Path(__file__))},tasks=tasks,no_changed_failure_classification=True,no_affected_whole_tasks_launched=True))
    c.cpu.OUT=OUT;c.cpu.BINARY=c.BINARY;c.cpu.CONFIG=c.CONFIG
    report=OUT/'reports/SOURCE_CONTINUATION.json';result=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
        offset=0
        while offset<len(tasks):
            width=min(2 if offset==0 else 30,len(tasks)-offset);budget(width)
            result.extend(pool.map(run,tasks[offset:offset+width]));offset+=width
            failed=[r for r in result if r['status']!='PASS']
            c.write(report,dict(status='STOPPED_RETAINED' if failed else ('PASS' if len(result)==20 else 'RUNNING'),planned=20,tasks=result))
            print('SOURCE_CONTINUATION',len(result),'/20',len(failed),'failures',flush=True)
            if failed:raise RuntimeError(('SOURCE_CONTINUATION_FAILED_RETAINED',[r['label'] for r in failed]))
    print('PASS source20; original WHOLE failure/partial reports preserved',flush=True)

if __name__=='__main__':main()
