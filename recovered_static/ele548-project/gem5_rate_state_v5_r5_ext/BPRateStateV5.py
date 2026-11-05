from m5.objects.BranchPredictor import TAGE, TAGEBase
from m5.params import Param
from m5.util.pybind import PyBindMethod

class RateStateV5TAGEBase(TAGEBase):
    type = 'RateStateV5TAGEBase'
    cxx_class = 'bp::CpuRateStateV5TAGEBase'
    cxx_header = 'cpu/pred/research_rate_state_v5_tage.hh'
    representation = Param.String('recurrent','recurrent/direct/geometric/stratum/short32')
    tap_budget = Param.Unsigned(8,'Fixed per-bank history taps')
    lookup_latency = Param.Unsigned(0,'Additional finite lookup response cycles; zero is isolation diagnostic')
    lookup_ii = Param.Unsigned(1,'Lookup engine initiation interval in CPU cycles')
    journal_service = Param.Bool(False,'Finite raw-journal append/rollback publication; false only for isolation diagnostic')
    journal_merge_undo = Param.Bool(False,'One bounded rewind packet at an actual BPU squash boundary')
    undo_batch_latency = Param.Unsigned(2,'Assumed batch rewind latency1/2; primary is2, not physical measurement')
    promotion_group = Param.Unsigned(3,'Static safe promotion grouping:0 ALL130,1 EARLY,2 LATE,3 THREE')
    sham_wait = Param.Bool(False,'Clean-only P0 periodic-response timing diagnostic; no detection')
    audit_file = Param.String('','Diagnostic committed dynamic identity/branch read provenance')
    audit_limit = Param.Unsigned(20000,'Maximum committed branch rows; full identity hash retained')
    inspection_interval = Param.Unsigned(0, 'Optional continuation ED history-update interval,1..64;0 is legacy')
    role_policy = Param.String('LEGACY', 'LEGACY/N1/H1/REV')
    maintenance_cycles = Param.Unsigned(0, 'Finite queued history maintenance service cycles,0 same-stage hypothesis')
    resource_mode = Param.String('LEGACY','LEGACY/SHARED1/SPLIT2/SHARED2 dependent RMW endpoint')
    decouple_shadow = Param.Bool(False,'Independent finite actual-commit shadow queue')
    rmw_latency = Param.Unsigned(1,'Service latency before functional sampling/publication')
    rmw_ii = Param.Unsigned(1,'Initiation interval; source dependence may limit throughput')
    hot_queue_depth = Param.Unsigned(64,'Finite source/history request capacity')
    shadow_queue_depth = Param.Unsigned(8,'Finite actual-commit shadow capacity')
    cost_remove = Param.String('NONE','ORACLE_COST removal: NONE/SPEC_SOURCE/COMMIT_SHADOW/FOLD_CHECK/RECOVERY/ALL')
    full_delta = Param.Bool(False,'Matched full-delta maintenance backend')
    reset_recovery = Param.Bool(False,'Controlled reset instead of H1 rebuild')
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

class RateStateV5TAGE(TAGE):
    type = 'RateStateV5TAGE'
    cxx_class = 'bp::CpuRateStateV5TAGE'
    cxx_header = 'cpu/pred/research_rate_state_v5_tage.hh'
    tage = RateStateV5TAGEBase()
