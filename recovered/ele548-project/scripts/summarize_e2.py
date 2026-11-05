#!/usr/bin/env python3
"""Matched fixed-workload trial uncertainty, preserving helpful and zero faults."""
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def wilson(k,n):
    z=1.959963984540054;d=1+z*z/n;mid=(k/n+z*z/(2*n))/d
    half=z*math.sqrt(k/n*(1-k/n)/n+z*z/(4*n*n))/d
    return [mid-half,mid+half]

def main():
    c=json.loads((ROOT/'configs/e2.holdout.lock.json').read_text());report=json.loads((ROOT/'reports/E2_CAMPAIGN.json').read_text())
    assert report['status']=='PASS_FIXED_HOLDOUT_E2' and report['config_sha256']==sha(ROOT/'configs/e2.holdout.lock.json')
    path=ROOT/report['trial_CSV'];assert report['trial_CSV_sha256']==sha(path)
    with path.open() as f:rows=list(csv.DictReader(f))
    groups={}
    for r in rows:
        if r['model']=='ZERO':continue
        profile=c['K_profiles'][r['model'].split('__')[0]];mean_k=(profile['1']+2*profile['2'])/(profile['1']+profile['2'])
        rate=float(r['event_rate_per_conditional'])
        if r['mode']=='repeat':
            if r['population']=='storage_scaled_full':rate*=65370/int(r['exposed_bits'])
            if r['model'].endswith('equal_expected_flip'):rate*=mean_k
            reference=min(c['base_event_rates_per_conditional'],key=lambda a:abs(a-rate));assert math.isclose(reference,rate,rel_tol=1e-10)
        else:reference=None
        key=(r['mode'],r['model'],r['population'],int(r['field']),reference)
        groups.setdefault(key,[]).append(r)
    rng=np.random.default_rng(c['bootstrap_seed']);summary=[]
    for key,data in sorted(groups.items(),key=lambda kv:str(kv[0])):
        by={(r['workload'],r['scheme'],int(r['trial'])):r for r in data}
        n=c['single_trials_per_workload_selected_field'] if key[0]=='single' else c['repeat_trials_per_workload_condition']
        indices=rng.integers(0,n,size=(2000,len(c['workloads']),n))
        items={}
        for scheme in c['schemes']:
            selected=[by[(w,scheme,i)] for w in c['workloads'] for i in range(n)]
            metrics={}
            for metric in ['net','delta_MPKI','harm','help','detected','corrected','due','reset_refill','fallback_predictions','end_differing_base_bits','event_count','flip_count','selected_payload_flips','extra_storage_flips']:
                a=np.array([[float(by[(w,scheme,i)][metric]) for i in range(n)] for w in c['workloads']])
                draws=np.stack([a[j,indices[:,j,:]].mean(axis=1) for j in range(len(c['workloads']))],axis=1).mean(axis=1)
                metrics[metric]={'mean':float(a.mean()),'trial_bootstrap_95CI':np.quantile(draws,[.025,.975]).tolist()}
            # Matched seed/trial difference; for storage_scaled the same RNG seed
            # does not mean same event counts/sites, stated in the group contract.
            effect=np.array([[float(by[(w,scheme,i)]['delta_MPKI'])-float(by[(w,'P0',i)]['delta_MPKI']) for i in range(n)] for w in c['workloads']])
            draws=np.stack([effect[j,indices[:,j,:]].mean(axis=1) for j in range(len(c['workloads']))],axis=1).mean(axis=1)
            metrics['delta_MPKI_difference_from_P0']={'mean':float(effect.mean()),'matched_trial_bootstrap_95CI':np.quantile(draws,[.025,.975]).tolist()}
            harmful=sum(int(r['net'])>0 for r in selected)
            items[scheme]={'trials':len(selected),'metrics':metrics,'net_harm_probability':harmful/len(selected),
                           'net_harm_Wilson95CI':wilson(harmful,len(selected)),
                           'helpful_trials':sum(int(r['net'])<0 for r in selected),'zero_net_trials':sum(int(r['net'])==0 for r in selected),
                           'endpoint_base_difference_fraction':sum(int(r['end_differing_base_bits'])!=0 for r in selected)/len(selected)}
        summary.append({'mode':key[0],'model':key[1],'population':key[2],'field':key[3],'base_reference_rate_per_conditional':key[4],
                        'event_pairing':'identical event times/sites' if key[2]!='storage_scaled_full' else 'matched seeds, scheme-scaled population/rate changes event times/sites',
                        'schemes':items})
    result={'status':'PASS_FIXED_HOLDOUT_E2_SUMMARY','scope_id':c['scope_id'],'scope_sha256':c['scope_sha256'],
            'campaign_sha256':sha(ROOT/'reports/E2_CAMPAIGN.json'),'config_sha256':sha(ROOT/'configs/e2.holdout.lock.json'),
            'successful_trials':len(rows),'execution_failures':len(report['failures']),'groups':summary,'bootstrap_replicates':2000,
            'CI_boundary':'fixed six workloads, trial/seed randomness only; matched trial bootstrap within workload; no branch-level independence or unseen-workload inference',
            'rate_boundary':c['rate_status'],'CPU_cycles_IPC_measured':False,'RTL_latency_measured':False,
            'limitations':c['limitations']+['Logical word/field mappings differ by experiment; no measured predictor geometry or replica separation.',
                'Detector counters report performed correction/vote operations, not oracle truth. >=3 SECDED errors and same-bit >=2 TMR copies can silently fail.',
                'Last prediction divergence is not proof of permanent recovery; endpoint state differences are horizon-censored observations.',
                'Storage access counters are logical operation proxies, not transistor toggles or measured energy.',
                'Full-population events mostly affect unprotected state. Fixed n=10 per workload/condition can have wide uncertainty for rare S* or extra-cell hits.']}
    (ROOT/'reports/E2_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    figdir=ROOT/'reports/e2/figures';figdir.mkdir(parents=True,exist_ok=True)
    selected=[g for g in summary if g['mode']=='single'];fig,axes=plt.subplots(1,2,figsize=(9,3.8))
    for ax,g in zip(axes,sorted(selected,key=lambda g:g['field'])):
        m=[g['schemes'][s]['metrics']['delta_MPKI'] for s in c['schemes']];a=np.array([x['mean'] for x in m]);ci=np.array([x['trial_bootstrap_95CI'] for x in m]);
        ax.bar(c['schemes'],a,color=['#6c7585','#d6a54d','#267ab4','#4f9e72']);ax.errorbar(range(4),a,yerr=np.maximum(0,np.array([a-ci[:,0],ci[:,1]-a])),fmt='none',color='black',capsize=3)
        ax.axhline(0,color='gray',lw=.7);ax.set_title('raw/path history' if g['field']==4 else 'folded history');ax.set_ylabel('Paired change in MPKI');ax.tick_params(axis='x',rotation=20)
    fig.suptitle('E2: one SBU in selected payload; 100k conditional followup');fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(figdir/f'single_recovery.{ext}',dpi=180)
    plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4),sharey=False)
    for ax,pop in zip(axes,c['repeat_populations']):
        for i,scheme in enumerate(c['schemes']):
            points=[g for g in summary if g['mode']=='repeat' and g['model']=='M1_CHARM_6T__equal_event' and g['population']==pop];points.sort(key=lambda g:g['base_reference_rate_per_conditional'])
            x=np.array([g['base_reference_rate_per_conditional'] for g in points]);m=[g['schemes'][scheme]['metrics']['delta_MPKI'] for g in points]
            a=np.array([p['mean'] for p in m]);ci=np.array([p['trial_bootstrap_95CI'] for p in m])
            ax.errorbar(x*(1+.035*(i-1.5)),a,yerr=np.maximum(0,np.array([a-ci[:,0],ci[:,1]-a])),marker='o',label=scheme,capsize=3)
        ax.set_xscale('log');ax.set_title(pop.replace('_',' '));ax.set_xlabel('Base reference events / conditional');ax.set_ylabel('Change in MPKI');ax.axhline(0,color='gray',lw=.7)
    axes[0].legend(fontsize=8);fig.suptitle('E2: CHARM 6T K profile; software stress rates');fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(figdir/f'repeat_populations.{ext}',dpi=180)
    plt.close(fig)
    lines=['# E2 holdout 보호 비교 — 2026-10-12','',
           f"실제 HW1 trace 6개의 분리된 holdout에서 {len(rows)} trials를 완료했다. Execution failure {len(report['failures'])}. 동결된 S*는 `E1_SSTAR_V1`, raw/path + folded history 346 bits/23 words다. CPU cycles·IPC는 이 결과에 포함되지 않으며 gem5 E3에서 별도 실행한다.",'',
           '## 단일 SBU — 같은 payload bit/time의 네 설계 비교','',
           '| Field | Scheme | 평균 ΔMPKI (95% trial bootstrap CI) | 평균 net extra misses |','|---|---|---:|---:|']
    for g in sorted(selected,key=lambda g:g['field']):
        for s in c['schemes']:
            m=g['schemes'][s]['metrics'];a=m['delta_MPKI'];lo,hi=a['trial_bootstrap_95CI']
            lines.append(f"| {'raw/path' if g['field']==4 else 'folded'} | {s} | {a['mean']:.6g} [{lo:.6g}, {hi:.6g}] | {m['net']['mean']:.4g} |")
    lines+=['','SECDED/TMR의 selected payload SBU 결과는 정상 정정의 검증이다. Added parity/check/controller/replica bit 노출은 별도 storage_scaled_full 결과에 포함했다. Parity는 검출 후 해당 history를 초기화하고 tagged provider를 제외해 130 actual control updates 동안 bimodal로 예측한다. SECDED DUE도 동일 fallback을 사용한다. Tagged counter/tag는 fallback 동안 학습·할당하지 않으며 원래 usefulness aging은 유지한다.','',
            '## 반복 주입과 한계','',
            'Poisson gap에 CHARM 6T(205:9), 8T(142:5) K=1/2 분포를 각각 mark했다. 같은 사건율과 같은 기대 flip 수를 별도로 비교했다. 시간 단위는 conditional-branch exposure이며 1e-4/1e-3은 소프트웨어 stress rate다. 실제 target per-bit/second SEU rate로 보고하지 않는다.','',
            'selected_payload는 S*의 조건부 민감도, paired_base_full은 같은 전체 core 사건, storage_scaled_full은 추가 보호 저장 bit까지 같은 per-bit density에 노출하는 비교다. Added storage를 포함하면 설계마다 bit 수와 event count/site가 달라지므로 동일 사건으로 설명하지 않는다. 현재 MCU anchor는 logical sensitivity이며 실측 predictor geometry가 아니다.','',
            '보호기에는 injector event/K 또는 golden prediction/state를 제공하지 않았다. 모든 event가 atomic unique bits이며 모든 같은-bin 사건을 순서대로 적용한다. 한 trial 시작 때만 warmup으로 reset하고 반복 사건 사이에는 reset하지 않는다. Harm/help/zero는 모두 보존했다. Net>0는 predictor loss outcome이지 architectural failure/SDC가 아니다.','',
            'Decoder 이상의 오류도 실제 law로 처리한다: parity의 even-error miss, SECDED의 3-bit miscorrection/4-bit undetected case, TMR의 같은 bit 두 사본 majority failure가 correctness test에서 확인됐다. 인공적으로 성공 처리하지 않았다.','',
            '95% CI는 고정된 6개 workload 내 matched trial/seed bootstrap 2000회다. Branch를 독립 trial로 간주하지 않으며 새로운 프로그램 모집단/mission rate에 대한 CI가 아니다. Full-state endpoint equality와 last divergence는 영구 회복 보장이 아니다.','',
            '## 재현과 남은 작업','',
            '`bash setup/build_e2.sh`, `.venv/bin/python scripts/run_e2.py --phase preflight`, `--phase main`, `.venv/bin/python scripts/summarize_e2.py`. 입력/source/config/binary/manifest와 trial/event CSV의 hash는 `E2_PREFLIGHT.json`, `E2_CAMPAIGN.json`, `E2_SUMMARY.json`에 있다. 최초 compile failure는 vector<bool> proxy auto deduction 문제였으며 `e2/build_attempt1.log`에 보존하고 bool 명시로 수정했다.','',
            'DONE: 세 recovery behavior, clean equivalence, added-bit enumeration/injection, fixed holdout SBU/CHARM single/repeat 비교. NOT DONE: CERN physical grouping/footprint qualification, Flying Laptop time stress 연결, gem5 CPU FI·speculation/rollback·latency sensitivity, 실제 RTL latency/PPA. Cadence와 TCAD는 실행하지 않았다.']
    lines += ['', '## 반복 CHARM 6T 예시 — 기준율 1e-3/conditional, 같은 사건율', '',
              '| Population | Scheme | 평균 ΔMPKI (95% CI) | 평균 extra-cell flips/trial |', '|---|---|---:|---:|']
    for g in summary:
        if g['mode']=='repeat' and g['model']=='M1_CHARM_6T__equal_event' and g['base_reference_rate_per_conditional']==.001:
            for s in c['schemes']:
                m=g['schemes'][s]['metrics'];a=m['delta_MPKI'];lo,hi=a['trial_bootstrap_95CI']
                lines.append(f"| {g['population']} | {s} | {a['mean']:.6g} [{lo:.6g}, {hi:.6g}] | {m['extra_storage_flips']['mean']:.4g} |")
    lines += ['', 'Full-population과 selected-population의 ΔMPKI는 서로 다른 조건부 노출이므로 그 크기를 직접 비교해 보호 우열로 설명하지 않는다. Full population의 fixed 60 trials/condition은 드문 S*/added-cell 사건에 대한 정밀도 보장이 아니며 CI를 함께 읽는다. 전체 32 조건, harm/help, 회복 동작 수와 기대 flip 수 정규화 결과는 E2_SUMMARY.json에 있다.']
    (ROOT/'reports/E2_REPORT.ko.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status':result['status'],'trials':len(rows),'groups':len(summary),'failures':len(report['failures'])},indent=2))

if __name__=='__main__':main()
