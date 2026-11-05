#!/usr/bin/env python3
"""Approved existing-owner replication, maximum12; no retries or new RNG."""
from pathlib import Path
import concurrent.futures, datetime, fcntl, hashlib, importlib.util, json, math, os, re, shutil, subprocess, sys, time, traceback
sys.dont_write_bytecode = True
BASE=Path(__file__).resolve().parents[1]; ROOT=BASE.parent; REPORT=BASE/'reports'
OUT=BASE/'runtime/cpu_fault_next'
OLD=Path('/home/youns/workspace/ele548-project-v9'); V10=Path('/home/youns/workspace/ele548-project-v10')
spec=importlib.util.spec_from_file_location('old_validation',V10/'native_lifetime_next/tools/lifetime_runner.py')
prior=importlib.util.module_from_spec(spec); spec.loader.exec_module(prior)
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def load(p): return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p): return {'path':str(p),'sha256':sha(p)}
def put(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2); f.write('\n')
def checked(v):
    assert sha(v['path'])==v['sha256'],('SOURCE_CHANGED',v['path']);return Path(v['path'])
def seconds(p): return prior.time_seconds(p)
def resources(additional=0):
    assert len(list((OLD/'rate_state_v9').glob('**/reports/run_starts/*.json')))==352
    assert len(list((V10/'native_lifetime_next/runtime/reports/run_starts').glob('*.json')))==108
    assert len(list((BASE/'runtime/cpu_regression/run_starts').glob('*.json')))==6
    starts=list((OUT/'run_starts').glob('*.json'))
    assert len(starts)<=12 and 3475+len(starts)<=3487
    used=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time') if not p.is_relative_to(OUT))
    reserved=0
    for p in starts:
        marker=load(p); folder=OUT/marker['label']
        if (folder/'EXECUTION.json').exists(): used+=seconds(folder/'gem5.log.time')
        else: reserved+=marker['reserved_cpu_seconds']
    assert used+reserved+additional<2.5*3600,('V11_TIME_BUDGET',used,reserved,additional)
    assert 11.171808333333335+(used+reserved+additional)/3600<16
    assert 76.57026388888889+(used+reserved+additional)/3600<108
    def kib(p):return int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0])
    sizes={str(p):kib(p) for p in [OLD,V10,ROOT]};gib=sum(sizes.values())/1048576
    assert sizes[str(ROOT)]<192*1024 and gib<8 and gib+20.54370880126953<34
    assert shutil.disk_usage(ROOT).free>=10*1024**3
    return {'actual_global_CPU':3475+len(starts),'new_attempts':len(starts),'v11_recorded_coreh':used/3600,
            'inflight_reserved_coreh':reserved/3600,'combined_recorded_coreh':11.171808333333335+used/3600,
            'global_recorded_coreh':76.57026388888889+used/3600,'worktree_GiB':gib,
            'charged_total_GiB':gib+20.54370880126953,'disk_scope':'Inherited charged legacy snapshot plus actual3 worktrees; not full original workspace'}
def main():
    approval=REPORT/'BUDGET_AMENDMENT_3487.lock.json';auth=load(approval)
    assert auth['authorized_by']=='user' and auth['status']=='USER_AUTHORIZED_3487_AND_V11_2P5_COREH'
    proposal_path=checked(auth['proposal']);proposal=load(proposal_path)
    assert auth['CPU_cap']==3487 and auth['v11_coreh_cap']==2.5
    gate=load(checked(proposal['CPU_gate']));assert gate['status']=='PASS_ALL6_OVERWRITE_ZERO_FAULT_CPU_REGRESSIONS_NOT_COST_VALIDATION'
    binary=checked(gate['binary']);config=BASE/'gem5_overlay/o3_overwrite_v11.py'
    normal_plan=load(checked(gate['plan']));checked(normal_plan['config'])
    build=load(REPORT/'CPU_BUILD.lock.json')
    for item in build['actual_included_files']:checked(item)
    tasks=proposal['new_tasks'];assert len(tasks)==12 and not OUT.exists(),'NO_DUPLICATE_DISPATCH'
    clean={(r['program'],r['R']):r for r in gate['tasks']}
    pilot_keys={('qsort_small',1,'NATIVE_LIFETIME_NEXT.0.0'),('dijkstra_small',1,'NATIVE_LIFETIME_NEXT.1.0')}
    tasks.sort(key=lambda t:(0 if (t['program'],t['R'],t['owner']) in pilot_keys else 1,t['program'],t['R'],t['owner']))
    for t in tasks:t['timeout_seconds']=max(120,math.ceil(3*clean[t['program'],t['R']]['host_cpu_seconds']))
    OUT.mkdir();(OUT/'run_starts').mkdir()
    plan_path=REPORT/'FAULT12_PLAN.lock.json'
    put(plan_path,{'status':'USER_AUTHORIZED_FROZEN_BEFORE_FAULT12','at':now(),'authorization':ref(approval),
                   'proposal':ref(proposal_path),'tasks':tasks,'binary':ref(binary),'config':ref(config),'runner':ref(Path(__file__)),
                   'read_only_validator':ref(V10/'native_lifetime_next/tools/lifetime_runner.py'),
                   'case_definition':'Same6 owner/tick/site atR1/R8; development replication, no independent holdout',
                   'timeout_definition':'max120,3x corresponding actual overwrite normal host seconds; single-core process group; <=12 no retry'})
    resources(sum(t['timeout_seconds']+5 for t in tasks))
    rows=[]
    def one(t):
        with prior.slot() as lease:
            with (OUT/'COUNT.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX);before=resources(t['timeout_seconds']+5)
                assert before['new_attempts']<12
                for key in ['program_binary','control','expected_stdout','schedule']:checked(t[key])
                assert sha(binary)==gate['binary']['sha256'] and sha(config)==normal_plan['config']['sha256']
                put(OUT/'run_starts'/(t['label']+'.json'),{'label':t['label'],'at':now(),'plan':ref(plan_path),
                    'reserved_cpu_seconds':t['timeout_seconds']+5})
            folder=Path(t['output']);folder.mkdir(exist_ok=False)
            (folder/'schedule.ticks').write_bytes(Path(t['schedule']['path']).read_bytes())
            command=[str(binary),'--outdir='+str(folder),str(config),*t['config_arguments_without_schedule'],'--schedule',str(folder/'schedule.ticks')]
            core=sorted(os.sched_getaffinity(0))[:32][lease];start=time.perf_counter()
            env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
            row={'label':t['label'],'program':t['program'],'R':t['R'],'owner':t['owner'],'policy':'OVERWRITE',
                 'status':'FAIL_RETAINED','cycles':None,'started_at':now(),'output':str(folder),'command':command,'host_core':core}
            try:
                with (folder/'gem5.log').open('x') as log:
                    p=subprocess.run(['/usr/bin/taskset','-c',str(core),'/usr/bin/time','-f','%U %S %M','-o',str(folder/'gem5.log.time'),
                        '/usr/bin/timeout','--signal=TERM','--kill-after=3',str(t['timeout_seconds']),*command],
                        cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=t['timeout_seconds']+20)
                row['exit_code']=p.returncode;assert p.returncode==0,'CPU_FAILURE_OR_TIMEOUT'
                result=prior.validate(t,row,folder)
                assert result['seu']['representation_overwrite']==1 and result['total_bits']==65522
                for line in (folder/'gem5.log').read_text().splitlines():
                    if re.search(r'unsupported|unimplemented|ignoring syscall',line,re.I):
                        assert re.fullmatch(r'src/sim/syscall_emul\.hh:816: warn: Unsupported ioctl call \(return ENOTTY\): ioctl\(1, 0x5413, \.\.\.\) @ \(0x[0-9a-f]+=>0x[0-9a-f]+\)\.\(0=>1\)',line),'UNKNOWN_UNSUPPORTED_WARNING'
                row.update(result);row['status']='PASS_PROGRAM_AND_EXACT_LOGICAL_INJECTION'
            except Exception as e:
                row['failure']=repr(e);row['cycles']=None
                (folder/'validation_exception.txt').write_text(traceback.format_exc())
            row['wall_seconds']=time.perf_counter()-start;row['ended_at']=now()
            row['host_cpu_seconds']=seconds(folder/'gem5.log.time')
            row['hashes']={p.name:sha(p) for p in folder.iterdir() if p.is_file()}
            put(folder/'EXECUTION.json',row);return row
    def report(status):
        p=REPORT/'FAULT12.tmp';p.write_text(json.dumps({'status':status,'planned':12,'completed':len(rows),'plan':ref(plan_path),
                                                      'tasks':rows,'resources':resources()},indent=2)+'\n')
        os.replace(p,REPORT/'FAULT12.json')
    for start,width in [(0,2),(2,10)]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:rows.extend(pool.map(one,tasks[start:start+width]))
        passed=all(r['status'].startswith('PASS_') for r in rows)
        report(('RUNNING' if start==0 else 'PASS_ACTUAL12_FAULT_REPLICATION_NOT_INDEPENDENT_OR_COST_QUALIFICATION') if passed else 'FAIL_RETAINED_NO_RETRY')
        assert passed,'FAULT_GATE_FAILED_NO_RETRY'
        print('OVERWRITE_FAULT',len(rows),'/12 PASS',flush=True)
    assert resources()['actual_global_CPU']==3487
if __name__=='__main__':main()
