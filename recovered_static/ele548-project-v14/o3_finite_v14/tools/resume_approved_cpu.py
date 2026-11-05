#!/usr/bin/env python3
"""Admit only unstarted approved matched groups after a budget-only stop.

Preserves the original runner, its stop and all outputs. Reuses the exact frozen
trial function via AST, changing only host admission order. No retry, new case,
timeout, input, seed, binary or simulated schedule is permitted.
"""
from pathlib import Path
import argparse, ast, concurrent.futures, fcntl, json, sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_cpu as original
BASE=original.BASE
def main():
    p=argparse.ArgumentParser();p.add_argument('--run',action='store_true');p.add_argument('--attempt',required=True);a=p.parse_args()
    load=original.load
    stop_path=BASE/'reports/CPU_STOP_BUDGET.json'
    assert stop_path.exists(),'WAIT_FOR_ORIGINAL_BUDGET_STOP'
    assert load(stop_path)['status']=='STOP_BEFORE_DISPATCH_COMPLETE_MATCHED_GROUPS'
    plan_path=BASE/'reports/CPU24_PLAN.lock.json';plan=load(plan_path)
    for key in ['runner','binary','config','proposal','authorization']:original.checked(plan[key])
    allocation=BASE/'reports/INTERNAL_CPU_ALLOCATION_R1.lock.json'
    assert allocation.exists()
    guard_path=BASE/'tools/resources_followon.py'
    original.r=original.mod('allocated_resource_guard',guard_path)
    assert original.r.phase_cap()==3.55
    bounds_path=BASE/'reports/CPU_PROGRAM18_HOST_BOUNDS.lock.json';bounds=load(bounds_path)
    assert bounds['CPU24_plan']['sha256']==original.m.sha(plan_path)
    build=load(BASE/'reports/MEASURED_BINARY_B1.json')
    for item in build['actual_dependencies']:original.checked(item)
    starts=list((original.OUT/'run_starts').glob('*.json'))
    all_rows=[];started=set()
    for marker in starts:
        label=load(marker)['label'];started.add(label)
        path=original.OUT/label/'EXECUTION.json'
        assert path.exists(),'ORIGINAL_COHORT_STILL_HAS_OUTSTANDING_RESERVATION'
        row=load(path);assert row['status'].startswith('PASS_'),'CORRECT_FAILURE_BEFORE_NEW_CPU'
        all_rows.append(row)
    groups=[]
    for i in range(0,18,3):
        group=bounds['tasks'][i:i+3];present=[t['label'] in started for t in group]
        assert all(present) or not any(present),'INCOMPLETE_STARTED_MATCHED_GROUP'
        if not any(present):groups.append(group)
    # Preserve order when possible, but a shorter independent matched group may
    # run when the first one cannot be reserved. Only host order can change.
    if not a.run:
        print(json.dumps({'status':'DRY_RUN_NO_DISPATCH','pending_groups':groups,'resources':original.r.snapshot()},indent=2));return
    new_plan=BASE/'reports'/('CPU_REMAINDER_'+a.attempt+'.lock.json')
    original.m.put(new_plan,{'status':'EXISTING_USER_AUTHORIZATION_PENDING_TASKS_ONLY','original_stop':original.m.ref(stop_path),
        'CPU24_plan':original.m.ref(plan_path),'bounds':original.m.ref(bounds_path),'tool':original.m.ref(Path(__file__)),
        'allocation':original.m.ref(allocation),'resource_guard':original.m.ref(guard_path),
        'admission_only_change':'dynamic complete-group admission as reservations become actual; exact original one(t); aggregate caps/timeouts/config/inputs retained',
        'groups':groups,'resources':original.r.snapshot()})
    namespace=vars(original).copy()
    namespace.update(binary=original.checked(build['binary']),config=original.checked(plan['config']),
        build=build,proposal=load(original.checked(plan['proposal'])),plan=plan_path)
    tree=ast.parse(original.checked(plan['runner']).read_text())
    main_node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    one=next(n for n in main_node.body if isinstance(n,ast.FunctionDef) and n.name=='one')
    exec(compile(ast.Module(body=[one],type_ignores=[]),str(original.checked(plan['runner'])),'exec'),namespace)
    dispatch=namespace['one'];round_id=0;failed=False;active={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
        while groups or active:
            if not failed:
                for group in list(groups):
                    if len(active)+len(group)>32:continue
                    cost=sum(t['timeout_seconds']+5 for t in group)
                    # Use the exact same COUNT lock as the frozen trial function
                    # so snapshots cannot read partially published markers.
                    with (original.OUT/'COUNT.lock').open('a+') as lock:
                        fcntl.flock(lock,fcntl.LOCK_EX)
                        unmarked=[t for t in active.values() if not (original.OUT/'run_starts'/(t['label']+'.json')).exists()]
                        try:original.r.snapshot(cost+sum(t['timeout_seconds']+5 for t in unmarked),len(group)+len(unmarked))
                        except AssertionError:continue
                    groups.remove(group)
                    for task in group:active[pool.submit(dispatch,task)]=task
                    print('ADMITTED',','.join(t['label'] for t in group),flush=True)
            if not active:break
            finished,_=concurrent.futures.wait(active,timeout=55,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                task=active.pop(future);row=future.result();all_rows.append(row)
                if not row['status'].startswith('PASS_'):failed=True
                original.m.put(BASE/'reports'/('CPU_REMAINDER_'+a.attempt+'_RESULT'+str(round_id)+'.json'),
                    {'status':row['status'],'task':row,'plan':original.m.ref(new_plan),'resources':original.r.snapshot()})
                print('COMPLETED',task['label'],row['status'],row.get('cycles'),flush=True);round_id+=1
    identities={}
    for row in all_rows:identities.setdefault(row['program'],set()).add(row['seu']['committed_identity'])
    matched=all(len(values)==1 for values in identities.values())
    original.m.put(BASE/'reports'/('CPU_REMAINDER_'+a.attempt+'_FINAL.json'),
        {'status':'PASS_ALL_24_CLEAN_NOT_PROTECTION_COMPARISON' if not groups and len(all_rows)==24 and matched and not failed else 'STOP_BUDGET_OR_UNRESOLVED_VISIBLE',
            'tasks':all_rows,'unrun':groups,'same_architectural_identity':matched,'plan':original.m.ref(new_plan),'resources':original.r.snapshot()})
    print('REMAINDER_TERMINAL',len(all_rows),'unrun_groups',len(groups),'matched_identity',matched,flush=True)
    assert not failed,'FAILED_STAGE_PRESERVED_NO_RETRY'
if __name__=='__main__':main()
