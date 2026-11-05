"""Finite request/response TAGE with source protection and external SEU input."""
from m5.objects.BranchPredictor import TAGE, TAGEBase
from m5.params import Param
from m5.util.pybind import PyBindMethod


class FiniteTAGEBase(TAGEBase):
    type = 'FiniteTAGEBase'
    cxx_class = 'bp::CpuFiniteTAGEBase'
    cxx_header = 'cpu/pred/finite_tage.hh'
    representation = Param.String('recurrent', 'recurrent or exact direct folding')
    pipeline_latency = Param.Unsigned(1, 'Source query latency in CPU cycles: 1 or 2')
    pipeline_ii = Param.Unsigned(1, 'Source query initiation interval; fixed at 1')
    rmw_latency = Param.Unsigned(1, 'Source update latency in CPU cycles: 1 or 2')
    rmw_ii = Param.Unsigned(1, 'Source update initiation interval; fixed at 1')
    early_unconditional = Param.Bool(False, 'Enable early unconditional checkpoint path')
    inspection_interval = Param.Unsigned(0, 'Parity update interval: 0 for every operation, or 64')
    scheme = Param.String('P0', 'P0/P_ED/P_ECC/P_TMR on selected history')
    schedule_file = Param.String('', 'Tick and semicolon-separated logical sites per event')
    event_log = Param.String('', 'Applied event log')
    summary_file = Param.String('', 'Final predictor, pipeline, and injection counters')
    manifest_file = Param.String('', 'Exposed logical storage and exclusions')
    cycle_ticks = Param.Tick(500, 'Pinned 2GHz CPU cycle in default gem5 tick units')
    cxx_exports = [PyBindMethod('dumpSeu')]


class FiniteTAGE(TAGE):
    type = 'FiniteTAGE'
    cxx_class = 'bp::CpuFiniteTAGE'
    cxx_header = 'cpu/pred/finite_tage.hh'
    tage = FiniteTAGEBase()
