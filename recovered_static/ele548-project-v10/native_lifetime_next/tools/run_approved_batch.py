"""Durable phase orchestration; each frozen runner phase enforces approval/caps."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'native_lifetime_next';OUT=BASE/'runtime';REPORTS=OUT/'reports';REPORTS.mkdir(exist_ok=True)
status=REPORTS/'BATCH_DRIVER.json';assert not status.exists(),'IMMUTABLE_BATCH_DRIVER_EXISTS'
python=ROOT/'.venv/bin/python';runner=BASE/'tools/lifetime_runner.py'
assert str(Path(sys.executable).absolute())==str(python)
assert (OUT/'configs/BUDGET_AMENDMENT.lock.json').is_file(),'USER_AUTHORIZATION_REQUIRED'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
record=dict(status='RUNNING',started_at=now(),pid=os.getpid(),driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),phases=[],new_global_cap=3475)
def save():
    p=status.with_suffix('.tmp');p.write_text(json.dumps(record,indent=2)+'\n');os.replace(p,status)
save()
for phase in ['clean','fault-plan','fault']:
    command=[str(python),'-B',str(runner),'--phase',phase,'--workers','32']
    entry=dict(phase=phase,started_at=now(),command=command);record['phases'].append(entry);save()
    with (REPORTS/('phase_'+phase+'.console.log')).open('x') as stream:
        p=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
    entry.update(exit_code=p.returncode,ended_at=now());save()
    if p.returncode:
        record.update(status='STOPPED_RETAINED_FAILED_PHASE',ended_at=now());save();raise SystemExit(2)
record.update(status='COMPLETE_ALL_PRIMARY_PHASES_CHECK_ACCEPTANCE_AND_ANALYZE',ended_at=now());save()
