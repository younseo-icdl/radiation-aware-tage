"""Units and pairing for an exploratory policy extension; no physical-rate fitting."""
import math
import copy
from summarize_e3_cpu import comparable_config

def abcd(a,b,c,d):
    if a<=0 or c<=0:raise ValueError('positive clean CPU cycles required')
    return {'net_cycles_B_minus_D':b-d,'clean_overhead_pct':100*(c/a-1),
            'fault_loss_pct_own_clean':100*(d/c-1),'total_slowdown_pct':100*(d/a-1),
            'net_benefit_pct_points':100*(b-d)/a,'fault_excess_cycles_D_minus_C':d-c}

def comparable_periodic_config(config):
    normalized=copy.deepcopy(config)
    conditional=normalized['system']['cpu']['branchPred']['conditionalBranchPred']
    assert conditional['type']=='PeriodicTAGE' and conditional['cxx_class']=='bp::CpuPeriodicTAGE'
    conditional.update(type='ResearchTAGE',cxx_class='bp::CpuTAGE')
    tage=conditional['tage'];assert tage['type']=='PeriodicTAGEBase' and tage['cxx_class']=='bp::CpuPeriodicTAGEBase'
    tage.update(type='ResearchTAGEBase',cxx_class='bp::CpuTAGEBase')
    del tage['inspection_interval']
    return comparable_config(normalized)

def assert_pair(reference,trial):
    assert (reference['program'],reference['mode'],reference['field'],reference['trial'],reference['seed']) == (
        trial['program'],trial['mode'],trial['field'],trial['trial'],trial['seed'])
    assert reference['schedule_card']['input_schedule_sha256']==trial['schedule_sha256']

def residual_wait_expectation(k):
    if k<=0:raise ValueError('positive interval')
    return k/2 # Continuous, independent uniform phase; not actual TAGE timing.

def proxy_J(k,c,rate,d):
    if k<=0 or c<0 or rate<0 or d<0:raise ValueError('assumed nonnegative damage/cost model')
    return c/k+rate*d*residual_wait_expectation(k)

def continuous_optimum(c,rate,d):
    if c<=0 or rate<=0 or d<=0:return None
    return math.sqrt(2*c/(rate*d))

def max_covers_population_quantile_probability(n,q=.95):
    if n<0 or not 0<q<1:raise ValueError('sample count and quantile')
    return 1-q**n # IID conditional sample; no claim of unseen-workload validity.
