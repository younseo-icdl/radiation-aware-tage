#!/usr/bin/env python3
"""Audit before reporting B-D and finite single-event tail observations."""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run_o3_public_baseline import stats
from summarize_e3_cpu import sha,estimate,wilson,comparable_config
from periodic_analysis import abcd,assert_pair,comparable_periodic_config,max_covers_population_quantile_probability
from run_periodic_cpu import plan,validate_reference
ROOT=Path(__file__).resolve().parents[1]

def main():
    c=json.loads((ROOT/'configs/periodic_extension.lock.json').read_text());report=json.loads((ROOT/'reports/PERIODIC_CPU_EVAL.json').read_text())
    assert report['status']!='RUNNING' and report['completed_runs']==report['planned_runs']==c['cpu_new_runs']
    selection=json.loads((ROOT/'sources/periodic_policy_selection.lock.json').read_text())
    assert selection['config_sha256']==report['config_sha256']==sha(ROOT/'configs/periodic_extension.lock.json')
    assert report['selection_sha256']==sha(ROOT/'sources/periodic_policy_selection.lock.json')
    for p,h in report['baseline_campaign_hashes'].items():assert sha(ROOT/p)==h
    source=json.loads((ROOT/'sources/gem5_periodic_source.lock.json').read_text())
    for p,h in source['source_hashes'].items():assert sha(ROOT/p)==h
    assert report['source_lock_sha256']==sha(ROOT/'sources/gem5_periodic_source.lock.json')
    assert report['binary_sha256']==sha(ROOT/'third_party/gem5-periodic/build/X86_STAGE0/gem5.opt')
    assert report['gate_sha256']==sha(ROOT/'reports/PERIODIC_CPU_GATE.json')
    native={r['name']:r for r in json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text())['programs']}
    old_main=json.loads((ROOT/'reports/E3_CPU_MAIN.json').read_text());old_lat=json.loads((ROOT/'reports/E3_CPU_LATENCY.json').read_text())
    jobs,refs=plan(c,selection,old_main,old_lat,native)
    keys=lambda t:(t['program'],t['mode'],t['field'],t['trial'],t['seed'],t['interval'])
    assert set(map(keys,jobs))==set(map(keys,report['tasks'])) and len(set(map(keys,report['tasks'])))==len(jobs)
    assert report['baseline_references']==refs
    clean={(r['program'],r['scheme']):r for r in refs if r['reference_role']=='clean'}
    clean.update({(r['program'],r['scheme']):r for r in report['tasks'] if r['mode']=='zero' and r['status']=='PASS'})
    reference_pairs={(r['program'],r['mode'],r['field'],r['trial']):r for r in refs if r['scheme']=='P0' and r['mode']!='zero'}
    failures=[]
    for r in report['tasks']:
        if r['status']!='PASS':failures.append(r);continue
        d=ROOT/r['output']
        for file,key in [('stats.txt','stats_sha256'),('seu.json','seu_sha256'),('program.stdout','stdout_sha256'),('config.json','config_sha256'),('logical_manifest.json','manifest_sha256'),('events.csv','event_log_sha256'),('events.csv.repairs.csv','repair_log_sha256')]:assert sha(d/file)==r[key]
        assert sha(d/'schedule.ticks')==r['schedule_sha256']
        st=stats(d/'stats.txt');seu=json.loads((d/'seu.json').read_text());assert r['seu']==seu
        assert int(st['system.cpu.numCycles'])==r['cycles'] and int(st['system.cpu.commitStats0.numInsts'])==r['committed_instructions']==int(st['simInsts'])
        assert int(st['finalTick'])==seu['end_tick'] and np.isclose(r['IPC'],r['committed_instructions']/r['cycles'])
        assert r['conditional_mispredictions']==int(st['system.cpu.branchPred.mispredicted_0::DirectCond']+st['system.cpu.branchPred.mispredicted_0::IndirectCond'])
        assert r['stdout_sha256']==native[r['program']]['native_stdout_sha256'] and not (d/'program.stderr').read_bytes()
        original=ROOT/clean[(r['program'],'P_ED')]['output']/'config.json'
        raw_config=json.loads((d/'config.json').read_text())
        assert comparable_periodic_config(raw_config)==comparable_config(json.loads(original.read_text()))
        params=raw_config['system']['cpu']['branchPred']['conditionalBranchPred']['tage']
        assert (params['inspection_interval'],params['check_cycles'],params['repair_cycles'],params['cycle_ticks'],params['scheme'])==(selection['selected_interval'],c['cpu_check_cycles'],c['cpu_repair_cycles'],500,'P_ED')
        manifest=json.loads((d/'logical_manifest.json').read_text());assert manifest['total_bits']==65442
        assert len([s for s in manifest['additional_sites'] if s['structure']=='inspection_progress'])==8
        events=[(int(s.split()[0]),list(map(int,s.split()[1].split(';')))) for s in (d/'schedule.ticks').read_text().splitlines()]
        due=[e for e in events if e[0]<=seu['end_tick']]
        with (d/'events.csv').open() as f:actual=list(csv.DictReader(f))
        assert len(due)==len(actual)==seu['applied_events']
        for e,(tick,ids) in zip(actual,due):
            assert int(e['tick'])==tick and list(map(int,e['site_ids'].split(';')))==ids and e['XOR_verified']=='1'
            assert all(a!=b for a,b in zip(e['before_bits'],e['after_bits']))
        assert sum(len(ids) for _,ids in due)==seu['applied_flips']
        if r['mode']!='zero':assert_pair(reference_pairs[(r['program'],r['mode'],r['field'],r['trial'])],r)
    rng=np.random.Generator(np.random.PCG64(548202613));groups=[]
    methods=c['required_baselines']+['P_PERIODIC_ED']
    per_trial=[]
    for scheme in methods:
        records=[r for r in (refs if scheme!='P_PERIODIC_ED' else report['tasks']) if r['scheme']==scheme and r['mode']=='repeat' and r['status']=='PASS']
        metrics=defaultdict(lambda:defaultdict(list))
        for r in sorted(records,key=lambda r:(r['program'],r['trial'])):
            program=r['program'];A=clean[(program,'P0')]['cycles'];C=clean[(program,scheme)]['cycles']
            ref=reference_pairs[(program,'repeat','mixed',r['trial'])];assert_pair(ref,r) if scheme=='P_PERIODIC_ED' else None
            assert ref['seed']==r['seed']
            v=abcd(A,ref['cycles'],C,r['cycles'])
            v.update(cycles=r['cycles'],IPC=r['committed_instructions']/r['cycles'],conditional_MPKI=r['conditional_MPKI'],checks=r['seu']['checks'],response_hold_cycles=r['seu']['response_hold_cycles'],repair_batches=r['seu']['repair_batches'],applied_events=r['seu']['applied_events'],encode_words=r['seu']['encode_words'],delta_parity_operations=r['seu'].get('delta_parity_operations',0))
            per_trial.append(dict(program=program,scheme=scheme,trial=r['trial'],seed=r['seed'],**v))
            for name,value in v.items():metrics[name][program].append(value)
        summary={name:estimate([data[p] for p in c['cpu_programs']],rng,2000) for name,data in metrics.items()}
        programs={p:{name:estimate([data[p]],rng,2000) for name,data in metrics.items()} for p in c['cpu_programs']}
        groups.append(dict(scheme=scheme,trials=len(records),metrics=summary,program_metrics=programs))
    tails=[]
    for program in c['cpu_programs']:
        for field in c['single_fields']:
            rows=[r for r in report['tasks'] if r['program']==program and r['mode']=='single' and r['field']==field and r['status']=='PASS']
            delays=[];excess=[];net=[];censored=0
            for r in sorted(rows,key=lambda r:r['trial']):
                d=ROOT/r['output'];tick=int((d/'schedule.ticks').read_text().split()[0])
                with (d/'events.csv.repairs.csv').open() as f:repairs=list(csv.DictReader(f))
                if not repairs:censored+=1
                else:delays.append((int(repairs[0]['tick'])-tick)/500)
                C=clean[(program,'P_PERIODIC_ED')]['cycles'];A=clean[(program,'P0')]['cycles']
                B=reference_pairs[(program,'single',field,r['trial'])]['cycles']
                excess.append(r['cycles']-C);net.append(B-r['cycles'])
            def qs(v):return None if not v else dict(mean=float(np.mean(v)),p50=float(np.quantile(v,.5)),p95=float(np.quantile(v,.95)),maximum=float(max(v)),n=len(v))
            tails.append(dict(program=program,field=field,attempted=c['cpu_single_eval_trials_per_field'],normal_exits=len(rows),detection_right_censored=censored,detection_delay_CPU_cycles=qs(delays),fault_excess_cycles_D_minus_C=qs(excess),net_cycles_B_minus_D=qs(net),max_covers_population_p95_probability_under_IID=max_covers_population_quantile_probability(len(rows)),quantile_status='observed five-seed conditional pilot; no certified population p95 or worst-case bound'))
    cpp=json.loads((ROOT/'reports/PERIODIC_CPP_DESIGN.json').read_text());assert cpp['status']=='PASS_FIXED_CPP_DESIGN_PILOT'
    cpp_groups=[]
    for label in c['required_baselines']+[f'P_PERIODIC_ED_k{k}' for k in c['candidate_intervals']]:
        for mode in ['single','repeat']:
            rows=[r for r in cpp['tasks'] if r['variant']==label and r['mode']==mode]
            for r in rows:assert sha(ROOT/(r['output']+'.csv'))==r['CSV_sha256'] and r['status']=='PASS'
            delays=[int(r['metrics']['detector_delay_control_updates']) for r in rows if int(r['metrics']['detector_delay_control_updates'])>=0]
            cpp_groups.append(dict(variant=label,mode=mode,n=len(rows),mean_net_extra_misses=float(np.mean([int(r['metrics']['net']) for r in rows])),mean_checks=float(np.mean([int(r['metrics']['checks']) for r in rows])),observed_harm_p95=float(np.quantile([int(r['metrics']['harm']) for r in rows],.95)),mean_detection_delay_control_updates=float(np.mean(delays)) if delays else None,observed_detection_delay_control_updates_p95=float(np.quantile(delays,.95)) if delays else None,not_detected_or_censored=len(rows)-len(delays)))
    result=dict(status='PASS_AUDITED_PERIODIC_EXTENSION_PILOT' if not failures else 'AUDITED_PILOT_WITH_RETAINED_FAILURES',new_CPU_runs=len(report['tasks']),failures=[{k:r.get(k) for k in ['label','status','error']} for r in failures],failure_Wilson95CI=wilson(len(failures),len(report['tasks'])),campaign_sha256=sha(ROOT/'reports/PERIODIC_CPU_EVAL.json'),config_sha256=sha(ROOT/'configs/periodic_extension.lock.json'),analysis_source_sha256=sha(Path(__file__)),selected_interval=selection['selected_interval'],selection_sha256=sha(ROOT/'sources/periodic_policy_selection.lock.json'),baseline_reused_runs=len(refs),groups=groups,single_event_observed_tails=tails,cpp_design_groups=cpp_groups,per_trial=per_trial,statistical_unit='matched seed within2 fixed programs; bootstrap2000 equal program weights; means normal-exit conditional and benefit on paired normal exits; failures retained',clean_update_lane_added_latency=0,actual_RTL_PPA_measured=False,physical_rate_calibrated=False,novelty='periodic parity/checking are prior art; no new scheme novelty claim',source_and_control_gate='369 odd logical cases and13 actual O3 checksum cases;8 additional policy cells exposed by gates but targeted pilot excludes sidecars/control')
    (ROOT/'reports/PERIODIC_EXTENSION_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    path=ROOT/'reports/periodic_extension/figures';path.mkdir(exist_ok=True)
    fig,axes=plt.subplots(1,2,figsize=(10,4));x=np.arange(len(groups))
    for ax,name,ylabel in [(axes[0],'total_slowdown_pct','Total CPU cycle slowdown (%)'),(axes[1],'net_benefit_pct_points','Net B-D (% of P0 clean cycles)')]:
        means=np.array([g['metrics'][name]['mean'] for g in groups]);ci=np.array([g['metrics'][name]['bootstrap95CI'] for g in groups])
        ax.bar(x,means,yerr=np.maximum(0,np.stack([means-ci[:,0],ci[:,1]-means])),capsize=4)
        ax.set_xticks(x,['P0','parity','SECDED','TMR',f'periodic\nk={selection["selected_interval"]}']);ax.set_ylabel(ylabel);ax.axhline(0,color='gray',lw=.7)
    fig.suptitle('CHARM6T targeted payload; assumed C1/R4, update lane0 extra cycles;2 fixed programs')
    fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(path/f'periodic_cpu_comparison.{ext}',dpi=180)
    plt.close(fig)
    print(json.dumps({'status':result['status'],'trials':len(report['tasks']),'failures':len(failures)}))
if __name__=='__main__':main()
