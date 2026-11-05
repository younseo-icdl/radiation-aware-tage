#!/usr/bin/env python3
"""At most6 zero-fault regressions under the existing3475 CPU cap."""
from pathlib import Path
import concurrent.futures,contextlib,csv,datetime,fcntl,hashlib,importlib.util,json,os,re,subprocess,sys,time,traceback
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;OUT=BASE/'runtime/cpu_regression'
V10=Path('/home/youns/workspace/ele548-project-v10');OLD=Path('/home/youns/workspace/ele548-project-v9')
spec=importlib.util.spec_from_file_location('v11_tools',BASE/'tools/prepare_gate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
spec=importlib.util.spec_from_file_location('frozen_lifetime_validation',V10/'native_lifetime_next/tools/lifetime_runner.py');prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def static_caps():
    assert len(list((OLD/'rate_state_v9').glob('**/reports/run_starts/*.json')))==352
    assert len(list((V10/'native_lifetime_next/runtime/reports/run_starts').glob('*.json')))==108
    count=len(list((OUT/'run_starts').glob('*.json')))
    assert count<=6 and 3469+count<=3475
    return count
def main():
    m.budget();assert not OUT.exists(),'NO_DUPLICATE_CPU_REGRESSION_DRIVER'
    build_path=BASE/'reports/CPU_BUILD.lock.json';build=json.loads(build_path.read_text())
    assert build['status']=='PASS_NEW_INCREMENTAL_GEM5_BINARY_BUILT_NOT_CPU_REGRESSION_TESTED'
    binary=Path(build['binary']['path']);assert m.sha(binary)==build['binary']['sha256']
    config=BASE/'gem5_overlay/o3_overwrite_v11.py'
    old_report=V10/'native_lifetime_next/runtime/reports/LIFETIME_CLEAN.json';clean=json.loads(old_report.read_text())
    assert clean['status']=='PASS'
    controls={(r['program'],r['R']):r for r in clean['tasks'] if r['policy']=='U'}
    task_lock=V10/'native_lifetime_next/runtime/configs/LIFETIME_CLEAN.lock.json'
    original=json.loads(task_lock.read_text())
    OUT.mkdir();(OUT/'run_starts').mkdir()
    tasks=[]
    for key in [('qsort_small',1),('dijkstra_small',1),('qsort_small',8),('dijkstra_small',8),('sha1',1),('sha1',8)]:
        source=next(t for t in original['tasks'] if (t['program'],t['R'],t['policy'])==(*key,'U'))
        t=json.loads(json.dumps(source));t['phase']='V11_ZERO_FAULT_REGRESSION';t['policy']='OVERWRITE';t['label']=key[0]+'.R'+str(key[1])+'.OVERWRITE'
        t['output']=str(OUT/t['label']);args=t['config_arguments_without_schedule'];args[args.index('--representation')+1]='overwrite'
        assert t['schedule']['sha256']==hashlib.sha256(b'').hexdigest()
        tasks.append(t)
    plan={'status':'FROZEN_BEFORE_SIX_EXISTING_RESERVE_ZERO_FAULT_REGRESSIONS','at':now(),'purpose':'Regression gate only, no fault performance selection or new campaign','user_scope':'Active user goal minimum structural change; existing cap3475 and6 reserved regression cases; no cap/time/disk increase',
          'global_before':3469,'global_cap':3475,'maximum_new_cpu':6,'tasks':tasks,'old_report':m.ref(old_report),'old_task_lock':m.ref(task_lock),
          'binary':m.ref(binary),'config':m.ref(config),'build':m.ref(build_path),'tool':m.ref(Path(__file__)),
          'normal_cost':'C0 assumed, native synchronous reference; normal equivalence, not physical timing advantage','shared_slots':32}
    plan_path=BASE/'reports/CPU_REGRESSION_PLAN.lock.json';m.write(plan_path,plan)
    rows=[]
    def one(t,timeout):
        with prior.slot() as lease:
            with (OUT/'COUNT.lock').open('a+') as lock:
                fcntl.flock(lock,fcntl.LOCK_EX);assert static_caps()<6
                for field in ['program_binary','control','expected_stdout','schedule']:
                    assert m.sha(t[field]['path'])==t[field]['sha256']
                m.write(OUT/'run_starts'/(t['label']+'.json'),{'at':now(),'phase':t['phase'],'label':t['label'],'plan':m.ref(plan_path)})
            folder=Path(t['output']);folder.mkdir(exist_ok=False)
            (folder/'schedule.ticks').write_bytes(b'')
            command=[str(binary),'--outdir='+str(folder),str(config),*t['config_arguments_without_schedule'],'--schedule',str(folder/'schedule.ticks')]
            core=sorted(os.sched_getaffinity(0))[:32][lease]
            env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
            row={'label':t['label'],'program':t['program'],'R':t['R'],'status':'FAIL_RETAINED','cycles':None,'command':command,'started_at':now(),'host_core':core,'timeout_seconds':timeout,'output':str(folder)}
            start=time.perf_counter()
            try:
                with (folder/'gem5.log').open('x') as log:
                    timed=['/usr/bin/taskset','-c',str(core),'/usr/bin/time','-f','%U %S %M','-o',str(folder/'gem5.log.time'),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(timeout),*command]
                    process=subprocess.run(timed,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout+20)
                row['exit_code']=process.returncode;assert process.returncode==0,'CPU_FAILED_OR_TIMEOUT'
                result=prior.validate(t,row,folder)
                reference=controls[(t['program'],t['R'])]
                for field in ['cycles','instructions','total_bits']:assert result[field]==reference[field],('NORMAL_REFERENCE_DIFFERENCE',field)
                for field in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:
                    assert result['seu'][field]==reference['seu'][field],('NORMAL_STATE_RNG_DIFFERENCE',field)
                assert result['seu']['representation_overwrite']==1 and result['seu']['overwrite_forward_calls']>0
                for line in (folder/'gem5.log').read_text().splitlines():
                    if re.search(r'unsupported|unimplemented|ignoring syscall',line,re.I):
                        assert re.fullmatch(r'src/sim/syscall_emul\.hh:816: warn: Unsupported ioctl call \(return ENOTTY\): ioctl\(1, 0x5413, \.\.\.\) @ \(0x[0-9a-f]+=>0x[0-9a-f]+\)\.\(0=>1\)',line),'UNKNOWN_UNSUPPORTED_WARNING'
                row.update(result);row['status']='PASS_NORMAL_FUNCTION_STATE_CPU_C0_NOT_TIMING_QUALIFICATION'
            except Exception as error:
                row['status']='FAIL_RETAINED';row['cycles']=None;row['failure']=repr(error)
                (folder/'validation_exception.txt').write_text(traceback.format_exc())
            row['wall_seconds']=time.perf_counter()-start;row['ended_at']=now()
            row['host_cpu_seconds']=prior.time_seconds(folder/'gem5.log.time')
            row['hashes']={p.name:m.sha(p) for p in folder.iterdir() if p.is_file()}
            m.write(folder/'EXECUTION.json',row)
            return row
    status=BASE/'reports/CPU_REGRESSION.json'
    def save():
        p=status.with_suffix('.tmp');p.write_text(json.dumps({'status':'RUNNING','planned':6,'completed':len(rows),'tasks':rows},indent=2)+'\n');os.replace(p,status)
    for start,width in [(0,2),(2,4)]:
        current=m.budget();remaining=(1-current['recorded_v11_coreh'])*3600
        timeout=min(1200,int(remaining/width)-5);assert timeout>=120
        reservation=BASE/'reports'/('CPU_RESERVATION_'+str(start)+'.json')
        m.write(reservation,{'status':'BOUNDED_INFLIGHT_ONE_CORE_PROCESSGROUPS','width':width,'timeout_seconds':timeout,'maximum_cpu_seconds':width*(timeout+4),'remaining_seconds':remaining,'plan':m.ref(plan_path)})
        with concurrent.futures.ThreadPoolExecutor(max_workers=width) as pool:
            rows.extend(pool.map(lambda t:one(t,timeout),tasks[start:start+width]))
        save();m.budget();assert all(r['status'].startswith('PASS_') for r in rows),'REGRESSION_GATE_FAILED_RETAINED'
        print('NORMAL_OVERWRITE_REGRESSION',len(rows),'/6 PASS',flush=True)
    final={'status':'PASS_ALL6_OVERWRITE_ZERO_FAULT_CPU_REGRESSIONS_NOT_COST_VALIDATION','actual_global_cpu':3469+static_caps(),'new_cpu_runs':len(rows),'fault_cpu_runs':0,'plan':m.ref(plan_path),'binary':m.ref(binary),'tasks':rows,'resources':m.budget()}
    p=status.with_suffix('.final.tmp');p.write_text(json.dumps(final,indent=2)+'\n');os.replace(p,status)
if __name__=='__main__':main()
