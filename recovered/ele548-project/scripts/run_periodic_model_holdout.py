#!/usr/bin/env python3
"""Finite source-pattern holdout; reuse fixed schedules and disjoint selection owners."""
import concurrent.futures
import csv
import json
import subprocess
from pathlib import Path
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]

def main():
    c=json.loads((ROOT/'configs/periodic_model_holdout.lock.json').read_text())
    selected=json.loads((ROOT/'sources/periodic_policy_selection.lock.json').read_text());k=selected['selected_interval']
    design_seeds={r['seed'] for r in json.loads((ROOT/'reports/PERIODIC_CPP_DESIGN.json').read_text())['tasks']}
    original={name:json.loads((ROOT/f'reports/{name}_MAIN.json').read_text()) for name in ['CERN_FOOTPRINT','FLYING_TIMING']}
    out=ROOT/'reports/periodic_extension/model_holdout';out.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for name,campaign in original.items():
        for r in campaign['tasks']:
            if r['scheme']!='P_ED' or r['workload'] not in c['workloads']:continue
            if name=='CERN_FOOTPRINT':
                if r['trial'] not in c['CERN_trials'] or r['normalization']!='equal_event':continue
                fields=['workload','source_file','mode','normalization','mapping','trial']
            else:
                if r['trial'] not in c['Flying_trials'] or r['K_profile']!='SBU':continue
                fields=['workload','duplicate_policy','timing_model','K_profile','trial']
            assert r['seed'] not in design_seeds
            references=[a for a in campaign['tasks'] if all(a[f]==r[f] for f in fields)]
            assert {a['scheme'] for a in references}=={'P0','P_ED','P_ECC','P_TMR'}
            for a in references:
                assert a['status']=='PASS' and sha(ROOT/a['CSV'])==a['CSV_sha256']
                assert sha(Path(a['command'][5]))==a['schedule_sha256']
            idx=len(jobs);prefix=out/f'{name}.{idx:03d}'
            command=r['command'].copy();command[0]=str(ROOT/'build/periodic_scheduled');command[7]=str(prefix);command.append(str(k))
            jobs.append(dict(source_family=name,condition={f:r[f] for f in fields},seed=r['seed'],command=command,output=str(prefix.relative_to(ROOT)),schedule_sha256=r['schedule_sha256'],baseline_references=references))
    assert len(jobs)==c['expected_runs']
    def run(t):
        with (ROOT/(t['output']+'.log')).open('w') as f:p=subprocess.run(t['command'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=120)
        assert p.returncode==0
        path=ROOT/(t['output']+'.csv')
        with path.open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==1 and rows[0]['status']=='PASS'
        m=rows[0]
        for key in ['clean_misses','instructions','post_branches','event_count','flip_count']:
            assert m[key]==t['baseline_references'][0]['metrics'][key]
        return dict(t,status='PASS',metrics=m,CSV_sha256=sha(path),events_CSV_sha256=sha(ROOT/(t['output']+'.events.csv')))
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers']) as pool:rows=list(pool.map(run,jobs))
    record={'status':'PASS_FIXED_CONDITIONAL_MODEL_HOLDOUT_PILOT','config_sha256':sha(ROOT/'configs/periodic_model_holdout.lock.json'),'selection_sha256':sha(ROOT/'sources/periodic_policy_selection.lock.json'),'original_campaigns':{f'reports/{name}_MAIN.json':sha(ROOT/f'reports/{name}_MAIN.json') for name in original},'trials':len(rows),'tasks':rows,'no_reselection':True,'same_scope':'346 selected payload bits, sidecars/progress excluded in targeted model pilot','interpretation':'branch-trace source-pattern sensitivity; source time compression and hypothetical geometry retained; not actual CPU cycles or physical calibration'}
    (ROOT/'reports/PERIODIC_MODEL_HOLDOUT.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'status':record['status'],'trials':len(rows)}))
if __name__=='__main__':main()
