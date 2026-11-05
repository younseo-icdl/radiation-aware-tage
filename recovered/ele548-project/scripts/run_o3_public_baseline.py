#!/usr/bin/env python3
"""Three actual programs under the pristine pinned O3; no CPU fault injection."""
import concurrent.futures
import argparse
import hashlib
import json
import math
import os
import subprocess
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def stats(path):
    result={}
    for line in path.read_text().splitlines():
        fields=line.split()
        if len(fields)<2 or fields[0].startswith(('#','-')):continue
        try:result[fields[0]]=float(fields[1])
        except ValueError:continue
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=['debug','opt'],default='opt');args=parser.parse_args()
    native=json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text());assert native['status']=='PASS_THREE_ACTUAL_PUBLIC_PROGRAM_NATIVE_ANSWERS'
    binary=ROOT/('third_party/gem5/build/X86_STAGE0/gem5.'+args.variant);lock=json.loads((ROOT/'reports/software.lock.json').read_text())
    assert sha(binary)==lock['gem5_build' if args.variant=='debug' else 'gem5_opt_build']['binary_sha256']
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    outdir=ROOT/'reports/gem5_o3_public';outdir.mkdir(parents=True,exist_ok=True)
    report=ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json'
    report.write_text(json.dumps({'status':'RUNNING','variant':args.variant,'fault_injection':False,'programs':[]},indent=2)+'\n')
    def run(item):
        path=outdir/item['name'];path.mkdir(exist_ok=True);program=ROOT/item['binary'];inp=ROOT/item['input']
        assert sha(program)==item['binary_sha256'] and sha(inp)==item['input_sha256']
        stdout=path/'program.stdout';stderr=path/'program.stderr';log=path/'gem5.log'
        command=[str(binary),'--outdir='+str(path),str(ROOT/'gem5/o3_public.py'),'--binary',str(program),'--input',str(inp),'--stdout',str(stdout),'--stderr',str(stderr)]
        start=time.perf_counter();result={'program':item['name'],'command':command,'log':str(log.relative_to(ROOT))}
        with log.open('w') as f:
            try:p=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=900)
            except subprocess.TimeoutExpired:return dict(result,status='FAIL_TIMEOUT',wall_seconds=time.perf_counter()-start)
        result.update(exit_code=p.returncode,wall_seconds=time.perf_counter()-start)
        if p.returncode:return dict(result,status='FAIL_EXECUTION')
        if 'Exit cause: exiting with last active thread context code: 0' not in log.read_text():return dict(result,status='FAIL_TERMINATION')
        if not stdout.exists() or sha(stdout)!=item['native_stdout_sha256'] or not stderr.exists() or stderr.read_bytes():return dict(result,status='FAIL_NATIVE_OUTPUT_MATCH')
        system_config=json.loads((path/'config.json').read_text())['system']
        cpu_config=system_config['cpu'][0] if isinstance(system_config['cpu'],list) else system_config['cpu']
        tage_config=cpu_config['branchPred']['conditionalBranchPred']['tage']
        geometry=json.loads((ROOT/'configs/predictor.lock.json').read_text())['geometry']
        assert cpu_config['type']=='BaseO3CPU' and cpu_config['numThreads']==1 and not cpu_config['decoupledFrontEnd']
        assert tage_config['type']=='TAGEBase' and tage_config['speculativeHistUpdate']
        for k in ['nHistoryTables','minHist','maxHist','tagTableTagWidths','logTagTableSizes','tagTableCounterBits','tagTableUBits','pathHistBits','logUResetPeriod','instShiftAmt','takenOnlyHistory']:
            assert tage_config[k]==geometry[k],k
        assert system_config['clk_domain']['clock']==[500]
        s=stats(path/'stats.txt');cycles=s['system.cpu.numCycles'];instructions=s['system.cpu.commitStats0.numInsts'];ipc=s['system.cpu.ipc']
        assert s['simInsts']==instructions
        assert cycles>0 and instructions>0 and math.isclose(ipc,instructions/cycles,rel_tol=1e-6,abs_tol=5.1e-7)
        conditional_mispreds=s.get('system.cpu.branchPred.mispredicted_0::DirectCond',0)+s.get('system.cpu.branchPred.mispredicted_0::IndirectCond',0)
        all_mispreds=s['system.cpu.branchPred.mispredicted_0::total']
        stall={k:v for k,v in s.items() if k.startswith('system.cpu.fetch.') and any(t in k.lower() for t in ['stall','blocked','squash','icachewait'])}
        result.update(status='PASS_NATIVE_ANSWER_PRISTINE_O3',stdout_sha256=sha(stdout),stats_sha256=sha(path/'stats.txt'),config_sha256=sha(path/'config.json'),
            cycles=int(cycles),committed_instructions=int(instructions),IPC=ipc,IPC_from_counts=instructions/cycles,
            conditional_mispredictions=int(conditional_mispreds),all_branch_mispredictions=int(all_mispreds),
            conditional_MPKI=1000*conditional_mispreds/instructions,all_branch_MPKI=1000*all_mispreds/instructions,
            idle_cycles=s['system.cpu.idleCycles'],fetch_stall_counters=stall,
            branch_prediction_stat_boundary='committed mispredicted_0 counters; condIncorrect/corrected counters include speculative branches and are not used as committed MPKI numerator')
        return result
    start=time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,native['programs']))
    result={'status':'PASS_THREE_PRISTINE_O3_CLEAN_BASELINES' if all(r['status']=='PASS_NATIVE_ANSWER_PRISTINE_O3' for r in results) else 'FAIL_ONE_OR_MORE_BASELINES',
        'programs':results,'variant':args.variant,'gem5_binary_sha256':sha(binary),'source_commit':lock['source_commits']['gem5'],'gem5_config_sha256':sha(ROOT/'gem5/o3_public.py'),
        'workload_manifest_sha256':sha(ROOT/'reports/E3_PUBLIC_WORKLOADS.json'),'fault_injection':False,'protected_CPU_implementations':False,
        'ROI':native['ROI'],'workload_boundary':native['workload_boundary'],'warmup':'cold whole process, no separate warmup/stat reset',
        'latency':'pinned standard gem5 predictor path; no modeled or measured protection delay','wall_seconds':time.perf_counter()-start}
    report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'programs':[{k:r.get(k) for k in ['program','status','cycles','IPC','conditional_MPKI','wall_seconds']} for r in results]},indent=2),flush=True)
    if result['status'].startswith('FAIL'):raise SystemExit(1)
if __name__=='__main__':main()
