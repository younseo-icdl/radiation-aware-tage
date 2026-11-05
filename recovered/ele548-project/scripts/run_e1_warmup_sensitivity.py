#!/usr/bin/env python3
"""Complete the locked sensitivity for preflight-flagged design warmups."""
import json
import argparse
from pathlib import Path
from run_e1 import task_command,run_command,validate_rows,sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');args=parser.parse_args()
    c=json.loads((ROOT/'configs/e1.design.lock.json').read_text())
    s=json.loads((ROOT/'configs/e1.warmup_sensitivity.lock.json').read_text())
    p=json.loads((ROOT/'reports/E1_PREFLIGHT.json').read_text())
    windows=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())
    byname={w['workload']:w for w in windows['workloads']}
    outdir=ROOT/'reports/e1/warmup_sensitivity';outdir.mkdir(parents=True,exist_ok=True)
    outcomes=[]
    for warm in p['warmup']:
        if warm['stability_400k_vs_500k']:continue
        name=warm['workload'];entry=byname[name]['split_files']['design'];path=ROOT/entry['path']
        assert sha(path)==entry['sha256']
        item=(c['workloads'].index(name),name,path);output=outdir/f'{name}.M0.csv'
        command=task_command(c,item,'M0',s['trials_per_workload_field'],s['seed_base'],s['alternate_warmup_conditional_branches'],output)
        result=({'status':'PASS','command':command,'mode':'verify previously executed locked data'} if args.verify_only else
                run_command(command,outdir/f'{name}.log',c['per_task_timeout_seconds']))
        if result['status']!='PASS':raise RuntimeError(json.dumps(result))
        rows=validate_rows(output,s['trials_per_workload_field']*6,c)
        result.update(workload=name,trials=len(rows),CSV=str(output.relative_to(ROOT)),CSV_sha256=sha(output))
        outcomes.append(result)
    report={'status':'PASS_LOCKED_FLAGGED_WARMUP_SENSITIVITY','config_sha256':sha(ROOT/'configs/e1.warmup_sensitivity.lock.json'),
            'tasks':outcomes,'verification_only':args.verify_only,'holdout_performance_evaluated':False,'scope_selection_uses':'primary full-prefix M0 only'}
    (ROOT/'reports/E1_WARMUP_SENSITIVITY.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'tasks':len(outcomes),'trials':sum(r['trials'] for r in outcomes)},indent=2))


if __name__=='__main__':main()
