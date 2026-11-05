"""Aggregate only executed evidence; failures retain empty cycle estimands."""
from v5_common import ROOT,write,sha
from v5_statistics import metrics,paired_interval,poisson_window
from pathlib import Path
import csv,json,statistics,collections,math,sys
from run_o3_public_baseline import stats
PARTIAL='--partial' in sys.argv
FINAL=ROOT/'rate_state_v5/results';FINAL.mkdir(exist_ok=True)
R4=ROOT/'rate_state_v5/runtime';R5=ROOT/'rate_state_v5/runtime_r5'

def read(p):return json.loads(p.read_text())
def table(name,rows,schema=None):
    if not rows:
        if schema:
            with (FINAL/name).open('w') as f:csv.DictWriter(f,fieldnames=schema).writeheader()
        else:(FINAL/name).unlink(missing_ok=True) # Never retain a stale older cohort's CSV.
        return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with (FINAL/name).open('w') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def rows(folder,name):
    p=folder/'reports'/(name+'.json')
    if not p.exists():return []
    d=read(p)
    if PARTIAL and d['status'] not in ['PASS','COMPLETED_WITH_FAILED_RUNS']:return []
    assert d['status'] in ['PASS','COMPLETED_WITH_FAILED_RUNS'],(name,d['status'])
    return d['tasks']

def casekey(r):return tuple(r.get(k) for k in ['program','scenario','owner','id','repetitions'])
if not PARTIAL:
    required=[(R4,'A_CONDITIONAL',384),(R4,'A_STRESS',162),(R4,'CLEAN',45),
      (R5,'SOURCE',180),(R5,'WHOLE',240),(R5,'SHORT_CONTROL',96),
      (R5,'PERSISTENT_CLEAN',60),(R5,'PERSISTENT_FAULT',96),(R5,'METADATA',12),
      (R5,'EVALUATION_V3_CLEAN',4),(R5,'EVALUATION_V3_FAULT',800)]
    for folder,name,count in required:
        assert (folder/'reports'/(name+'.json')).exists(),('MISSING_REQUIRED_COHORT',name)
        actual=rows(folder,name);locked=read(folder/'configs'/(name+'.lock.json'))['tasks']
        assert len(actual)==len(locked)==count,('INCOMPLETE_COHORT',name,len(actual),len(locked))
        assert len({casekey(r) for r in actual})==count,('DUPLICATE_CASE',name)
        assert {casekey(r) for r in actual}=={casekey(t) for t in locked},('FROZEN_CASE_SET_MISMATCH',name)

allrows=[];failures=[];sources=[]
for folder,cohort,cleanphase,ref in [
 (R4,'A_CONDITIONAL','CLEAN','FINITE0'),(R4,'A_STRESS','CLEAN','FINITE0'),
 (R5,'SOURCE','CLEAN','NATIVE'),(R5,'WHOLE','CLEAN','NATIVE'),(R5,'SHORT_CONTROL','CLEAN','NATIVE'),
 (R5,'PERSISTENT_FAULT','PERSISTENT_CLEAN','FINITE0'),
 (R5,'EVALUATION_FAULT','EVALUATION_CLEAN','NATIVE'),
 (R5,'EVALUATION_V2_FAULT','EVALUATION_V2_CLEAN_ALL','NATIVE'),
 (R5,'EVALUATION_V3_FAULT','EVALUATION_V3_CLEAN_ALL','NATIVE')]:
    rs=rows(folder,cohort)
    if not rs:continue
    cs=rows(folder,cleanphase);cmap={(r['program'],r['id'],r.get('repetitions')):r for r in cs}
    bmap={(r['program'],r['scenario'],r['owner'],r['id']):r for r in rs}
    sources.append(dict(path=str((folder/'reports'/(cohort+'.json')).relative_to(ROOT)),sha256=sha(folder/'reports'/(cohort+'.json')),runs=len(rs)))
    for r in rs:
        rep=r.get('repetitions');key=(r['program'],r['scenario'],r['owner'])
        b=bmap[(*key,ref)];ar=cmap[(r['program'],ref,rep)];cr=cmap[(r['program'],r['id'],rep)]
        out=dict(cohort=cohort,namespace=folder.name,program=r['program'],scenario=r['scenario'],owner=r['owner'],policy=r['id'],reference=ref,
          repetitions=rep,status=r['status'],reference_status=b['status'],A=ar['cycles'],B=b.get('cycles'),C=cr['cycles'],D=r.get('cycles'),
          normal_overhead_pct=100*(cr['cycles']/ar['cycles']-1),pair_valid=r['status']=='PASS' and b['status']=='PASS',
          applied_events=r.get('seu',{}).get('applied_events'),scheduled_events=r.get('seu',{}).get('scheduled_events'),applied_flips=r.get('seu',{}).get('applied_flips'),
          total_bits=r.get('total_bits'),output=r['output'])
        if r['status']=='PASS':
            st=stats(ROOT/r['output']/'stats.txt')
            out['bac_branch_mispredictions']=int(st['system.cpu.bac.branchMisspredict'])
            out['bac_mispredicts_per_1000_committed_insts']=1000*out['bac_branch_mispredictions']/r['instructions']
            out['unique_source_wait_cycles']=r['seu'].get('unique_waits',[None])[0]
        if out['pair_valid']:out.update(metrics(out['A'],out['B'],out['C'],out['D']))
        allrows.append(out)
        if not out['pair_valid']:failures.append(out)
table('CPU_ABCD.csv',allrows)
grouped=collections.defaultdict(list)
for r in allrows:grouped[tuple(r[k] for k in ['cohort','program','scenario','policy','reference'])].append(r)
summaries=[]
for key,rs in sorted(grouped.items()):
    valid=[r for r in rs if r['pair_valid']]
    m,lo,hi=paired_interval([r['net_gain_pp'] for r in valid])
    d=dict(zip(['cohort','program','scenario','policy','reference'],key),n_scheduled=len(rs),n_valid_pairs=len(valid),n_invalid_pairs=len(rs)-len(valid),
       mean_gain_pp=m,gain_CI_low=lo,gain_CI_high=hi,normal_overhead_pct=rs[0]['normal_overhead_pct'],
       mean_residual_pct=statistics.mean(r['residual_pct'] for r in valid) if valid else None,
       mean_residual_pp=statistics.mean(r['residual_pp'] for r in valid) if valid else None,
       mean_total_slowdown_pct=statistics.mean(r['total_slowdown_pct'] for r in valid) if valid else None,
       mean_repair_only_gain_pp=statistics.mean(r['repair_only_gain_pp'] for r in valid) if valid else None,
       mean_additional_damage_reduction_pp=statistics.mean(r['additional_damage_reduction_pp'] for r in valid) if valid else None,
       empirical_damage_p90_pp=float(__import__('numpy').quantile([r['residual_pp'] for r in valid],.90)) if valid else None,
       empirical_damage_max_pp=max(r['residual_pp'] for r in valid) if valid else None,
       helpful_fault_fraction=statistics.mean(r['D']<r['C'] for r in valid) if valid else None,
       zero_damage_fraction=statistics.mean(r['D']==r['C'] for r in valid) if valid else None,
       unapplied_or_zero_event_pairs=sum(r['applied_events']==0 for r in valid),
       performance_inference='complete paired survivors only; NOT population-qualified if any failed pair')
    summaries.append(d)
table('CPU_PAIRED_SUMMARY.csv',summaries);table('CPU_FAILED_PAIRS.csv',failures,list(allrows[0]) if allrows else ['cohort','program','scenario','owner','policy','status'])

clean=[]
for folder,phase in [(R4,'CLEAN'),(R5,'CLEAN'),(R5,'EVALUATION_V3_CLEAN_ALL')]:
    rs=rows(folder,phase)
    for r in rs:
        a=next(x for x in rs if x['program']==r['program'] and x['id']=='NATIVE')
        st=stats(ROOT/r['output']/'stats.txt')
        clean.append(dict(namespace=folder.name,clean_phase=phase,program=r['program'],policy=r['id'],cycles=r['cycles'],instructions=r['instructions'],IPC=r['IPC'],
          normal_vs_native_pct=100*(r['cycles']/a['cycles']-1),logical_bits=r['total_bits'],
          journal_requests=r['seu'].get('journal_accepted'),journal_max=r['seu'].get('journal_max_count'),
          primitive_undos=r['seu'].get('primitive_undos'),undo_packets=r['seu'].get('undo_packets'),coalesced_undos=r['seu'].get('coalesced_undo_operations'),output=r['output']))
        clean[-1]['bac_branch_mispredictions']=int(st['system.cpu.bac.branchMisspredict'])
table('REPRESENTATION_COMPARISON.csv',clean)

# Base-only physical rate arithmetic: no fake extrapolation of unsampled metadata.
conditional=[r for r in allrows if r['cohort']=='A_CONDITIONAL'];rate=[];breakeven=[]
widths={'raw':130,'path':16,'fold':200,'table':65024}
owners=read(R4/'configs/A_conditional_owners.lock.json')['owners']
for program in sorted(set(r['program'] for r in conditional)):
    H=next(x['common_horizon_cycles'] for x in owners if x['program']==program)
    for policy in ['FINITE0','PARITY64','ECC64_RMW','TMR']:
        chosen=[r for r in conditional if r['program']==program and r['policy']==policy]
        A=chosen[0]['A'];C=chosen[0]['C']
        for eta in [.1,1,10]:
            weights={k:widths[k]*(1 if k=='table' else eta) for k in widths};N=sum(weights.values())
            weighted=lambda column:sum(weights[k]*statistics.mean(r[column] for r in chosen if r['scenario']==k) for k in weights)/N
            Bbar=weighted('B');Dbar=weighted('D');incremental=(Bbar-A)-(Dbar-C)
            threshold=(C-A)/incremental if incremental>0 and C>A else None
            breakeven.append(dict(program=program,policy=policy,FF_over_SRAM_assumed=eta,normal_cycles=C-A,
              repair_gain_cycles_per_one_event=incremental,linear_mu_cross=threshold,
              interpretation='local first-order extrapolation only; not demonstrated crossing' if threshold is not None else 'no positive local crossing required/proven; inspect clean scheduling or nonpositive repair benefit',
              observed_window_cycles=H,calibration='BASE_ONLY_ASSUMPTION; added storage unknown'))
            for sigma in [1.05e-14,1.468e-14]:
                for scale in [0,.1,1,10,1e12,1e15]:
                    rbit=sigma*20/3600*scale;lam=rbit*N/2e9;mu=lam*H;p0,p1,p2=poisson_window(mu)
                    rate.append(dict(program=program,policy=policy,classification='ZERO' if scale==0 else 'LITERATURE_DEVICE_CONDITIONAL_ARITHMETIC' if scale==1 else 'ASSUMPTION_SENSITIVITY' if scale<100 else 'ACCELERATED_SURROGATE_OUTSIDE_RARE_VALIDITY',
                      sigma_cm2_bit=sigma,assumed_flux_cm2_hour=20,scale=scale,FF_over_SRAM_assumed=eta,window_cycles=H,window_seconds=H/2e9,
                      flip_rate_SRAM_bit_second=rbit,base_SBU_event_rate_second=rbit*N,event_mean_fixed_window=mu,p0=p0,p1=p1,p_ge2_unmodeled=p2,
                      zero_event_cycles_A=A,zero_event_cycles_C=C,one_uniform_event_mean_B=Bbar,one_uniform_event_mean_D=Dbar,
                      known_partial_A_cycles=p0*A+p1*Bbar,known_partial_C_cycles=p0*C+p1*Dbar,
                      known_partial_gain_cycles=p0*(A-C)+p1*(Bbar-Dbar),
                      omitted_terms='N>=2 duration/survival unknown; event timing common fixed H; added protection storage hazard unsampled; extended execution beyond H excluded',
                      validity='PARTIAL_FIXED_WINDOW_SURROGATE_NOT_EXPECTED_COMPLETION_OR_MISSION_FIT'))
table('RATE_REGIME_MAP.csv',rate);table('LOCAL_RATE_BREAK_EVEN.csv',breakeven)

# Repeated tasks: paired owner across R stays one statistical owner, no n multiplication.
persistent=[]
pr=[r for r in allrows if r['cohort']=='PERSISTENT_FAULT']
for r in pr:
    one=next(x for x in pr if x['program']==r['program'] and x['owner']==r['owner'] and x['policy']==r['policy'] and x['repetitions']==1)
    if r['pair_valid'] and one['pair_valid']:
        cold_D=one['D']+(r['repetitions']-1)*one['C'];cold_C=r['repetitions']*one['C']
        persistent.append(dict(program=r['program'],policy=r['policy'],owner=r['owner'],R=r['repetitions'],retained_fault_cycles=r['D'],retained_clean_cycles=r['C'],
          retained_damage_cycles=r['D']-r['C'],cold_launch_damage_cycles=cold_D-cold_C,
          cold_comparator='DERIVED full CPU/cache/allocator reset launches; not isolated predictor-reset CPU experiment'))
table('PERSISTENT_CPU_DAMAGE.csv',persistent)
write(FINAL/'ANALYSIS.lock.json',dict(status='INTERIM_COMPLETED_COHORTS_ONLY' if PARTIAL else 'MEASURED_AGGREGATION',reports=sources,paired_bootstrap=dict(seed=3515480000,draws=10000,CI=.95),
 schema='A clean reference; B fault reference; C clean policy; D fault policy. B-D total net includes normal scheduling; repair-only is difference of differences.',
 difference_of_differences='additional damage reduction includes representation susceptibility, exposure and timing interactions; legacy repair_only field is not an isolated repair-mechanism estimate.',
 no_failed_run_imputation=True,physical='No fabricated PPA/FIT or target rate. R28 audit partial.',rows=len(allrows),failed_pairs=len(failures)))
print('Actual ABCD',len(allrows),'paired summaries',len(summaries),'rate rows',len(rate),'invalid pairs',len(failures))
