from m5.objects.BranchPredictor import TAGE, TAGEBase
from m5.params import Param
from m5.util.pybind import PyBindMethod

class ContinuationTAGEBase(TAGEBase):
    type = 'ContinuationTAGEBase'
    cxx_class = 'bp::CpuContinuationTAGEBase'
    cxx_header = 'cpu/pred/research_continuation_tage.hh'
    inspection_interval = Param.Unsigned(0, 'Optional continuation ED history-update interval,1..64;0 is legacy')
    role_policy = Param.String('LEGACY', 'LEGACY/N1/H1/REV')
    maintenance_cycles = Param.Unsigned(0, 'Finite queued history maintenance service cycles,0 same-stage hypothesis')
    scheme = Param.String('P0', 'P0/P_ED/P_ECC/P_TMR on fixed history scope')
    schedule_file = Param.String('', 'Frozen tick whitespace semicolon-ID events')
    event_log = Param.String('', 'Actual applied event log')
    summary_file = Param.String('', 'Final functional/injection counters')
    manifest_file = Param.String('', 'Actual added CPU protection cells')
    read_log = Param.String('', 'Optional bounded ordinary prediction-read log')
    read_log_limit = Param.Unsigned(200, 'First reads logged for ordering/timing gates')
    cycle_ticks = Param.Tick(500, 'Must equal CPU cycle; default pinned 2GHz')
    check_cycles = Param.Unsigned(0, 'Assumed check/read response latency')
    repair_cycles = Param.Unsigned(0, 'Assumed repair port hold latency')
    cxx_exports = [PyBindMethod('dumpSeu')]

class ContinuationTAGE(TAGE):
    type = 'ContinuationTAGE'
    cxx_class = 'bp::CpuContinuationTAGE'
    cxx_header = 'cpu/pred/research_continuation_tage.hh'
    tage = ContinuationTAGEBase()
