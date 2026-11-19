from collections import Counter
import unittest

from simulation.analysis.sweep_design import METHODS, confirmatory_rows, pilot_cells, precision

PLAN = {
    'pilot': {'workloads':['qsort'], 'nonzero_rates_eps':[20], 'paired_seeds':4},
    'confirmatory': {'workloads':['qsort','crc32'], 'nonzero_rates_eps':[20,200,2000,8000]},
    'diagnostic_fault_law':'k1_only',
    'exposure_policy':'common_raw130',
    'timing_contract':'matched',
    'clock_period_ticks':13850,
    'ticks_per_second':10**12,
}
LAW='k1_k2_205_9'


def sample_rows():
    rows=[]
    for rate, seed_list in ((0, ('clean',)), (20, ('1','2','3','4'))):
        for seed in seed_list:
            for method in METHODS:
                halt = seed in ('1','2','3') and method=='ecc'
                cycles=30+(int(seed) if rate and method=='rebuild' else 0)
                rows.append(dict(stage='pilot', status='detected_stop' if halt else 'correct',
                                 workload='qsort',reference_rate_eps=rate,seed_id=seed,method=method,
                                 fault_law_id=LAW if rate else 'clean_reference',
                                 run_id=seed+'-'+method,pair_id=seed,shared_tape_sha256=seed,
                                 clock_period_ticks=13850,ticks_per_second=10**12,
                                 git_commit='source',input_sha256='input',timing_contract='matched',
                                 exposure_policy='common_raw130',roi_start_tick=0,roi_end_tick=cycles*13850,
                                 retired_instructions=100,direction_wrong=1))
    return rows


class SweepDesignTests(unittest.TestCase):
    def test_halting_arm_does_not_enter_conditional_time_precision(self):
        cells,seeds=pilot_cells(sample_rows(),PLAN['pilot'],LAW)
        self.assertEqual(seeds,{1,2,3,4})
        output={row['rebuild_comparator']:row for row in precision(cells)}
        self.assertEqual(output['ecc']['joint_correct'],1)
        self.assertIsNone(output['ecc']['projected_normal_half_width']['64']['runtime_benefit_pp'])
        self.assertEqual(output['tmr']['joint_correct'],4)
        self.assertGreater(output['tmr']['projected_normal_half_width']['8']['runtime_benefit_pp'],0)
        self.assertIsNone(output['tmr']['projected_normal_half_width']['64']['mpki_difference'])

    def test_missing_or_mismatched_arm_fails_closed(self):
        rows=sample_rows()
        with self.assertRaisesRegex(ValueError,'all five'):
            pilot_cells(rows[:-1],PLAN['pilot'],LAW)
        rows[-1]['shared_tape_sha256']='different'
        with self.assertRaisesRegex(ValueError,'shared_tape'):
            pilot_cells(rows,PLAN['pilot'],LAW)

    def test_expansion_preserves_existing_seed_namespace_without_overlap(self):
        small=list(confirmatory_rows(PLAN,LAW,8,202611290000,{11},True))
        large=list(confirmatory_rows(PLAN,LAW,64,202611290000,{11},True))
        self.assertTrue({r['planned_run_id'] for r in small} <= {r['planned_run_id'] for r in large})
        self.assertEqual(len(large),2*5*(1+2*4*64))
        used=Counter(r['seed_id'] for r in large if r['seed_id']!='clean')
        self.assertEqual(len(used),2*2*4*64)
        self.assertEqual(set(used.values()),{5})
        with self.assertRaisesRegex(ValueError,'collides'):
            list(confirmatory_rows(PLAN,LAW,8,10,{11},False))
