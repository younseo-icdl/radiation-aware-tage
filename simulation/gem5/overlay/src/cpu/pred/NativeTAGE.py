"""Ordinary unprotected TAGE with external XOR and read-only observations."""
from m5.objects.BranchPredictor import TAGE, TAGEBase, ConditionalPredictor
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
    history_protection = Param.String('none', 'Active history protection: none, ecc_halt, ecc_refill, or tmr')
    direct_queries = Param.Bool(False, 'Derive consumed folds directly from current raw history')
    direct_bank_mask = Param.Unsigned(0, 'Static whole-bank direct mask, bits0..6')
    lease_period = Param.Unsigned(0, 'Actual speculative raw appends between quiescent rebases; zero disables')
    lease_latency_ticks = Param.Tick(1000, 'Charged quiescent canonical service time, not measured PPA')
    lease_log_file = Param.String('', 'Actual autonomous lease start/publish event trace')
    history_activity_file = Param.String('', 'Optional ordered history operations for activity replay')
    history_activity_end_tick = Param.Tick(0, 'Exclusive end tick of the activity capture')
    cxx_exports = [PyBindMethod('dumpResearch')]


class NativeTAGE(TAGE):
    type = 'NativeTAGE'
    cxx_class = 'bp::NativeTAGE'
    cxx_header = 'cpu/pred/native_tage.hh'
    tage = NativeTAGEBase()
    commit_trace_file = Param.String('', 'Gzip committed branch times and consumed source snapshots')
    query_latency = Param.Unsigned(0, 'Additional conditional-query latency, in CPU cycles')
    query_ii_cycles = Param.Unsigned(0, 'Optional minimum interval between issued conditional queries')
    query_pipeline = Param.Bool(False, 'Register conditional query indices and tags before row selection')
    single_training_port = Param.Bool(False, 'Admit at most one conditional branch training per cycle')
    row_activity_file = Param.String('', 'Bounded returned-row and target input activity for staged queries')
    cycle_ticks = Param.Unsigned(500, 'CPU clock period in simulator ticks')
    force_base = Param.Bool(False, 'Diagnostic: force base output while retaining TAGE internals')
    max_restore_owners = Param.Unsigned(512, 'Declared finite history-owner capacity, asserted and measured')


class BimodalMin(ConditionalPredictor):
    type = 'BimodalMin'
    cxx_class = 'bp::BimodalMin'
    cxx_header = 'cpu/pred/bimodal_min.hh'
    log_size = Param.Unsigned(13, 'PC-indexed prediction table log2 entries')
    hysteresis_ratio = Param.Unsigned(2, 'Log2 prediction/hysteresis sharing ratio')
    summary_file = Param.String('', 'Actual program-exit summary')
    fault_tick = Param.Tick(0, 'Single forced base-counter upset; zero disables')
    fault_site = Param.Unsigned(0, 'Prediction bits then shared hysteresis bits')
    cxx_exports = [PyBindMethod('dumpResearch')]
