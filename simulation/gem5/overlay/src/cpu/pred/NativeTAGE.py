"""Ordinary unprotected TAGE with external XOR and read-only observations."""
from m5.objects.BranchPredictor import TAGE, TAGEBase
from m5.params import Param
from m5.util.pybind import PyBindMethod


class NativeTAGEBase(TAGEBase):
    type = 'NativeTAGEBase'
    cxx_class = 'bp::NativeTAGEBase'
    cxx_header = 'cpu/pred/native_tage.hh'
    schedule_file = Param.String('', 'Explicit ticks and atomic logical sites; no periodic polling')
    event_file = Param.String('', 'Actual injection log')
    summary_file = Param.String('', 'Architectural-exit observations')
    manifest_file = Param.String('', 'Supported logical targets; not a whole-state certificate')
    origin_file = Param.String('', 'Original raw-bit provenance under append/undo/rollover')
    cxx_exports = [PyBindMethod('dumpResearch')]


class NativeTAGE(TAGE):
    type = 'NativeTAGE'
    cxx_class = 'bp::NativeTAGE'
    cxx_header = 'cpu/pred/native_tage.hh'
    tage = NativeTAGEBase()
    commit_trace_file = Param.String('', 'Gzip committed branch times and consumed source snapshots')
