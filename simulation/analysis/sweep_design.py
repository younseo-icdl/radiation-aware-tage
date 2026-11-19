"""Project confirmation precision from a complete paired pilot and freeze a grid."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import stdev

from .native_completion import stop_stats

METHODS = ('unprotected', 'rebuild', 'ecc', 'tmr', 'ecc_refill')
COMPARATORS = ('unprotected', 'ecc', 'tmr', 'ecc_refill')
RECOVERY = dict(zip(METHODS, ('none', 'own_raw_refold_4096', 'halt_on_due',
                             'majority_feedback_repair', 'fallback_refill')))
BUDGETS = (8, 16, 32, 64)
VALID_OUTCOMES = {'correct', 'detected_stop', 'timeout', 'dut_crash', 'sdc'}


def pilot_cells(rows, settings, law):
    groups = {}
    ids = set()
    for row in rows:
        if row['stage'] != 'pilot' or row['status'] not in VALID_OUTCOMES:
            raise ValueError('all pilot rows must have an observed terminal outcome')
        if row['run_id'] in ids:
            raise ValueError('duplicate pilot run ID')
        ids.add(row['run_id'])
        workload, rate, seed = row['workload'], int(row['reference_rate_eps']), row['seed_id']
        expected_law = law if rate else 'clean_reference'
        if row['fault_law_id'] != expected_law or (seed == 'clean') != (rate == 0):
            raise ValueError('pilot law or clean seed does not match its rate')
        cell = groups.setdefault((workload, rate), {})
        pair = cell.setdefault(seed, {})
        method = row['method']
        if method not in METHODS or method in pair:
            raise ValueError(f'unknown or duplicate method in {(workload, rate, seed)}')
        pair[method] = row
    expected_cells = {(workload, rate) for workload in settings['workloads']
                      for rate in (0, *settings['nonzero_rates_eps'])}
    if set(groups) != expected_cells:
        raise ValueError('pilot cell grid is incomplete or has unexpected conditions')
    global_seeds = set()
    for (_workload, rate), cell in groups.items():
        expected_seeds = settings['paired_seeds'] if rate else 1
        if len(cell) != expected_seeds:
            raise ValueError('pilot cell does not have the declared number of paired seeds')
        for seed, pair in cell.items():
            if set(pair) != set(METHODS):
                raise ValueError('pilot seed does not include all five arms')
            if rate:
                if int(seed) in global_seeds:
                    raise ValueError('pilot fault seed reused across cells')
                global_seeds.add(int(seed))
            for field in ('pair_id','shared_tape_sha256','clock_period_ticks','ticks_per_second',
                          'git_commit','input_sha256','timing_contract','exposure_policy'):
                if len({arm[field] for arm in pair.values()}) != 1:
                    raise ValueError(f'pilot pair disagrees on {field}')
            if not rate and any(arm['status'] != 'correct' for arm in pair.values()):
                raise ValueError('pilot clean controls did not all complete correctly')
    return groups, global_seeds


def outcomes(row):
    if row['status'] != 'correct':
        return None
    ticks=int(row['roi_end_tick'])-int(row['roi_start_tick'])
    instructions=int(row['retired_instructions'])
    misses=int(row['direction_wrong'])
    if ticks <= 0 or instructions <= 0 or not 0 <= misses <= instructions:
        raise ValueError('successful arm has invalid time or direction counts')
    return ticks/int(row['ticks_per_second']), 1000*misses/instructions


def cell_precision(cell, baseline):
    runtime,mpki=[],[]
    for pair in cell.values():
        control,candidate=outcomes(pair[baseline]),outcomes(pair['rebuild'])
        if control is not None and candidate is not None:
            runtime.append(100*(control[0]-candidate[0])/control[0])
            mpki.append(candidate[1]-control[1])
    observed=len(runtime)
    fraction=observed/len(cell)
    def spread(values):
        if len(values)<2:
            return None
        return stdev(values) or None
    variability={'runtime_benefit_pp':spread(runtime),'mpki_difference':spread(mpki)}
    projections={}
    for budget in BUDGETS:
        joint=budget*fraction
        projections[str(budget)]={'projected_joint_successes':joint, **{
            key:1.96*sd/math.sqrt(joint) if joint>=8 and sd is not None else None
            for key,sd in variability.items()}}
    return dict(total_seeds=len(cell),joint_correct=observed,observed_joint_fraction=fraction,
                pilot_sample_deviation=variability,projected_normal_half_width=projections)


def precision(cells):
    return [{'workload':workload,'rate_eps':rate,'rebuild_comparator':arm,
             **cell_precision(cell,arm)}
            for (workload,rate),cell in sorted(cells.items()) if rate
            for arm in COMPARATORS]


def host_cost(cells, run_root):
    per_cell=[]
    for (workload,rate), cell in sorted(cells.items()):
        seconds=0.0
        for pair in cell.values():
            for row in pair.values():
                run=run_root/row['run_id']
                stats=stop_stats(run/'stats.txt',int(row['roi_end_tick']))
                elapsed=float(stats['hostSeconds'])
                if not math.isfinite(elapsed) or elapsed < 0:
                    raise ValueError(f'invalid host measurement in {run}')
                seconds+=elapsed
        per_cell.append(dict(workload=workload,rate_eps=rate,observed_host_seconds=seconds,
                             mean_arm_sum_seconds_per_seed=seconds/len(cell)))
    return dict(cells=per_cell,
                projected_primary_overlap_host_hours={
                    str(n):sum(item['mean_arm_sum_seconds_per_seed']*(n if item['rate_eps'] else 1)
                               for item in per_cell)/3600 for n in BUDGETS},
                scope='sum of observed host elapsed times, with projections only for pilot workloads and rates')


def confirmatory_rows(plan, law, count, namespace, used, both_laws):
    settings=plan['confirmatory']
    laws=(law,plan['diagnostic_fault_law']) if both_laws else (law,)
    if count not in BUDGETS or not 0<=namespace<=10**18:
        raise ValueError('invalid seed count or namespace')
    for wi,workload in enumerate(settings['workloads']):
        work=[('clean_reference',0,'clean','')]
        for li,exposure in enumerate(laws):
            for ri,rate in enumerate(settings['nonzero_rates_eps']):
                for si in range(count):
                    # Retain the original eight proposed seeds with the adopted
                    # namespace. Additional seeds have a separate per-rate range.
                    offset=ri*10+si if si<8 else 100+ri*64+si
                    seed=namespace+li*1000000+wi*1000+offset
                    if seed in used:
                        raise ValueError(f'confirmation seed {seed} collides with an existing tape')
                    used.add(seed)
                    work.append((exposure,rate,str(seed),str(si)))
        for exposure,rate,seed,replicate in work:
            digest=hashlib.sha256(f'confirmatory:{workload}:{exposure}:{rate}:{seed}'.encode()).hexdigest()
            pair='planned-'+digest[:16]
            for arm in METHODS:
                yield dict(planned_run_id=f'{pair}-{arm}',stage='confirmatory',workload=workload,
                           method=arm,recovery_policy=RECOVERY[arm],pair_id=pair,seed_id=seed,
                           replicate_index=replicate,fault_law_id=exposure,reference_rate_eps=rate,
                           exposure_policy=plan['exposure_policy'],timing_contract=plan['timing_contract'],
                           clock_period_ticks=plan['clock_period_ticks'],ticks_per_second=plan['ticks_per_second'],
                           rebuild_interval_appends=4096 if arm=='rebuild' else 0,
                           rebuild_service_cycles=2 if arm=='rebuild' else 0,status='PLANNED_NOT_EXECUTED')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot',type=Path,required=True)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run-root',type=Path,help='optional directory containing raw pilot run folders')
    parser.add_argument('--freeze-seeds',type=int,choices=BUDGETS)
    parser.add_argument('--runtime-target-pp',type=float)
    parser.add_argument('--mpki-target',type=float)
    parser.add_argument('--rationale')
    parser.add_argument('--namespace',type=int,default=202611290000)
    parser.add_argument('--both-laws',action='store_true')
    args=parser.parse_args()
    try:
        targets=(args.runtime_target_pp,args.mpki_target)
        if args.freeze_seeds and (not args.rationale or
                any(value is None or not math.isfinite(value) or value<=0 for value in targets)):
            raise ValueError('freeze requires positive endpoint targets and a decision rationale')
        plan=json.loads(args.plan.read_text())
        law=plan['primary_fault_law']['id']
        with args.pilot.open() as stream:
            groups,pilot_seeds=pilot_cells(csv.DictReader(stream),plan['pilot'],law)
        projections=precision(groups)
        resource=host_cost(groups,args.run_root) if args.run_root else None
        frozen=None
        if args.freeze_seeds:
            frozen=list(confirmatory_rows(plan,law,args.freeze_seeds,args.namespace,
                                          set(pilot_seeds),args.both_laws))
        args.output.mkdir(parents=True)
        report=dict(pilot_sha256=hashlib.sha256(args.pilot.read_bytes()).hexdigest(),
                    plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                    pilot_seed_count=len(pilot_seeds), budgets=BUDGETS, projections=projections,
                    host_cost=resource,
                    interpretation='planning approximation using observed joint correctness and sample deviation; '
                                   'no confidence intervals, significance decisions or equality claims',
                    frozen_seed_count=args.freeze_seeds,frozen_grid_rows=len(frozen) if frozen else 0,
                    targets=dict(runtime_half_width_pp=targets[0],mpki_half_width=targets[1]),
                    rationale=args.rationale, namespace=args.namespace if frozen else None)
        if frozen:
            with (args.output/'confirmatory.csv').open('x',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=frozen[0])
                writer.writeheader()
                writer.writerows(frozen)
        (args.output/'precision.json').write_text(json.dumps(report,indent=2)+'\n')
    except (OSError,ValueError,KeyError,ZeroDivisionError) as error:
        parser.error(str(error))


if __name__=='__main__':
    main()
