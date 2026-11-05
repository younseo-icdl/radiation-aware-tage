"""Thirteen bounded R2 correctness trials; no new performance campaign."""
import argparse, concurrent.futures, datetime, json, re, shutil
from pathlib import Path
import native_v9_common as c
import native_v9_gate as oldgate

ROOT=c.ROOT;OUT=ROOT/'rate_state_v9/r2/runtime';BINARY=ROOT/'third_party/gem5-native-v9r2/build/X86_PIPELINE/gem5.opt';CONFIG=ROOT/'gem5/o3_native_v9r2.py'
COUNTS={'GATE_NORMAL':6,'PENDING_ACTIVE_SBU':6,'OLD_FAILURE_REPLAY':1}
def put(p,d):assert not p.exists(),('IMMUTABLE_R2',str(p));c.write(p,d)
def verify():
    s=c.load(OUT/'configs/source.lock.json')
    for name,h in s['files'].items():assert c.sha(ROOT/name)==h,('R2_SOURCE_CHANGED',name)
    for name,h in s['transport'].items():assert c.sha(ROOT/'third_party/gem5-native-v9r2/src'/name)==h,('R2_TRANSPORT_CHANGED',name)
    assert c.sha(CONFIG)==s['config']['sha256']
    for key in ['cpp_gate','cpp_gate_binding','r1_producer','r1_preservation']:
        p=ROOT/s[key]['path'];assert c.sha(p)==s[key]['sha256'],('R2_BOUND_REFERENCE_CHANGED',key)
    assert c.load(ROOT/s['cpp_gate']['path'])['status'].startswith('PASS')
    cpp=c.load(ROOT/s['cpp_gate_binding']['path']);assert cpp['status'].startswith('PASS')
    for name,h in cpp['source'].items():assert c.sha(ROOT/name)==h,('R2_TESTED_CLASS_CHANGED',name)
    for name,h in s['installed_extensions'].items():assert c.sha(ROOT/'third_party/gem5-native-v9r2/src/cpu/pred'/Path(name).name)==h,('R2_COMPILE_COPY_CHANGED',name)
    bound=OUT/'configs/BUILT_PRODUCER.pending.json'
    if bound.exists():assert c.load(bound)['source']==c.ref(OUT/'configs/source.lock.json'),'R2_SOURCE_LOCK_CHANGED_AFTER_BIND'
    for name,h in c.load(OUT/'configs/PRESERVED_R1.lock.json')['hashes'].items():assert c.sha(ROOT/name)==h,('R1_CHANGED',name)
    return s
def starts():return list((ROOT/'rate_state_v9').glob('**/reports/run_starts/*.json'))
def budget(n=0):
    assert 3009+len(starts())+n<=3200,'GLOBAL3200_CPU_CAP'
    assert len(list((OUT/'reports/run_starts').glob('*.json')))+n<=13,'R2_CORRECTNESS13_CAP'
    assert c.used_seconds()<12*3600 and 65.39845555555556+c.used_seconds()/3600<108,'CORE_HOURS'
    assert c.disk_gib()<8 and c.disk_gib()+20.54370880126953<34,'DISK_CAP'
    assert shutil.disk_usage(ROOT).free>=10*1024**3,'FREE10GIB'
    assert not list((ROOT/'rate_state_v9').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT'
def bind():
    source=verify();log=OUT/'reports/BUILD_1.log';timing=OUT/'reports/BUILD_1.time'
    assert 'scons: done building targets.' in log.read_text(errors='replace') and c.seconds(timing)>0,'R2_ACTUAL_BUILD_INCOMPLETE'
    assert c.sha(BINARY)!=source['copied_old_binary_sha256'],'COPIED_R1_BINARY_NOT_R2_BUILD'
    budget(13)
    put(OUT/'configs/BUILT_PRODUCER.pending.json',dict(status='ACTUAL_R2_BUILD_BOUND_NOT_CPU_GATED',binary=c.ref(BINARY),config=c.ref(CONFIG),source=c.ref(OUT/'configs/source.lock.json'),build_log=c.ref(log),build_time=c.ref(timing),cpp=c.ref(OUT/'gates/CPP_GATE_BINDING.json')))
    put(OUT/'configs/ROUND.lock.json',dict(status='DECLARED_BEFORE_R2_CPU',phase_counts=COUNTS,planned_cpu=13,global_before=3186,global_after_if_complete=3199,global_cap=3200,new_v9_coreh_cap=12,global_coreh_cap=108,shared_slot_cap=32,first_pilot_trials=2,producer=c.ref(OUT/'configs/BUILT_PRODUCER.pending.json'),script=c.ref(Path(__file__)),scope='Correctness-only common protected pending endpoint. Reused old failure tape is deterministic replication, not independent holdout. No new WHOLE/performance qualification.'))
def run(t):
    with c.slot():
        start=datetime.datetime.now(datetime.timezone.utc).isoformat();p=OUT/'reports/run_starts'/(t['phase']+'.'+t['label']+'.json');put(p,dict(phase=t['phase'],label=t['label'],started_at=start))
        r=c.cpu.run_cpu(t);r.update(started_at=start,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        if r['status']=='PASS':
            if re.search(r'instruction .*unimplemented|ignoring syscall|unimplemented syscall',(ROOT/r['output']/'gem5.log').read_text(),re.I):r.update(status='FAIL_VALIDATION',failure='UNSUPPORTED_ISA_OR_SYSCALL')
        if r['status']=='PASS' and t.get('tape_horizon_ticks') and r['seu']['end_tick']>t['tape_horizon_ticks']:r.update(status='FAIL_VALIDATION',failure='TAPE_HORIZON_EXCEEDED')
        if r['status']!='PASS':
            r['cycles']=None;r.setdefault('hashes',{}).update({p.name:c.sha(p) for p in (ROOT/r['output']).iterdir() if p.is_file() and p.name!='gem5.log.time'})
        return r
def execute(tasks,name):
    verify();bound=c.load(OUT/'configs/BUILT_PRODUCER.pending.json')
    assert c.sha(BINARY)==bound['binary']['sha256'] and c.sha(CONFIG)==bound['config']['sha256']
    assert len(tasks)==COUNTS[name]
    lock=OUT/'configs'/(name+'.lock.json');put(lock,dict(status='FIXED_BEFORE_R2_PHASE',tasks=tasks,round=c.ref(OUT/'configs/ROUND.lock.json')))
    report=OUT/'reports'/(name+'.json');assert not report.exists()
    c.cpu.OUT=OUT;c.cpu.BINARY=BINARY;c.cpu.CONFIG=CONFIG;rows=[];offset=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        while offset<len(tasks):
            width=min(2 if offset==0 else 6,len(tasks)-offset);budget(width)
            rows.extend(pool.map(run,tasks[offset:offset+width]));offset+=width
            failed=[r for r in rows if r['status']!='PASS']
            c.write(report,dict(status='STOPPED_RETAINED' if failed else ('PASS' if len(rows)==len(tasks) else 'RUNNING'),planned=len(tasks),tasks=rows))
            print(name,len(rows),len(failed),'failures',flush=True)
            if failed:raise RuntimeError(('R2_CORRECTNESS_FAILED_RETAINED',name,[r['label'] for r in failed]))
    return rows
def normal():
    item=c.load(c.OUT/'configs/development_inputs.lock.json')['checksum']
    rows=execute([c.make(item,i,'GATE_NORMAL',audit=True) for i in c.IDS],'GATE_NORMAL')
    oldgate.OUT=OUT;oldgate.compare_normal(rows)
    original=next(r for r in c.load(c.OUT/'reports/GATE_NORMAL.json')['tasks'] if r['id']=='U');ref=next(r for r in rows if r['id']=='U')
    for file in ['committed_audit.csv','committed_audit.csv.training.csv']:assert c.sha(ROOT/ref['output']/file)==c.sha(ROOT/original['output']/file),('R2_VS_R1_FULL_AUDIT',file)
    expected={'U':65522,'C_PAR_FREQUENT':65586,'C_PAR_PERIODIC':65594,'C_ECC':65684,'C_TMR':66214,'A_DIR':66354}
    for row in rows:
        assert row['total_bits']==expected[row['id']]
        assert row['seu']['native_pending_bits']==152 and row['seu']['native_pending_repairs']==0
    put(OUT/'reports/R1_R2_NORMAL_EQUALITY.json',dict(status='PASS_FULL_CHECKSUM_READ_TRAINING_BYTE_IDENTICAL_R1_R2_AND_ALL_SIX',r1=c.ref(c.OUT/'reports/GATE_NORMAL.json'),r2=c.ref(OUT/'reports/GATE_NORMAL.json'),actual_manifest_bits=expected))
def active():
    normal=c.load(OUT/'reports/GATE_NORMAL.json')['tasks'];item=c.load(c.OUT/'configs/development_inputs.lock.json')['checksum'];tasks=[]
    for row in normal:
        manifest=c.load(ROOT/row['output']/'logical_manifest.json')
        sites=[s['id'] for s in manifest['additional_sites'] if s['structure']=='pending_lookup_record' and s['bit']==67 and s['replica']==0];assert len(sites)==1
        tasks.append(c.make(item,row['id'],'PENDING_ACTIVE_SBU','PENDING_ACTIVE','DIRECTED','400000 '+str(sites[0])+'\n',expected=row['instructions']))
    rows=execute(tasks,'PENDING_ACTIVE_SBU')
    for r in rows:
        s=r['seu'];assert s['applied_events']==s['applied_flips']==1
        assert s['native_pending_repairs']==1 and s['native_pending_corrected_copies']==1 and s['native_pending_uncorrectable']==0
        assert s['response_hold_cycles']>=1,('REAL_PENDING_CORRECTION_HOLD',r['id'])
    put(OUT/'reports/PENDING_ACTIVE_ACCEPTANCE.json',dict(status='PASS_ALL_SIX_ACTUAL_NATIVE_PENDING_ACTIVE_SBU_WITH_RESPONSE_HOLD',source=c.ref(OUT/'reports/PENDING_ACTIVE_SBU.json'),scope='One directed active-bit event and program answer. C++ class covers bounded total<=2physical flips; not exhaustive CPU squash/ownership/metadata scenarios.'))
def replay():
    old=c.load(c.OUT/'configs/HOLDOUT_FAULT.lock.json')['tasks'];target=next(t for t in old if t['label']=='dijkstra_small.WHOLE_K1_REF_SCALE10000000000000000.V9_CONFIRMATION.1.0.A_DIR')
    task=dict(target);task['phase']='OLD_FAILURE_REPLAY';task['owner']='R1_FAILURE_REPLICATION';task['label']='dijkstra.R1_FAILURE_REPLICATION.A_DIR'
    r=execute([task],'OLD_FAILURE_REPLAY')[0]
    assert r['seu']['native_pending_repairs']>=1
    put(OUT/'reports/OLD_FAILURE_ACCEPTANCE.json',dict(status='PASS_R2_EXACT_OLD_TAPE_ANSWER_AND_PENDING_REPAIR',source=c.ref(OUT/'reports/OLD_FAILURE_REPLAY.json'),old_task_lock=c.ref(c.OUT/'configs/HOLDOUT_FAULT.lock.json'),old_failed_raw='rate_state_v9/runtime/reports/HOLDOUT_FAULT/'+target['label'],schedule_sha256=r['schedule_sha256'],new_whole_added_metadata_not_targeted_by_this_replay=True,not_independent_evaluation=True))
def freeze():
    for name in ['R1_R2_NORMAL_EQUALITY','PENDING_ACTIVE_ACCEPTANCE','OLD_FAILURE_ACCEPTANCE']:assert c.load(OUT/'reports'/(name+'.json'))['status'].startswith('PASS')
    verify();put(OUT/'configs/PRODUCER.lock.json',dict(status='PASS_BOUNDED_R2_CORRECTNESS13_NOT_FULL_CAMPAIGN_QUALIFICATION',built=c.ref(OUT/'configs/BUILT_PRODUCER.pending.json'),acceptance={n:c.ref(OUT/'reports'/(n+'.json')) for n in ['R1_R2_NORMAL_EQUALITY','PENDING_ACTIVE_ACCEPTANCE','OLD_FAILURE_ACCEPTANCE']},actual_cpu_attempts=13,no_new_performance_winner=True,remaining_global_cpu=3200-3009-len(starts())))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['bind','normal','active','replay','freeze']);a=p.parse_args();globals()[a.phase]()
