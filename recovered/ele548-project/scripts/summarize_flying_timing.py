#!/usr/bin/env python3
"""Matched detector-time pattern sensitivity; no physical-rate inference."""
import json
import hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    c=json.loads((ROOT/'configs/flying_timing.lock.json').read_text());report=json.loads((ROOT/'reports/FLYING_TIMING_MAIN.json').read_text())
    assert report['status']=='PASS_FIXED_DETECTION_TIMING_STRESS' and report['successful_trials']==c['main_trials'] and report['config_sha256']==sha(ROOT/'configs/flying_timing.lock.json')
    by={(r['workload'],r['duplicate_policy'],r['timing_model'],r['K_profile'],r['scheme'],r['trial']):r for r in report['tasks']}
    n=c['trials_per_workload_condition'];rng=np.random.default_rng(c['bootstrap_seed']);groups=[]
    def uncertainty(a,index):
        draws=np.stack([a[j,index[:,j,:]].mean(axis=1) for j in range(len(c['workloads']))],axis=1).mean(axis=1)
        return {'mean':float(a.mean()),'matched_trial_bootstrap95CI':np.quantile(draws,[.025,.975]).tolist()}
    for policy in c['duplicate_policies']:
        for profile in c['K_profiles']:
            index=rng.integers(0,n,size=(2000,len(c['workloads']),n))
            for timing in c['timing_models']:
                for scheme in c['schemes']:
                    data=np.array([[float(by[(w,policy,timing,profile,scheme,i)]['metrics']['delta_MPKI']) for i in range(n)] for w in c['workloads']])
                    control=np.array([[float(by[(w,policy,'conditional_Poisson_fixed_N',profile,scheme,i)]['metrics']['delta_MPKI']) for i in range(n)] for w in c['workloads']])
                    metrics={}
                    for key in ['net','harm','help','detected','corrected','DUE','reset_refill','refill_updates','fallback_predictions','end_differing_base_bits','flip_count']:
                        a=np.array([[float(by[(w,policy,timing,profile,scheme,i)]['metrics'][key]) for i in range(n)] for w in c['workloads']]);metrics[key]=uncertainty(a,index)
                    groups.append({'policy':policy,'profile':profile,'timing':timing,'scheme':scheme,'trials':len(c['workloads'])*n,'delta_MPKI':uncertainty(data,index),
                        'delta_MPKI_difference_from_fixed_N_Poisson':uncertainty(data-control,index),'metrics':metrics})
    result={'status':'PASS_DETECTION_TIME_SENSITIVITY_SUMMARY','config_sha256':sha(ROOT/'configs/flying_timing.lock.json'),'campaign_sha256':sha(ROOT/'reports/FLYING_TIMING_MAIN.json'),
        'source_record_counts':{'collapse':2055,'preserve':2129,'duplicate_extra_rows':74},'source_records_are_physical_SEU_events':False,
        'source_count_or_gaps_are_MCU_size':False,'target_per_bit_second_rate':None,'workload_boundary':'fixed six real HW1 holdout intervals, same 100k conditional exposure, original instruction denominator',
        'uncertainty_boundary':'source detection-time series fixed; bootstrap matched trial within workload for anchor/mark/shuffle randomness, not physical SEU flux or unseen workload uncertainty',
        'groups':groups,'limitations':['compressed detection timestamps not particle timestamps','live exposure/detection cadence/sensitive-bit population unknown','two K marginals independent hypothesis, not a measured joint dataset','selected-payload conditional stress; extra storage/radiation to other CPU state excluded here','zero-latency non-spec behavioral model; CPU/RTL results separate']}
    (ROOT/'reports/FLYING_TIMING_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    out=ROOT/'reports/flying_timing/figures';out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(11,4));timings=c['timing_models'];x=np.arange(3)
    for ax,profile in zip(axes,c['K_profiles']):
        for scheme in c['schemes']:
            items=[next(g for g in groups if g['policy']=='collapse' and g['profile']==profile and g['timing']==timing and g['scheme']==scheme) for timing in timings]
            y=np.array([g['delta_MPKI']['mean'] for g in items]);ci=np.array([g['delta_MPKI']['matched_trial_bootstrap95CI'] for g in items]);ax.errorbar(x,y,yerr=np.maximum(0,np.array([y-ci[:,0],ci[:,1]-y])),marker='o',label=scheme,capsize=3)
        ax.set_xticks(x,['Observed gaps','Permuted gaps','Fixed-N Poisson']);ax.set_ylabel('Change in MPKI');ax.set_title(profile.replace('_',' '));ax.axhline(0,color='gray',lw=.7)
    axes[0].legend(fontsize=8);fig.suptitle('Flying Laptop detection-time ordering stress; timestamps collapsed');fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(out/f'detection_time_sensitivity.{ext}',dpi=180)
    plt.close(fig)
    lines=['# Flying Laptop 검출시간 패턴 시험 — 2026-10-12','',f"고정한 {report['successful_trials']} trials를 완료했다. 실행 실패 0. 실제 HW1 holdout 6개, 100k conditional 관측창, 동결 S* raw/path+folded 346 bits와 네 보호법을 사용했다.",'',
        'SOURCE FACT: 2129 raw rows, 2055 distinct timestamps/complete records, 74 duplicate extra rows. 이 데이터는 검출 기록이며 independent particle strike/MCU grouping/target bit rate를 식별하지 않는다.','',
        'NEW DERIVATION / ASSUMPTION: 각 source stream을 동일 100k conditional exposure로 압축해 원래 gap 순서, gap permutation, 같은 N의 homogeneous Poisson 조건부 uniform-time 대조를 비교했다. 이 압축 시간은 실제 CPU seconds가 아니다. Per-bit/second rate나 mission FIT를 추정하지 않는다.','',
        'Marks는 SBU 가정과 CHARM 6T 독립 K 가설을 따로 사용했다. 서로 다른 데이터셋의 marginals를 결합하는 가설이며 Flying Laptop이 MCU K를 측정했다고 표시하지 않는다. Duplicate preserve는 추가 hypothetical arrivals의 정책 민감도이고 중복 rows를 MCU의 K로 바꾸지 않았다. Unique occurrence0에는 양 정책에서 같은 mark를 부여했다.','',
        '## Collapsed timestamps — 같은 수의 기록에서 시간 순서 차이','',
        '| K 가설 | Scheme | Observed ΔMPKI | Permuted ΔMPKI | Fixed-N Poisson ΔMPKI | Observed−Poisson (95% CI) |','|---|---|---:|---:|---:|---:|']
    for profile in c['K_profiles']:
        for scheme in c['schemes']:
            vals=[next(g for g in groups if g['policy']=='collapse' and g['profile']==profile and g['timing']==timing and g['scheme']==scheme) for timing in timings]
            a=vals[0]['delta_MPKI_difference_from_fixed_N_Poisson'];lo,hi=a['matched_trial_bootstrap95CI']
            lines.append('| '+profile+' | '+scheme+' | '+' | '.join(f"{g['delta_MPKI']['mean']:.6g}" for g in vals)+f" | {a['mean']:.6g} [{lo:.6g}, {hi:.6g}] |")
    lines += ['', 'CI는 고정 source stream·workloads에 조건화한 matched seed bootstrap 2000회다. Source series의 관측누락/검출 cadence/물리 SEU-process 불확실성을 해결하지 않는다. Harm/help/zero를 보존했으며 원 instruction denominator로 ΔMPKI를 계산한다. 개별 branch를 독립 trial로 세지 않는다.','',
        'Extra parity/check/replica/controller bit 노출은 E2/E3의 별도 storage-scaled 비교에 포함하며, 이 timing 시험은 같은 selected payload를 대상으로 한다. 실제 latency·speculation/CPU performance·PPA는 이 C++ 결과로 주장하지 않는다.','',
        '## 재현','',
        '`build/scheduled`는 external sorted event times와 unique logical IDs를 읽는다. 동일 좌표의 distinct event들을 순서대로 모두 적용하며 한 trial 시작 이후 사건 간 reset하지 않는다. RNG는 protection과 독립이고 전체 event/K/site/time/seed 및 각 trial의 hash/card/log/CSV를 보존했다.','',
        '`scripts/run_flying_timing.py --phase pilot/main`, `scripts/summarize_flying_timing.py`, `configs/flying_timing.lock.json`. Main count 산술 표기 1440→2880은 main outcome 전에 corrected 했다. 최초 plan assertion과 이전 config/pilot는 reports/flying_timing에 보존했고 동일 48-run pilot을 다시 통과했다. 계획에 지정한 각 조건/seed 수를 바꾸지 않았다.']
    (ROOT/'reports/FLYING_TIMING_REPORT.ko.md').write_text('\n'.join(lines)+'\n')
    (ROOT/'data/curated/flying_timing_model_card.json').write_text(json.dumps({k:v for k,v in result.items() if k!='groups'},indent=2)+'\n')
    print('PASS paired detection-time shape sensitivity with physical-rate limits')
if __name__=='__main__':main()
