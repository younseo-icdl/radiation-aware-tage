#!/usr/bin/env python3
"""Compare optimized/debug checksum output and simulated counters, not wall time."""
import json
import hashlib
import os
import subprocess
from pathlib import Path
from run_o3_public_baseline import stats
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    out=ROOT/'reports/gem5_o3_opt_checksum';out.mkdir(exist_ok=True)
    binary=ROOT/'third_party/gem5/build/X86_STAGE0/gem5.opt';program=ROOT/'build/checksum_freestanding'
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    command=[str(binary),'--outdir='+str(out),str(ROOT/'gem5/o3_checksum.py'),'--binary',str(program)]
    with (out/'gem5.log').open('w') as f:p=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
    assert p.returncode==0
    log=(out/'gem5.log').read_text();assert 'checksum=1321703870693' in log and 'Exit cause: exiting with last active thread context code: 0' in log
    a=stats(out/'stats.txt');b=stats(ROOT/'reports/gem5_o3/stats.txt')
    keys=['system.cpu.numCycles','system.cpu.commitStats0.numInsts','system.cpu.commitStats0.numOps','system.cpu.branchPred.condPredicted','system.cpu.branchPred.condIncorrect','system.cpu.branchPred.mispredicted_0::total']
    for k in keys:assert a[k]==b[k],(k,a[k],b[k])
    result={'status':'PASS_OPT_DEBUG_CHECKSUM_AND_SIMULATED_COUNTERS','command':command,'exit_code':p.returncode,'counters':{k:a[k] for k in keys},
            'optimized_binary_sha256':sha(binary),'program_sha256':sha(program),'optimized_stats_sha256':sha(out/'stats.txt'),'debug_stats_sha256':sha(ROOT/'reports/gem5_o3/stats.txt'),
            'scope':'same synthetic checksum only; no CPU fault injection or independent TAGE algorithm validation'}
    (ROOT/'reports/E3_OPT_DEBUG_EQUIVALENCE.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])
if __name__=='__main__':main()
