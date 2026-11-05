from m5.objects.BranchPredictor import TAGE, TAGEBase
from m5.params import Param
from m5.util.pybind import PyBindMethod

class ResearchTAGEBase(TAGEBase):
    type = 'ResearchTAGEBase'
    cxx_class = 'bp::CpuTAGEBase'
    cxx_header = 'cpu/pred/research_tage.hh'
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

class ResearchTAGE(TAGE):
    type = 'ResearchTAGE'
    cxx_class = 'bp::CpuTAGE'
    cxx_header = 'cpu/pred/research_tage.hh'
    tage = ResearchTAGEBase()
