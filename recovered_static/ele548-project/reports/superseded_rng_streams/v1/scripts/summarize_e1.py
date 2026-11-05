#!/usr/bin/env python3
"""Stratified trial-level E1 inference and frozen design scope, no holdout fit."""
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


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def wilson(n_positive,n,z=1.959963984540054):
    p=n_positive/n;scale=1+z*z/n
    center=(p+z*z/(2*n))/scale
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    return [center-radius,center+radius]


def interval(x):return [float(np.quantile(x,.025)),float(np.quantile(x,.975))]


def main():
    config_path=ROOT/'configs/e1.design.lock.json';c=json.loads(config_path.read_text())
    campaign=json.loads((ROOT/'reports/E1_CAMPAIGN.json').read_text())
    assert campaign['status']=='PASS_FIXED_DESIGN_E1_CAMPAIGN'
    assert campaign['config_sha256']==sha(config_path)
    csv_path=ROOT/campaign['trial_CSV'];assert sha(csv_path)==campaign['trial_CSV_sha256']
    with csv_path.open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==5760 and all(r['status']=='PASS' for r in rows)
    fields=c['fields'];workloads=c['workloads'];models=list(c['K_profiles'])
    manifest=json.loads((ROOT/'sources/predictor_logical_state_manifest.json').read_text())
    bit_counts=manifest['bits_by_field'];total=manifest['total_bits']
    rng=np.random.default_rng(c['bootstrap_seed']);B=c['bootstrap_replicates']
    summaries=[];by_workload=[];boot_by_model={};field_by_model={}
    for model in models:
        model_summary=[];boots={}
        for field in fields:
            subset=[r for r in rows if r['model']==model and r['field']==field]
            pooled={};bootstrap={}
            for metric in ['harm','help','net','delta_MPKI']:
                means=[];rep=np.zeros(B)
                for workload in workloads:
                    data=np.array([float(r[metric]) for r in subset if r['workload']==workload])
                    means.append(float(data.mean()))
                    draw=rng.integers(0,len(data),size=(B,len(data)))
                    rep+=data[draw].mean(axis=1)/len(workloads)
                pooled[metric]=float(np.mean(means));bootstrap[metric]=rep
            boots[field]=bootstrap['delta_MPKI']*bit_counts[field]/total
            impacted=sum(int(r['harm'])+int(r['help'])>0 for r in subset)
            summary={'model':model,'field':field,'trials':len(subset),'bits':bit_counts[field],
                     'bit_exposure_weight':bit_counts[field]/total,'mean_harm':pooled['harm'],'mean_help':pooled['help'],
                     'mean_net_extra_misses':pooled['net'],'net_CI95':interval(bootstrap['net']),
                     'mean_delta_MPKI':pooled['delta_MPKI'],'delta_MPKI_CI95':interval(bootstrap['delta_MPKI']),
                     'bit_weighted_delta_MPKI':pooled['delta_MPKI']*bit_counts[field]/total,
                     'bit_weighted_delta_MPKI_CI95':interval(boots[field]),
                     'prediction_divergent_trials':impacted,'prediction_divergence_fraction':impacted/len(subset),
                     'observed_semantic_equal_at_H_fraction':sum(r['observed_semantic_equal_100000']=='1' for r in subset)/len(subset),
                     'not_equal_at_H_fraction':sum(r['observed_semantic_equal_100000']=='0' for r in subset)/len(subset),
                     'max_harm_observed':max(int(r['harm']) for r in subset),
                     'K2_trials':sum(r['multiplicity']=='2' for r in subset),
                     'cumulative_mean_net':{str(h):float(np.mean([int(r[f'net_{h}']) for r in subset])) for h in c['cumulative_checkpoints']}}
            model_summary.append(summary);summaries.append(summary)
            for workload in workloads:
                sample=[r for r in subset if r['workload']==workload]
                values=np.array([float(r['delta_MPKI']) for r in sample])
                rep=values[rng.integers(0,len(values),size=(B,len(values)))].mean(axis=1)
                effect=sum(int(r['harm'])+int(r['help'])>0 for r in sample)
                by_workload.append({'model':model,'field':field,'workload':workload,'trials':len(sample),
                    'mean_net':float(np.mean([int(r['net']) for r in sample])),'mean_delta_MPKI':float(values.mean()),
                    'delta_MPKI_CI95':interval(rep),'prediction_divergent_trials':effect,'divergence_Wilson95':wilson(effect,len(sample)),
                    'remaining_state_trials':sum(r['observed_semantic_equal_100000']=='0' for r in sample),
                    'no_prediction_effect_but_remaining_state_trials':sum(int(r['harm'])+int(r['help'])==0 and r['observed_semantic_equal_100000']=='0' for r in sample)})
        boot_by_model[model]=boots;field_by_model[model]=model_summary
    primary=field_by_model['M0']
    ranking=sorted(primary,key=lambda x:(-x['bit_weighted_delta_MPKI'],fields.index(x['field'])))
    selected=[x['field'] for x in ranking[:2]]
    matrix=np.column_stack([boot_by_model['M0'][f] for f in fields])
    top=np.argsort(-matrix,axis=1,kind='stable')[:,:2]
    top2_probability={f:float(np.any(top==i,axis=1).mean()) for i,f in enumerate(fields)}
    for item in primary:item['bootstrap_top2_fraction']=top2_probability[item['field']]
    per_event_ranking=[x['field'] for x in sorted(primary,key=lambda x:(-x['mean_delta_MPKI'],fields.index(x['field'])))]
    # Subfield diagnostics are conditional on the sampled subfield, not a new
    # independent campaign nor an excuse to change the frozen field-level rule.
    subfields=[]
    for field in ['raw_path','folded']:
        names=sorted({r['subfield'] for r in rows if r['model']=='M0' and r['field']==field})
        for name in names:
            sample=[r for r in rows if r['model']=='M0' and r['field']==field and r['subfield']==name]
            subfields.append({'field':field,'subfield':name,'trials':len(sample),'mean_net':float(np.mean([int(r['net']) for r in sample])),
                             'mean_delta_MPKI':float(np.mean([float(r['delta_MPKI']) for r in sample])),
                             'prediction_divergence_fraction':sum(int(r['harm'])+int(r['help'])>0 for r in sample)/len(sample)})
    # Source-profile difference: matched first 30 M0 events/time seeds. Do not
    # compare 100-sample M0 and 30-sample CHARM means as if samples were paired.
    matched=[]
    lookup={(r['model'],r['workload'],r['field'],r['trial']):r for r in rows}
    for model in models[1:]:
        for field in fields:
            difference=[];boot=np.zeros(B)
            for workload in workloads:
                values=[]
                for trial in range(30):
                    r=lookup[(model,workload,field,str(trial))];base=lookup[('M0',workload,field,str(trial))]
                    assert r['inject_offset']==base['inject_offset'] and r['instructions']==base['instructions']
                    values.append(float(r['delta_MPKI'])-float(base['delta_MPKI']))
                x=np.array(values);difference.append(float(x.mean()))
                boot+=x[rng.integers(0,len(x),size=(B,len(x)))].mean(axis=1)/len(workloads)
            matched.append({'model':model,'field':field,'pairs':180,'mean_delta_MPKI_minus_matched_M0':float(np.mean(difference)),
                            'paired_difference_CI95':interval(boot),'matching':'same injection times, K-dependent valid logical anchors'})
    warmup_sensitivity=[]
    preflight=json.loads((ROOT/'reports/E1_PREFLIGHT.json').read_text())
    for w in preflight['warmup']:
        if w['stability_400k_vs_500k']:continue
        path=ROOT/'reports/e1/warmup_sensitivity'/f"{w['workload']}.M0.csv"
        assert path.exists(), 'finish flagged warmup sensitivity before scope report'
        with path.open() as f:alternative=list(csv.DictReader(f))
        assert len(alternative)==600 and all(r['status']=='PASS' for r in alternative)
        alternative_scores=[]
        for field in fields:
            sample=[r for r in alternative if r['field']==field]
            assert len(sample)==100
            for r in sample:
                base=lookup[('M0',w['workload'],field,r['trial'])]
                assert r['inject_offset']==base['inject_offset'] and r['event_site_ids']==base['event_site_ids'] and r['instructions']==base['instructions']
            new_mean=float(np.mean([float(r['delta_MPKI']) for r in sample]))
            old_mean=next(x['mean_delta_MPKI'] for x in by_workload if x['model']=='M0' and x['field']==field and x['workload']==w['workload'])
            primary_mean=next(x['mean_delta_MPKI'] for x in primary if x['field']==field)
            score=(primary_mean+(new_mean-old_mean)/len(workloads))*bit_counts[field]/total
            alternative_scores.append({'field':field,'alternate_trace_mean_delta_MPKI':new_mean,'primary_trace_mean_delta_MPKI':old_mean,
                                       'global_score_with_alternate_trace':score})
        order=sorted(alternative_scores,key=lambda x:(-x['global_score_with_alternate_trace'],fields.index(x['field'])))
        warmup_sensitivity.append({'workload':w['workload'],'paired_trials':600,'warmup':400000,
                                   'CSV':str(path.relative_to(ROOT)),'sha256':sha(path),'fields':alternative_scores,
                                   'top2_with_alternate_warmup':[x['field'] for x in order[:2]],
                                   'selected_set_unchanged':set(x['field'] for x in order[:2])==set(selected)})
    # Concrete codeword payload boundary for all three E2 schemes. Natural
    # source registers; tagged selected fields share their (bank,row) word.
    sites=[json.loads(line) for line in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
    words={}
    for site in sites:
        if site['field'] not in selected:continue
        field=site['field'];bank=site['bank'];row=site['row']
        key=f'tagged:{bank}:{row}' if field in ['ctr','tag','u'] else (f'raw_path:{bank}' if field=='raw_path' else f'{field}:{bank}:{row}')
        words.setdefault(key,[]).append(site['site_id'])
    payload=sum(len(ids) for ids in words.values())
    assert payload==sum(bit_counts[f] for f in selected)
    ecc_extra=0
    for ids in words.values():
        r=0
        while 2**r<len(ids)+r+1:r+=1
        ecc_extra+=r+1
    scope={'schema_version':1,'status':'FROZEN_DESIGN_SCOPE_FOR_E2_NOT_A_PROTECTION_RESULT','scope_id':'E1_SSTAR_V1',
           'selected_fields':selected,'payload_bits':payload,'bits_by_selected_field':{f:bit_counts[f] for f in selected},
           'payload_word_count':len(words),'payload_words':[{'word_id':key,'site_ids':ids,'payload_bits':len(ids)} for key,ids in sorted(words.items())],
           'schemes':['P0','P_ED','P_ECC','P_TMR'],'word_boundary':'natural raw/path/fold registers; tagged selected payload fields grouped by bank,row; widths unchanged',
           'codec_storage_counts_before_controller_metadata':{'parity_bits':len(words),'SECDED_check_bits':ecc_extra,'TMR_extra_replica_bits':2*payload},
           'extra_state_exposure':'E2 must add/check/replica/valid/controller state manifest; counts above are not implemented storage or PPA',
           'physical_mapping':None,'selected_using':'locked M0 design scores only, signed bit-weighted mean delta MPKI',
           'design_config_sha256':sha(config_path),'campaign_sha256':sha(ROOT/'reports/E1_CAMPAIGN.json'),
           'holdout_windows':'reports/E1_WORKLOAD_WINDOWS.json','holdout_performance_evaluated':False,
           'uncertainty':'estimated scope selection with rank uncertainty; no claim of a statistically separated universal winner',
           'warmup_condition':'full available 500k prefix, finite-trace design condition; SHORT-INT-1 clean warmup sensitivity remains explicitly reported'}
    scope_path=ROOT/'sources/protection_scope.lock.json';scope_path.write_text(json.dumps(scope,indent=2)+'\n')
    report={'status':'PASS_E1_FIXED_DESIGN_CAMPAIGN_AND_SCOPE_FREEZE','config_sha256':sha(config_path),
            'campaign':campaign,'models':summaries,'by_workload_field':by_workload,'subfield_diagnostics':subfields,
            'matched_CHARM_difference':matched,'selection':{'primary_model':'M0','fields':selected,'payload_bits':payload,
                'rule':c['scope_selection_rule'],'bit_weighted_field_ranking':[x['field'] for x in ranking],
                'per_event_field_ranking':per_event_ranking,'bootstrap_top2_fraction':top2_probability,
                'scope_path':str(scope_path.relative_to(ROOT)),'scope_sha256':sha(scope_path)},
            'warmup':{'preflight_stability':preflight['stability'],'sensitivity':warmup_sensitivity},
            'source_K_uncertainty':{'6T_p2_Wilson95':wilson(9,214),'8T_p2_Wilson95':wilson(5,147),
                                     'policy':'source fitting uncertainty reported separately; no claim FI bootstrap includes it'},
            'statistical_contract':'2000 workload-stratified event-trial bootstrap; conditional on six fixed traces; no branch-level independence, no optional stopping',
            'limits':['no CPU cycles/IPC or hardware PPA','no physical adjacency or target absolute rate',
                      'same-program disjoint windows are not independent application validation','sampled endpoint state equality is not permanent recovery',
                      'CHARM K>=3 unobserved is not impossible','source/assumed exposure and snapshot slack exclusions retained'],
            'holdout_performance_evaluated':False}
    (ROOT/'reports/E1_SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
    figdir=ROOT/'reports/e1/figures';figdir.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(12,4.2),layout='constrained')
    for ax,key,ci_key,title in [(axes[0],'mean_net_extra_misses','net_CI95','Conditional severity per SBU event'),
                               (axes[1],'bit_weighted_delta_MPKI','bit_weighted_delta_MPKI_CI95','Contribution under uniform bit exposure')]:
        y=np.array([x[key] for x in primary]);ci=np.array([x[ci_key] for x in primary])
        error=np.array([np.maximum(0,y-ci[:,0]),np.maximum(0,ci[:,1]-y)])
        ax.bar(fields,y,color=['#d77b28' if f in selected else '#6789ab' for f in fields]);ax.errorbar(range(6),y,yerr=error,fmt='none',ecolor='black',capsize=3)
        ax.axhline(0,color='black',lw=.7);ax.set_title(title);ax.tick_params(axis='x',rotation=25)
    axes[0].set_ylabel('Extra misses / next 100k conditional branches')
    axes[1].set_ylabel('Bit-weighted paired delta MPKI')
    fig.suptitle('Plain TAGE: six fixed HW1 traces, 100 SBU trials/field/trace\nOrange = frozen S*; 95% stratified trial-bootstrap intervals')
    fig.savefig(figdir/'state_impact.png',dpi=180);fig.savefig(figdir/'state_impact.pdf');plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
    for item in primary:ax.plot(c['cumulative_checkpoints'],list(item['cumulative_mean_net'].values()),marker='o',label=item['field'])
    ax.set_xscale('log');ax.set_xlabel('Post-event conditional branches');ax.set_ylabel('Cumulative mean extra misses');ax.legend(ncol=3)
    ax.set_title('Propagation beyond the original upset: no injected repair')
    fig.savefig(figdir/'cumulative_impact.png',dpi=180);fig.savefig(figdir/'cumulative_impact.pdf');plt.close(fig)
    lines=['# E1 결과와 S* 선정 — 2026-10-12','','**DONE:** fixed 3600 M0 + 2160 CHARM design trials; all PASS. Holdout prediction/performance has not been evaluated.','',
           '| Field | Bits | Mean net extra misses | Mean delta MPKI | Bit-weighted delta MPKI (95% CI) | Bootstrap top2 fraction |','|---|---:|---:|---:|---|---:|']
    for item in primary:
        lo,hi=item['bit_weighted_delta_MPKI_CI95']
        lines.append(f"| {item['field']} | {item['bits']} | {item['mean_net_extra_misses']:.5g} | {item['mean_delta_MPKI']:.5g} | {item['bit_weighted_delta_MPKI']:.5g} [{lo:.5g}, {hi:.5g}] | {item['bootstrap_top2_fraction']:.3f} |")
    lines += ['',f"**동결된 S*: {', '.join(selected)}; {payload} base payload bits, {len(words)} natural payload words.** 같은 S*에 P0/P_ED/P_ECC/P_TMR 모두 구현·비교한다. 선정한 payload/codeword 경계와 source sites는 `sources/protection_scope.lock.json`에 있다. Codec check/replica 수는 장부 계산일 뿐 구현/PPA 결과가 아니다.",'',
              '선정은 미리 고정한 M0 bit-weighted signed delta MPKI rule이다. Harm/help/negative/zero trials를 모두 남겼다. Per-event ranking과 전체 bit 노출의 contribution ranking을 구분한다. 선택이 통계적으로 확실히 분리된 최적 보호법이라는 뜻은 아니다. Added bits의 exposure, protection overhead, physical mapping과 target rate는 이후 평가가 필요하다.','',
              'Warmup: 같은 ROI에서 20k/100k/200k/400k/500k를 비교했다. Predefined resolution에 따라 500k full prefix를 사용한다. SHORT-INT-1의 400k vs 500k clean MPKI 민감도를 남겼고 해당 trace의 추가 600 paired SBU trials를 별도 보고했다. Stationary state 또는 무한 trace 수렴을 입증했다고 하지 않는다.','']
    for item in warmup_sensitivity:lines.append(f"- {item['workload']} 400k로 대체한 global top2: {', '.join(item['top2_with_alternate_warmup'])}; selected-set unchanged={item['selected_set_unchanged']}.")
    lines += ['','범위: 실제 HW1 CBP trace 및 SPEC2006 유래 trace를 non-spec plain TAGE로 replay했다. 모든 trial은 사건 직후부터 같은 100k conditional branches; raw instruction-record interval로 MPKI denominator를 계산했다. CPU cycles/IPC 결과는 아니다.','',
              '통계: workload별 event-trial bootstrap 2000회, six fixed trace 집합에 조건부. Source K sampling uncertainty는 별도로 보고한다. 100k 후속 branches를 100k 독립 표본으로 세지 않는다. Last divergence와 sampled state equality를 true recovery time으로 바꾸지 않는다.','',
              '다음: 같은 S*의 세 recovery controller(E2)와 holdout 비교. CPU cycles/IPC는 gem5 O3의 별도 E3 workload/hook/보호 latency 실험에서 측정한다. Cadence/PDK 검토는 계속 유예한다.']
    (ROOT/'reports/E1_SCOPE_SELECTION.ko.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status':report['status'],'fields':selected,'payload_bits':payload,'bootstrap_top2_fraction':top2_probability,'warmup_sensitivity':[{k:w[k] for k in ['workload','top2_with_alternate_warmup','selected_set_unchanged']} for w in warmup_sensitivity]},indent=2),flush=True)


if __name__=='__main__':main()
