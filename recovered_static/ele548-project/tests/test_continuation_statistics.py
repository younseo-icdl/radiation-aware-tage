import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from continuation_statistics import *
class Statistics(unittest.TestCase):
 def test_identity_help_and_zero(self):
  for B,D in [(110,104),(95,100),(100,100)]:
   x=abcd(100,B,102,D);self.assertAlmostEqual(x['net_pp'],x['fault_unprotected_pct']-x['clean_overhead_pct']-x['residual_loss_pp'])
  self.assertLess(abcd(100,95,102,104)['net_pp'],0)
 def test_cluster_resampling_fixed_inputs(self):
  x=fixed_program_bootstrap({'a':[1,1,1],'b':[5,5,5]});self.assertEqual(x['mean'],3);self.assertEqual(x['CI95'],[3,3]);self.assertIsNone(fixed_program_bootstrap({'a':[1]})['CI95'])
 def test_pair_rejects_wrong_owner_schedule_oracle(self):
  b=dict(owner='x',program='p',scenario='s',input_sha256='a',schedule_sha256='b',status='PASS');d=dict(b)
  self.assertTrue(audit_pair(b,d));d['schedule_sha256']='c'
  with self.assertRaises(ValueError):audit_pair(b,d)
  d=dict(b,oracle=True)
  with self.assertRaises(ValueError):audit_pair(b,d)
 def test_failures_are_not_cycles0(self):
  for value in [0,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):abcd(100,100,100,value)
  b=dict(owner='x',program='p',scenario='s',input_sha256='a',schedule_sha256='b',status='PASS');self.assertFalse(audit_pair(b,dict(b,status='FAIL_WALL_TIMEOUT')))
 def test_zero_failure_upper_is_small_sample_bound(self):
  self.assertAlmostEqual(zero_failure_upper(10),1-.05**.1);self.assertIsNone(zero_failure_upper(0))
if __name__=='__main__':unittest.main()
