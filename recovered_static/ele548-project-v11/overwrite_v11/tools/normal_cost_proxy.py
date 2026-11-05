#!/usr/bin/env python3
"""Logical work and matched-source caveats; no timing/energy simulation."""
from pathlib import Path
import csv,hashlib,json
BASE=Path(__file__).resolve().parents[1];REPORT=BASE/'reports'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def stats(p):
    values={}
    for line in p.read_text().splitlines():
        f=line.split()
        if len(f)>1:
            try:values[f[0]]=float(f[1])
            except ValueError:pass
    return values
def main():
    cpu_path=REPORT/'CPU_REGRESSION.json';cpu=json.loads(cpu_path.read_text())
    assert cpu['status']=='PASS_ALL6_OVERWRITE_ZERO_FAULT_CPU_REGRESSIONS_NOT_COST_VALIDATION'
    old_path=Path('/home/youns/workspace/ele548-project-v10/native_lifetime_next/runtime/reports/LIFETIME_CLEAN.json')
    old=json.loads(old_path.read_text());rows=[];sources=[]
    for r in cpu['tasks']:
        p=Path(r['output'])/'stats.txt';assert sha(p)==r['hashes']['stats.txt']
        direct=next(d for d in old['tasks'] if (d['program'],d['R'],d['policy'])==(r['program'],r['R'],'A_DIR'))
        q=Path(direct['output'])/'stats.txt';assert sha(q)==direct['hashes']['stats.txt']
        a,b=stats(p),stats(q)
        fields=['system.cpu.branchPred.lookups_0::DirectCond','system.cpu.branchPred.lookups_0::IndirectCond']
        assert all(a[f]==b[f] for f in fields)
        conditional=int(sum(a[f] for f in fields));jobs=r['seu']['overwrite_forward_calls']+r['seu']['overwrite_undo_calls']
        rows.append({'program':r['program'],'R':r['R'],'CPU_conditional_lookup_count':conditional,
                     'overwrite_full_fold_jobs':jobs,'overwrite_jobs_per_conditional_lookup':jobs/conditional,
                     'all_lookup_count':r['seu']['lookup_issues'],
                     'direct_lookup_only_tap_term_proxy':conditional*912,
                     'overwrite_actual_tap_terms':r['seu']['overwrite_tap_terms']})
        sources.extend([ref(p),ref(q)])
    with (REPORT/'NORMAL_COST_PROXY.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    out={'status':'ACTUAL_COUNTS_WITH_EXPLICIT_LOGICAL_PROXY_NOT_ENERGY_OR_FINITE_CPU_COST',
         'records':rows,'sources':sources,'old_clean_report':ref(old_path),'new_clean_report':ref(cpu_path),
         'direct_proxy_scope':'21-fold set per conditional lookup. Actual direct reduction calls are NOT instrumented here; surprise-branch reindexing and diagnostic hashing may also call fold helpers. Not an exact total direct work counter.',
         'source_scope':'Overwrite/native recurrent retain inherited software raw buffer and pointer; direct exposes finite ring/rollback journal/head/FIFO. Conditional raw130 events are comparable; full physical source/storage cost is not matched by this CPU gate.',
         'next':'Match finite source retention, ownership, ports and undo service before whole-design cost claims; separate lookup and update timing.',
         'analysis_tool':ref(Path(__file__))}
    with (REPORT/'NORMAL_COST_PROXY.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(rows))
if __name__=='__main__':main()
