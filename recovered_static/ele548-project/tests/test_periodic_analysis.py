import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from periodic_analysis import abcd,assert_pair,continuous_optimum,proxy_J,max_covers_population_quantile_probability

class PeriodicAnalysis(unittest.TestCase):
    def test_net_benefit_cost_identity_and_helpful_faults(self):
        # Recovery lowers faulty execution but clean overhead can still lose.
        r=abcd(100,110,120,118)
        self.assertEqual(r['net_cycles_B_minus_D'],-8)
        self.assertLess(r['fault_excess_cycles_D_minus_C'],0)
        self.assertLess(r['fault_loss_pct_own_clean'],0)
        self.assertAlmostEqual(r['total_slowdown_pct'],100*((1+r['clean_overhead_pct']/100)*(1+r['fault_loss_pct_own_clean']/100)-1))
    def test_pair_rejects_wrong_seed_or_schedule(self):
        a=dict(program='p',mode='repeat',field='mixed',trial=0,seed=123,schedule_card={'input_schedule_sha256':'x'})
        b=dict(a,schedule_sha256='x');assert_pair(a,b)
        with self.assertRaises(AssertionError):assert_pair(a,dict(b,seed=124))
        with self.assertRaises(AssertionError):assert_pair(a,dict(b,schedule_sha256='y'))
    def test_continuous_proxy_optimum_against_bracket(self):
        k=continuous_optimum(1,.002,2)
        self.assertLess(proxy_J(k,1,.002,2),proxy_J(k/2,1,.002,2))
        self.assertLess(proxy_J(k,1,.002,2),proxy_J(k*2,1,.002,2))
        self.assertIsNone(continuous_optimum(1,0,2))
        with self.assertRaises(ValueError):proxy_J(1,1,.001,-1)
    def test_small_pilot_cannot_certify_p95_tail(self):
        self.assertLess(max_covers_population_quantile_probability(5),.25)
        self.assertLess(max_covers_population_quantile_probability(58),.95)
        self.assertGreaterEqual(max_covers_population_quantile_probability(59),.95)

if __name__=='__main__':unittest.main()
