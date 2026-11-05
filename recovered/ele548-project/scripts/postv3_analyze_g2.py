"""Actual phase intervals and matched grouping ablation; development only."""
import collections
import csv
import statistics
from postv3_common import *
from continuation_statistics import fixed_program_bootstrap
from run_o3_public_baseline import stats

campaign=json.loads((OUT/'reports/G2.json').read_text());assert campaign['status']=='PASS'
clean=json.loads((OUT/'reports/CLEAN.json').read_text())['tasks']
C={(t['program'],t['id']):t['cycles'] for t in clean}
by={(t['program'],t['scenario'],t['owner'],t['id']):t for t in campaign['tasks']}
phase_rows=[];pairs=[];allstats={}
waits=['wait_source','wait_shadow','wait_drain','wait_response','wait_retire']
diffs=waits+['fallback_predictions','squashed_restores','stale_training','drains','cancelled','retried',
             'training_calls','allocation_requests','squash_calls','correction_calls']
def qualified(t,row):
    return int(row['count']) if t['policy']=='STAGED' else 130-int(row['refill'])
def admitted(t,row):
    if t['policy']=='STAGED':return int(row['mask'])
    if row['event']=='DRAIN_END':return 127
    if row['event']=='PROGRAM_END':return 0 if t['seu']['recovery_active'] or int(row['refill']) else 127
    return 0
for t in campaign['tasks']:
    path=ROOT/t['output'];assert sha(path/'stats.txt')==t['hashes']['stats.txt']
    allstats[t['label']]=stats(path/'stats.txt')
    if t['id']=='P0':continue
    log=list(csv.DictReader((path/'events.csv.phases.csv').open()));opened=None
    for row in log:
        if row['event']=='DRAIN_START':
            assert opened is None,('UNCLOSED_PHASE',t['label']);opened=row
        elif row['event'] in ['DRAIN_END','DRAIN_ABORT','PROGRAM_END'] and opened is not None:
            item=dict(program=t['program'],scenario=t['scenario'],owner=t['owner'],variant=t['id'],
                phase=opened['reason'],epoch=int(opened['epoch']),start_tick=int(opened['tick']),
                end_tick=int(row['tick']),elapsed_cycles=(int(row['tick'])-int(opened['tick']))/500,
                mask_before=admitted(t,opened),mask_after=admitted(t,row),
                count_start=qualified(t,opened),count_end=qualified(t,row),
                inflight_start=int(opened['inflight_BI']),inflight_end=int(row['inflight_BI']),
                hot_start_raw=int(opened['hot']),hot_end_raw=int(row['hot']),
                pending_start=int(opened['pending']),pending_end=int(row['pending']),
                completion=row['event'],right_censored=row['event']=='PROGRAM_END',output=t['output'])
            item.update({key:int(row[key])-int(opened[key]) for key in diffs})
            assert all(item[w]>=0 for w in waits)
            phase_rows.append(item);opened=None
    assert opened is None,('NO_CENSOR_MARKER',t['label'])
    # Recovery work between drains is measured separately from the drains.
    # Elapsed intervals contain useful execution too; they are not lost cycles.
    segment=None;segment_name=None
    def append_segment(a,b,name,completion):
        item=dict(program=t['program'],scenario=t['scenario'],owner=t['owner'],variant=t['id'],
            phase=name,epoch=int(a['epoch']),start_tick=int(a['tick']),end_tick=int(b['tick']),
            elapsed_cycles=(int(b['tick'])-int(a['tick']))/500,
            mask_before=admitted(t,a),mask_after=admitted(t,b),count_start=qualified(t,a),count_end=qualified(t,b),
            inflight_start=int(a['inflight_BI']),inflight_end=int(b['inflight_BI']),
            hot_start_raw=int(a['hot']),hot_end_raw=int(b['hot']),pending_start=int(a['pending']),pending_end=int(b['pending']),
            completion=completion,right_censored=completion=='PROGRAM_END',output=t['output'])
        item.update({key:int(b[key])-int(a[key]) for key in diffs});phase_rows.append(item)
    for row in log:
        if row['event']=='RESET':
            if segment is not None:append_segment(segment,row,segment_name,'RESTARTED_BY_RESET')
            segment=row;segment_name='INITIAL_COMMITTED_REFILL'
        elif row['event']=='DRAIN_START':
            if segment is not None:append_segment(segment,row,segment_name,'DRAIN_REQUESTED');segment=None
        elif row['event']=='DRAIN_END' and t['policy']=='STAGED' and int(row['mask'])!=127:
            segment=row;segment_name='PARTIAL_BANK_EXECUTION'
        elif row['event']=='PROGRAM_END' and segment is not None:
            append_segment(segment,row,segment_name,'PROGRAM_END');segment=None
    ref=by[t['program'],t['scenario'],t['owner'],'P0']
    n1=by[t['program'],t['scenario'],t['owner'],'N1']
    p3=by[t['program'],t['scenario'],t['owner'],'P_3STAGE']
    A=C[t['program'],'P0'];cl=C[t['program'],t['id']]
    pairs.append(dict(program=t['program'],scenario=t['scenario'],owner=t['owner'],variant=t['id'],
        A=A,B=ref['cycles'],C=cl,D=t['cycles'],
        N1_cycles=n1['cycles'],P3_cycles=p3['cycles'],
        gain_vs_N1_pp=100*(n1['cycles']-t['cycles'])/A,
        gain_vs_P3_pp=100*(p3['cycles']-t['cycles'])/A,
        total_gain_pp=100*(ref['cycles']-t['cycles'])/A,
        clean_delta_pct=100*(cl-A)/A,fault_residual_pp=100*(t['cycles']-cl)/A,
        difference_of_differences_pp=100*((ref['cycles']-A)-(t['cycles']-cl))/A,
        scheduled_events=t['seu']['scheduled_events'],applied_events=t['seu']['applied_events'],
        censored_future_events=t['seu']['unapplied_future_events'],
        conditional_mispredictions=allstats[t['label']]['system.cpu.branchPred.mispredicted_0::DirectCond'],
        fallback_predictions=t['seu']['fallback_predictions'],drains=t['seu']['drains_completed'],
        drain_counter_calls=t['seu']['drain_hold_cycles'],detected_words=t['seu']['detected'],
        resets=t['seu']['reset_refill'],end_phi_mismatch_words=t['seu']['fold_phi_mismatch_words'],
        end_refill_remaining=t['seu']['refill_remaining'],end_recovery_active=t['seu']['recovery_active'],
        end_ready_mask=t['seu']['staged_ready_mask'] if t['policy']=='STAGED' else 0 if t['seu']['recovery_active'] or t['seu']['refill_remaining'] else 127,
        end_qualified_count=t['seu']['staged_count'] if t['policy']=='STAGED' else 130-t['seu']['refill_remaining'],
        logical_storage_bits=t['total_bits'],source=t['output']))
summaries=[]
for variant in [v['id'] for v in variants]:
    for scenario in ['SBU_SINGLE','CHARM_6T']:
        rr=[r for r in pairs if r['variant']==variant and r['scenario']==scenario]
        group={p:[r['gain_vs_N1_pp'] for r in rr if r['program']==p] for p in sorted({r['program'] for r in rr})}
        summary=dict(variant=variant,scenario=scenario,gain_vs_N1_pp=fixed_program_bootstrap(group,10000,8171026),
            per_program={p:dict(mean=statistics.mean(v),n=len(v)) for p,v in group.items()})
        summaries.append(summary)
write(OUT/'reports/G2_ANALYSIS.json',dict(status='ACTUAL_DEVELOPMENT_ANALYSIS_NOT_HOLDOUT',summaries=summaries,
    pairs=pairs,phase_intervals=len(phase_rows),failure_count=0,
    caveat='Four design-only owners per program/scenario; exploratory CI, not workload population or a precision guarantee. Unique wait reasons overlap between fetch and retirement and are not an additive CPI breakdown.'))
for name,rr in [('RECOVERY_PHASE_COST.csv',phase_rows),('PROMOTION_ABLATION.csv',pairs)]:
    with (OUT/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
print('G2 actual matched analysis',len(pairs),'pairs and',len(phase_rows),'phase intervals')
for r in summaries:print(r['variant'],r['scenario'],r['gain_vs_N1_pp']['mean'],r['gain_vs_N1_pp']['CI95'])
