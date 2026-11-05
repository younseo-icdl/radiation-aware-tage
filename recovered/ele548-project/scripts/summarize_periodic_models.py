#!/usr/bin/env python3
"""Matched point estimates for a 96-trial model pilot; no two-seed tail certification."""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]

def main():
    path=ROOT/'reports/PERIODIC_MODEL_HOLDOUT.json';r=json.loads(path.read_text())
    assert r['status']=='PASS_FIXED_CONDITIONAL_MODEL_HOLDOUT_PILOT' and r['trials']==len(r['tasks'])==96
    assert r['config_sha256']==sha(ROOT/'configs/periodic_model_holdout.lock.json')
    assert r['selection_sha256']==sha(ROOT/'sources/periodic_policy_selection.lock.json')
    design_seeds={t['seed'] for t in json.loads((ROOT/'reports/PERIODIC_CPP_DESIGN.json').read_text())['tasks']}
    for p,h in r['original_campaigns'].items():assert sha(ROOT/p)==h
    groups=defaultdict(list)
    for t in r['tasks']:
        assert t['seed'] not in design_seeds
        assert sha(ROOT/(t['output']+'.csv'))==t['CSV_sha256']
        assert sha(ROOT/(t['output']+'.events.csv'))==t['events_CSV_sha256']
        assert sha(Path(t['command'][5]))==t['schedule_sha256']
        with (ROOT/(t['output']+'.csv')).open() as f:a=list(csv.DictReader(f))[0]
        assert a==t['metrics'] and a['status']=='PASS'
        assert int(a['net'])==int(a['harm'])-int(a['help'])==int(a['faulty_misses'])-int(a['clean_misses'])
        assert np.isclose(float(a['delta_MPKI']),1000*int(a['net'])/int(a['instructions']))
        if t['source_family']=='CERN_FOOTPRINT':key=(t['source_family'],t['condition']['source_file'],t['condition']['mode'],t['condition']['mapping'])
        else:key=(t['source_family'],t['condition']['duplicate_policy'],t['condition']['timing_model'])
        values={}
        for b in t['baseline_references']:
            assert sha(ROOT/b['CSV'])==b['CSV_sha256']
            values[b['scheme']]=float(b['metrics']['delta_MPKI'])
        # Old scheduled CSVs did not export checks; missing is not measured0.
        values.update(P_PERIODIC_ED=float(a['delta_MPKI']),periodic_minus_ED=float(a['delta_MPKI'])-values['P_ED'],periodic_checks=int(a['checks']))
        groups[key].append(values)
    result={'status':'PASS_AUDITED_CONDITIONAL_MODEL_HOLDOUT_PILOT','campaign_sha256':sha(path),'analysis_source_sha256':sha(Path(__file__)),'groups':[{'condition':list(key),'trials':len(values),'means':{name:float(np.mean([v[name] for v in values])) for name in values[0]},'uncertainty':'two seeds per each of2 fixed traces; matched point estimate, no robust CI/tail/physical-population claim'} for key,values in sorted(groups.items())],'same_scope':346,'timing_or_mapping_measured_on_target':False,'CPU_performance_result':False}
    (ROOT/'reports/PERIODIC_MODEL_SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'groups':len(groups)}))
if __name__=='__main__':main()
