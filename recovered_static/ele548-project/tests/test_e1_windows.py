"""Meaningful exact-record/split checks before predictor campaigns."""
import json
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from prepare_e1_windows import OUT_DTYPE


@unittest.skipUnless((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').exists(),'E1 private windows not prepared')
class E1WindowTests(unittest.TestCase):
    def test_exact_format_and_disjoint_real_instruction_ranges(self):
        manifest=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())
        self.assertEqual(OUT_DTYPE.itemsize,18)
        for workload in manifest['workloads']:
            arrays={}
            for split,entry in workload['split_files'].items():
                path=ROOT/entry['path']
                with path.open('rb') as f:self.assertEqual(f.read(8),b'E1CBP001')
                self.assertEqual((path.stat().st_size-8)%18,0)
                array=np.memmap(path,dtype=OUT_DTYPE,offset=8,mode='r')
                self.assertEqual(len(array),entry['control_branches'])
                self.assertEqual(int(np.count_nonzero(array['conditional'])),entry['conditional_branches'])
                self.assertTrue(np.all(array['record'][1:]>array['record'][:-1]))
                self.assertTrue(np.all(array['taken']<=1) and np.all(array['conditional']<=1))
                self.assertEqual([int(array['record'][0]),int(array['record'][-1])],entry['first_last_inclusive_original_record'])
                arrays[split]=array
            self.assertLess(arrays['design']['record'][-1],arrays['holdout']['record'][0])
            self.assertEqual(workload['split_files']['design']['conditional_branches'],620000)
            self.assertEqual(workload['split_files']['holdout']['conditional_branches'],520000)

    def test_every_planned_injection_has_full_horizon(self):
        c=json.loads((ROOT/'configs/e1.design.lock.json').read_text())
        manifest=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())
        for workload in manifest['workloads']:
            e=workload['split_files']['design']
            a=np.memmap(ROOT/e['path'],dtype=OUT_DTYPE,offset=8,mode='r')
            conditional=np.flatnonzero(a['conditional'])
            for inject in [0,c['injection_prefix_conditional_branches']-1]:
                first=c['design_anchor_conditional_ordinal']+inject
                last=first+c['post_event_horizon_conditional_branches']-1
                self.assertLess(last,len(conditional))
                self.assertGreaterEqual(int(a['record'][conditional[last]]-a['record'][conditional[first]]+1),c['post_event_horizon_conditional_branches'])


if __name__=='__main__':unittest.main()
