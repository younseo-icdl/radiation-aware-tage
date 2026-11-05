"""V5 owns its evidence; earlier producers and results are immutable inputs."""
import concurrent.futures
import datetime
import json
import shutil
import resource
import fcntl,time,contextlib
from pathlib import Path
import v3_common as common
import v3_cpu_common as cpu

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rate_state_v5/runtime'
common.OUT=OUT
cpu.OUT=OUT
resource.setrlimit(resource.RLIMIT_CORE,(0,0))  # Own workers only; retain logs, avoid huge abort dumps.
sha,write,timed=common.sha,common.write,common.timed
def timed_cpu(command,log,**kwargs):
    # Same simulated deadline and resources; long R32 tasks need a host limit
    # supported by measured R1 speed. A host timeout is never a masked fault.
    args=list(map(str,command))
    if '--max-ticks' in args and args[args.index('--max-ticks')+1]=='2000000000000':
        kwargs['timeout']=7200
    return timed(command,log,**kwargs)
cpu.timed=timed_cpu
def used_cpu():
    total=0.
    for folder in (ROOT/'rate_state_v5').glob('runtime*'):
        if not folder.is_dir():continue
        for p in folder.rglob('*.time'):
            try:v=p.read_text().splitlines()[-1].split();total+=float(v[0])+float(v[1])
            except (ValueError,IndexError):pass
    return total
_run_cpu=cpu.run_cpu
@contextlib.contextmanager
def trial_slot():
    folder=ROOT/'rate_state_v5/.cpu_slots';folder.mkdir(exist_ok=True)
    held=None
    while held is None:
        for slot in range(8):
            f=(folder/f'{slot}.lock').open('a+')
            try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held=f;break
            except BlockingIOError:f.close()
        if held is None:time.sleep(.2)
    try:yield
    finally:fcntl.flock(held,fcntl.LOCK_UN);held.close()
def run_cpu_observed(t):
    with trial_slot():
        started=datetime.datetime.now(datetime.timezone.utc).isoformat()
        marker=OUT/'reports/run_starts'/f"{t['phase']}.{t['label']}.json"
        assert not marker.exists(),marker
        write(marker,dict(started_at=started,label=t['label'],phase=t['phase']))
        r=_run_cpu(t)
        r.update(started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        return r
cpu.run_cpu=run_cpu_observed

def note(identifier, status, observation, decision, next_action, **fields):
    record=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        hypothesis_id=identifier,status=status,observation=observation,
        decision=decision,next_experiment=next_action,
        question='Does removing recursive history state improve total performance under the stated exposure and resource contract?',
        competing_explanations=['Recursive-state persistence dominates source-event damage','Clean accuracy, finite service, speculative timing or table learning dominates total CPU cost'],**fields)
    with (OUT/'HYPOTHESIS_LOG.jsonl').open('a') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n')

def execute(tasks,name,workers=2,old=False,allowed_fault_failures=(),pilot_first_batch=0):
    if old:
        cpu.BINARY=ROOT/'third_party/gem5-postv3/build/X86_STAGE0/gem5.opt';cpu.CONFIG=ROOT/'gem5/o3_postv3.py'
    else:
        lock=OUT/'configs/PRODUCER.lock.json';pending=OUT/'configs/BUILT_PRODUCER.pending.json'
        producer=json.loads((lock if lock.exists() else pending).read_text()) if lock.exists() or pending.exists() else None
        cpu.BINARY=ROOT/(producer['binary'] if producer else 'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt')
        cpu.CONFIG=ROOT/(producer['config'] if producer else 'gem5/o3_rate_state_v5.py')
        relocation=OUT/'configs/PRODUCER.relocation.json'
        if relocation.exists():
            moved=json.loads(relocation.read_text());assert moved['original_lock_sha256']==sha(lock) and moved['binary_sha256']==producer['binary_sha256'];cpu.BINARY=ROOT/moved['binary']
        if producer:assert sha(cpu.BINARY)==producer['binary_sha256'] and sha(cpu.CONFIG)==producer['config_sha256'],'PRODUCER_MUTATED'
    report=OUT/'reports'/f'{name}.json'
    task_lock=OUT/'configs'/f'{name}.lock.json'
    rows=[]
    if report.exists():
        previous=json.loads(report.read_text());assert previous['status']=='RUNNING',('IMMUTABLE_TERMINAL_REPORT',report)
        frozen=json.loads(task_lock.read_text());assert frozen['tasks']==tasks,'RESUME_TASKS_CHANGED'
        assert frozen['binary_sha256']==sha(cpu.BINARY) and frozen['config_sha256']==sha(cpu.CONFIG),'RESUME_PRODUCER_CHANGED'
        rows=previous['tasks'];assert len(rows)<=len(tasks)
        for index,row in enumerate(rows):
            assert row['label']==tasks[index]['label'] and row['producer_binary_sha256']==frozen['binary_sha256']
            assert row['status']=='PASS' or allowed_fault_failures,'RESUME_RETAINS_FAULT_FAILURES_ONLY'
        print(name,'RESUME completed immutable prefix',len(rows),flush=True)
    else:
        content=dict(status='FROZEN_BEFORE_DISPATCH',tasks=tasks,binary_sha256=sha(cpu.BINARY),config_sha256=sha(cpu.CONFIG))
        if task_lock.exists():assert json.loads(task_lock.read_text())==content,'EXISTING_TASK_LOCK_CHANGED'
        else:write(task_lock,content)
    note(name+'.preflight','PLANNED',f'{len(tasks)} tasks frozen in configs/{name}.lock.json',
         'Native answers and protocol gates required; signed losses and zero-effect owners retained',
         'Analyze each program and paired owner before selecting or rejecting candidates',
         planned_run_count=len(tasks),failure_policy='Assertion/timeout/unsupported syscall/native mismatch never counted as masked fault',
         success_criterion_predeclared='normal2%, practical gain0.05pp; uncertainty and resource contracts retained')
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        start=len(rows)
        while start<len(tasks):
            width=min(workers,pilot_first_batch) if start==0 and pilot_first_batch else workers
            assert used_cpu()<96*3600,'96_CORE_HOUR_CAP'
            assert shutil.disk_usage(ROOT).free>=10*1024**3,'MIN_FREE_DISK_10GIB'
            count=0
            for folder in (ROOT/'rate_state_v5').glob('runtime*'):
                for p in (folder/'reports').glob('*.json'):
                    if p==report:continue
                    try:
                        payload=json.loads(p.read_text())
                        if isinstance(payload,dict):count+=len(payload.get('tasks',[]))
                    except json.JSONDecodeError:pass # Another runner may be atomically replacing its progress file.
            assert count+len(rows)+width<=2400,'CPU_RUN_CAP'
            batch=list(pool.map(cpu.run_cpu,tasks[start:start+width]))
            start+=width
            for r in batch:
                s=r.get('seu',{})
                if r['status']=='PASS' and 'journal_accepted' in s and s['journal_accepted']!=s['journal_completed']+s['journal_cancelled']+s['journal_pending']:
                    r.update(status='FAIL_VALIDATION',failure='JOURNAL_QUEUE_CONSERVATION')
            for r in batch:
                rows.append(r)
                with (OUT/'EXPERIMENT_LEDGER.jsonl').open('a') as f:
                    f.write(json.dumps({k:r.get(k) for k in ['label','status','started_at','ended_at','command','host_cpu_seconds','wall_seconds','max_rss_kib','output','producer_binary_sha256','failure']})+'\n')
                print(name,len(rows),r['label'],r['status'],r.get('failure'),flush=True)
            write(report,dict(status='RUNNING',tasks=rows,planned=len(tasks)))
            unexpected=[]
            for r in batch:
                if r['status']=='PASS':continue
                log=(ROOT/r['output']/'gem5.log').read_text(errors='replace') if r.get('output') else ''
                if not allowed_fault_failures or not any(message in log for message in allowed_fault_failures):unexpected.append(r)
            if unexpected:
                write(report,dict(status='FAIL_RETAINED',tasks=rows,planned=len(tasks),not_dispatched=len(tasks)-len(rows)))
                raise RuntimeError('Failed CPU stage retained; diagnose before further dispatch')
            if pilot_first_batch and len(rows)==width:
                peak=max(r.get('max_rss_kib') or 0 for r in rows)
                available=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
                assert peak*workers<available/2,'PILOT_MEMORY_GATE'
                write(OUT/'reports'/f'{name}_PILOT_SPEED.json',dict(status='PASS',actual_runs=len(rows),pilot_workers=width,
                    expanded_workers=workers,max_rss_kib=peak,available_ram_kib=available,mean_host_seconds=sum(r['host_cpu_seconds'] for r in rows)/len(rows),
                    remaining_host_seconds_estimate=(len(tasks)-len(rows))*sum(r['host_cpu_seconds'] for r in rows)/len(rows),forecast_is_not_measured=True))
    write(report,dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'COMPLETED_WITH_FAILED_RUNS',tasks=rows,planned=len(tasks),
        failed_runs=sum(r['status']!='PASS' for r in rows),allowed_fault_failure_messages=allowed_fault_failures,recorded_core_hours=used_cpu()/3600))
    return rows

def task(item, ident, phase, scenario, owner, event='', scheme='P0', policy='LEGACY', k=0,C=0, extra=None):
    return dict(id=ident,input=item,program=item['name'],phase=phase,scenario=scenario,owner=owner,
        label=f"{item['name']}.{scenario}.{owner}.{ident}",events_text=event,
        scheme=scheme,policy=policy,k=k,C=C,U=0,additional_args=extra or [])
