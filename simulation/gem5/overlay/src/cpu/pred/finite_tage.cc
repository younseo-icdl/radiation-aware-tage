#include "cpu/pred/finite_tage.hh"
#include "cpu/o3/bac.hh"
#include "cpu/pred/bpred_unit.hh"
#include "base/logging.hh"
#include <sstream>
#include <iomanip>
namespace bp {
static pipeline::Mode mode(const std::string &s) {
    if (s == "recurrent")
        return pipeline::Mode::Recurrent;
    if (s == "direct")
        return pipeline::Mode::Direct;
    if (s == "overwrite")
        return pipeline::Mode::Overwrite;
    throw std::invalid_argument("supported source representations: recurrent/direct");
}
CpuFiniteTAGEBase::CpuFiniteTAGEBase(const gem5::FiniteTAGEBaseParams &p)
    : pipeline::SourceAccess<RoundAccess>(p), mode_(mode(p.representation)),
      update_L_(p.rmw_latency), query_L_(p.pipeline_latency), early_enabled_(p.early_unconditional),
      summary_path_(p.summary_file), manifest_path_(p.manifest_file), scheme_name_(p.scheme),
      schedule_path_(p.schedule_file), event_path_(p.event_log), inspection_(p.inspection_interval),
      injection_([this] { inject_next(); }, name() + ".logical_SEU", false,
                 gem5::Event::CPU_Tick_Pri - 1),
      clock_([this] { run_clock(); }, name() + ".finite_protection", false,
             gem5::Event::CPU_Tick_Pri - 2),
      period(p.cycle_ticks) {
    fatal_if(period != 500 || p.numThreads != 1 || !p.speculativeHistUpdate || p.takenOnlyHistory ||
                 p.pipeline_ii != 1 || p.rmw_ii != 1,
             "common finite pipeline contract");
    fatal_if(
        (p.scheme != "P0" && p.scheme != "P_ED" && p.scheme != "P_ECC" && p.scheme != "P_TMR") ||
            (inspection_ && !(p.scheme == "P_ED" && inspection_ == 64)) ||
            (mode_ == pipeline::Mode::Direct && p.scheme != "P0") ||
            mode_ == pipeline::Mode::Overwrite,
        "fixed six-method scope");
}
CpuFiniteTAGEBase::~CpuFiniteTAGEBase() {
    if (clock_.scheduled())
        deschedule(clock_);
    if (injection_.scheduled())
        deschedule(injection_);
}
void CpuFiniteTAGEBase::init() {
    pipeline::SourceAccess<RoundAccess>::init();
    configure(mode_, update_L_, query_L_);
    auto protect = scheme_name_ == "P_ED"
                       ? (inspection_ ? pipeline::Protect::Periodic : pipeline::Protect::Parity)
                   : scheme_name_ == "P_ECC" ? pipeline::Protect::Ecc
                   : scheme_name_ == "P_TMR" ? pipeline::Protect::Tmr
                                             : pipeline::Protect::P0;
    enable_protection(protect, mode_);
    if (early_enabled_)
        enable_early();
    write_manifest();
    load_faults();
}
void CpuFiniteTAGEBase::startup() {
    fatal_if(gem5::curTick() != 0,
             "finite TAGE requires tick0 reset; checkpoint import not implemented");
    schedule(clock_, period);
    if (!faults_.empty())
        schedule(injection_, faults_[0].tick);
}
void CpuFiniteTAGEBase::run_clock() {
    advance();
    auto *g = protection();
    auto &ps = g->unit.stats;
    bool fallback = g->fallback();
    if (detector_output_ && (ps.detected != previous_detected_ || ps.resets != previous_resets_ ||
                             fallback != previous_fallback_)) {
        detector_output_ << gem5::curTick() << ',' << ps.detected << ',' << ps.corrected << ','
                         << ps.due << ',' << ps.resets << ',' << g->unit.epoch() << ','
                         << g->unit.refill_remaining() << ',' << fallback << '\n';
        detector_output_.flush();
    }
    previous_detected_ = ps.detected;
    previous_resets_ = ps.resets;
    previous_fallback_ = fallback;

    // OBSERVATION_BEGIN
    max_lookup_pending = std::max(max_lookup_pending, engine->port.pending());
    max_source_pending = std::max(max_source_pending, engine->port.source.pending());
    // OBSERVATION_END
    schedule(clock_, gem5::curTick() + period);
}
size_t CpuFiniteTAGEBase::table_bits() const {
    auto all = sites();
    size_t n = 0;
    for (auto &s : all)
        if (s.kind < 4)
            ++n;
    return n;
}
bool CpuFiniteTAGEBase::logical_bit(size_t id) const {
    auto all = sites();
    auto n = table_bits();
    if (id < n) {
        const auto &s = all[id];
        return (payload(s) >> s.bit) & 1;
    }
    return model_bit(id - n);
}
void CpuFiniteTAGEBase::corrupt(const std::vector<size_t> &ids) {
    auto n = table_bits();
    std::set<size_t> unique;
    std::vector<size_t> table, source;
    for (auto id : ids) {
        if (id >= n + model_bits() || !unique.insert(id).second)
            throw std::invalid_argument("invalid finite TAGE atomic logical fault sites");
        (id < n ? table : source).push_back(id < n ? id : id - n);
    }
    RoundAccess::corrupt(table);
    corrupt_model(source);
}
void CpuFiniteTAGEBase::write_manifest() {
    if (manifest_path_.empty())
        return;
    std::ofstream out(manifest_path_);
    fatal_if(!out, "finite TAGE manifest output unavailable");
    auto n = table_bits();
    out << "{\"scheme\":\"" << scheme_name_ << "\",\"inspection_interval\":" << inspection_
        << ",\"protection_check_L\":1,\"encode_L\":1,\"repair_holding_capacity\":1,\"word_widths\":"
           "[";
    auto widths = engine->port.source.selected_widths();
    for (unsigned w = 0; w < 23; ++w)
        out << (w ? "," : "") << widths[w];
    out << "],\"model\":\"V18_COMMON_FINITE_PROTECTION\",\"scope\":\"predictor tables plus finite "
           "source/controller; original allocator/RNG/CPU architectural storage "
           "excluded\",\"table_bits\":"
        << n << ",\"total_logical_bits\":" << n + model_bits()
        << ",\"source_update_L\":" << (mode_ == pipeline::Mode::Direct ? 1 : update_L_)
        << ",\"source_query_L\":" << query_L_
        << ",\"early_unconditional\":" << (early ? "true" : "false")
        << ",\"early_checkpoint_bits\":" << (early ? early->bits() : 0)
        << ",\"provider_extra_L\":1,\"II\":1,\"ingress_capacity\":4,\"squash_reserved_commands\":2,"
           "\"regions\":[{\"name\":\"original_logical_tables_in_pinned_Site_order\",\"start\":0,"
           "\"bits\":"
        << n << '}';
    for (auto &r : model_manifest())
        out << ",{\"name\":\"" << r.name << "\",\"start\":" << n + r.start << ",\"bits\":" << r.bits
            << '}';
    out << "],\"clock\":\"free-running actual gem5 events from reset; registered vector check then "
           "source reduction/provider; actual encoder uses same finite "
           "unit\",\"squash_backpressure\":\"when incoming commit/decode squash cannot reserve two "
           "ingress cells, hold all O3 stages and existing time buffers; source/cache events "
           "continue; conservative global recovery hold; claimed late checkpoints finish before "
           "source cancellation/squash\",\"retirement\":\"one actual credit release per cycle; "
           "recovery-tagged source ACKs and every claimed late path checkpoint must complete "
           "before release\",\"source_interface\":\"1130bit retained register ring with actual "
           "pre/post130 taps; not one-port SRAM\",\"exclusions\":[\"provider helper history arrays "
           "are combinational operands only\",\"host pointer associations to four token-bound "
           "CPU-owned BranchInfo objects; binding token/PC/valid is included; CPU-owned "
           "BranchInfo/expected-token/BTB/RAS and original time-buffer/architectural state; no "
           "extra squash message copy\",\"absolute software cycle/hold helpers, elaboration "
           "constants and diagnostic counters\",\"old native allocator/aging/RNG metadata and "
           "combinational SET\"],\"assumptions\":[\"declared source L1/2 and provider1 are model "
           "timing, not measured clock\",\"shared23-lane vector check/encode and mirrored metadata "
           "stage fit assumed; one decoded repair holding slot; unprotected retention reentry is "
           "not codec repair\"],\"not_implemented\":[\"checkpoint "
           "restore\",\"decoupled/multithread frontend\"]}\n";
}
void CpuFiniteTAGEBase::dumpSeu() {
    if (!faults_frozen_) {
        faults_frozen_ = true;
        censor_tick_ = gem5::curTick();
        if (injection_.scheduled())
            deschedule(injection_);
    }
    if (summary_path_.empty())
        return;
    std::ofstream out(summary_path_);
    fatal_if(!out, "finite TAGE summary unavailable");
    auto &s = engine->port.source.stats;
    auto *g = protection();
    const auto &ps = g->unit.stats;
    out << "{\"protection_pipeline_drained\":" << (g->drained() ? "true" : "false")
        << ",\"protection_metadata_repairs\":" << ps.metadata_repairs + g->metadata_repairs << ',';
    out << "\"scheme\":\"" << scheme_name_ << "\",\"inspection_interval\":" << inspection_
        << ",\"applied_events\":" << applied_events_ << ",\"applied_flips\":" << applied_flips_
        << ",\"scheduled_events\":" << faults_.size()
        << ",\"future_events_censored\":" << faults_.size() - fault_index_
        << ",\"censor_tick\":" << censor_tick_
        << ",\"faults_frozen\":" << (faults_frozen_ ? "true" : "false")
        << ",\"protection_checks\":" << ps.inspected << ",\"protection_encodes\":" << ps.encoded
        << ",\"protection_detected\":" << ps.detected
        << ",\"protection_corrected\":" << ps.corrected << ",\"protection_DUE\":" << ps.due
        << ",\"protection_resets\":" << ps.resets << ",\"protection_epoch\":" << g->unit.epoch()
        << ",\"refill_remaining\":" << g->unit.refill_remaining()
        << ",\"protection_fallback\":" << (g->fallback() ? "true" : "false")
        << ",\"protection_unit_busy\":" << ps.unit_busy
        << ",\"protection_sidecar_reads\":" << ps.sidecar_reads
        << ",\"protection_sidecar_writes\":" << ps.sidecar_writes
        << ",\"protection_source_repairs\":" << g->source_repair_publications
        << ",\"stale_source_ops_suppressed\":" << g->suppressed_stale_source_ops
        << ",\"stale_training_suppressed\":" << stale_training_suppressed
        << ",\"stale_provider_reissued\":" << engine->port.stale_protection_responses
        << ",\"committed_refill_publications\":" << g->committed_refill_publications
        << ",\"refill_drains\":" << refill_drains
        << ",\"unverified_retention_reentries\":" << s.unverified_retention_reentries << ',';
    out << "\"early_enabled\":" << (early ? "true" : "false")
        << ",\"early_claimed\":" << (early ? early->claims : 0)
        << ",\"early_delivered\":" << (early ? early->delivered : 0)
        << ",\"early_pending\":" << (early ? early->pending() : 0)
        << ",\"early_metadata_repairs\":" << (early ? early->metadata_repairs : 0)
        << ",\"early_cancel_requests\":" << (early ? early->deferred_cancels : 0)
        << ",\"early_retire_wait_calls\":" << early_retire_wait_calls << ',';
    // OBSERVATION_BEGIN
    out << "\"max_lookup_pending\":" << max_lookup_pending
        << ",\"max_source_pending\":" << max_source_pending
        << ",\"retire_recovery_wait_calls\":" << retire_recovery_wait_calls
        << ",\"retire_credit_decode_wait_calls\":" << retire_credit_decode_wait_calls << ',';
    // OBSERVATION_END
    out << "\"model\":\"FINITE_PROTECTED_SOURCE\",\"representation\":\""
        << (mode_ == pipeline::Mode::Recurrent ? "recurrent"
            : mode_ == pipeline::Mode::Direct  ? "direct"
                                               : "overwrite")
        << "\",\"tick\":" << gem5::curTick() << ",\"source_cycles\":" << engine->port.source.cycle()
        << ",\"lookups\":" << lookups << ",\"read_stalls\":" << read_stalls
        << ",\"recovery_core_hold_cycles\":" << recovery_hold_cycles
        << ",\"ingress_enqueued\":" << engine->enqueued << ",\"ingress_issued\":" << engine->issued
        << ",\"ingress_max_count\":" << engine->max_count
        << ",\"recovery_admission_waits\":" << engine->recovery_waits
        << ",\"source_issue_waits\":" << engine->source_issue_waits
        << ",\"read_ingress_waits\":" << engine->read_ingress_waits
        << ",\"source_accepted\":" << s.accepted << ",\"source_completed\":" << s.completed
        << ",\"source_cancelled\":" << s.cancelled
        << ",\"source_pending\":" << engine->port.source.pending()
        << ",\"source_dependency_stalls\":" << s.dependency_stalls
        << ",\"source_ordering_stalls\":" << s.ordering_stalls
        << ",\"source_queue_stalls\":" << s.input_full_stalls
        << ",\"source_response_stalls\":" << s.response_stalls
        << ",\"source_II_stalls\":" << s.II_stalls << ",\"bulk_undos\":" << s.bulk_undos
        << ",\"bulk_bits\":" << s.bulk_bits << ",\"metadata_repairs\":"
        << s.metadata_repairs + engine->metadata_repairs + engine->port.metadata_repairs +
               (early ? early->metadata_repairs : 0)
        << ",\"wrap_completions\":" << s.wrap_completions
        << ",\"lookup_accepted\":" << engine->port.accepted
        << ",\"lookup_produced\":" << engine->port.produced
        << ",\"lookup_consumed\":" << engine->port.consumed
        << ",\"lookup_cancelled\":" << engine->port.cancelled
        << ",\"lookup_pending\":" << engine->port.pending()
        << ",\"predictor_rng_draws\":" << predictor_rng_draws
        << ",\"predictor_rng_hash\":" << predictor_rng_hash
        << ",\"committed_ops\":" << committed_ops
        << ",\"committed_controls\":" << committed_controls
        << ",\"committed_identity\":" << committed_identity
        << ",\"conserved\":" << (conserved() ? "true" : "false")
        << ",\"applied_faults\":" << applied_events_
        << ",\"timing_qualification\":\"MODEL_ONLY\"}\n";
}
CpuFiniteTAGE::CpuFiniteTAGE(const gem5::FiniteTAGEParams &p)
    : TAGE(p), core(*dynamic_cast<CpuFiniteTAGEBase *>(p.tage)) {}
bool CpuFiniteTAGE::seuFrontendBlocked(gem5::ThreadID tid, bool actual_history_empty) {
    fatal_if(tid, "finite TAGE single thread");
    return core.frontend_blocked(actual_history_empty);
}
bool CpuFiniteTAGE::seuPredictionRequest(gem5::ThreadID tid, gem5::Addr pc, bool conditional,
                                         uint32_t &token) {
    if (!token && core.refill_complete()) {
        ++core.read_stalls;
        return false;
    }
    fatal_if(tid, "finite TAGE single thread");
    if (!token) {
        auto t = core.request(pc, conditional);
        if (!t) {
            ++core.read_stalls;
            return false;
        }
        token = t->packed();
        core.max_lookup_pending = std::max(core.max_lookup_pending, core.engine->port.pending());
        core.max_source_pending =
            std::max(core.max_source_pending, core.engine->port.source.pending());
    }
    if (core.early && !core.early->ready()) {
        ++core.read_stalls;
        return false;
    }
    if (!conditional && core.early_ready(pipeline::Token::unpack(token), pc))
        return true;
    auto r = core.engine->peek(pipeline::Token::unpack(token));
    if (!r) {
        ++core.read_stalls;
        return false;
    }
    fatal_if(r->pc != pc || r->conditional != conditional,
             "finite TAGE actual PC/type response ownership");
    return true;
}
bool CpuFiniteTAGE::seuPredictionReady(gem5::ThreadID tid, gem5::Addr pc, bool conditional) {
    fatal_if(tid, "finite TAGE single thread");
    if (core.early) {
        if (!core.early->ready())
            return false;
        if (!conditional) {
            for (const auto &d : core.engine->port.descriptors())
                if (core.early_ready(d.token, pc))
                    return true;
            return false;
        }
    }
    auto r = core.engine->head();
    return r && r->pc == pc && r->conditional == conditional;
}
bool CpuFiniteTAGE::predict(gem5::ThreadID tid, gem5::Addr pc, bool conditional, void *&history) {
    fatal_if(tid || history, "finite TAGE response consumer");
    if (!conditional && core.early) {
        auto *info = new TageBranchInfo(core, pc, false);
        core.consume_early(pc, info->tageBranchInfo);
        history = info;
        ++core.lookups;
        return true;
    }
    auto r = core.engine->head();
    fatal_if(!r || r->pc != pc || r->conditional != conditional,
             "finite TAGE response not actually ready");
    auto out = core.engine->take(r->token);
    fatal_if(!out, "finite TAGE response disappeared within non-yielding consume");
    auto *info = new TageBranchInfo(core, pc, conditional);
    out->payload.restore_response(*info->tageBranchInfo);
    info->tageBranchInfo->pathHist = out->path;
    history = info;
    ++core.lookups;
    return out->payload.get(25);
}
void CpuFiniteTAGE::seuCancelPending(gem5::ThreadID tid) {
    fatal_if(tid, "finite TAGE single thread");
    core.cancel();
}
void CpuFiniteTAGE::seuSquashBegin(gem5::ThreadID tid) {
    fatal_if(tid, "finite TAGE single thread");
    core.engine->begin();
}
void CpuFiniteTAGE::seuSquashEnd(gem5::ThreadID tid) {
    fatal_if(tid, "finite TAGE single thread");
    core.engine->end();
}
bool CpuFiniteTAGE::seuPipelineDrained() const { return core.engine && core.drained(); }
bool CpuFiniteTAGE::seuCanRetire(gem5::ThreadID tid, void *history) {
    fatal_if(tid, "finite TAGE single thread");
    if (!history)
        return true;
    const bool ready =
        core.can_retire(static_cast<TageBranchInfo *>(history)->tageBranchInfo->nGhist);
    // OBSERVATION_BEGIN
    if (!ready) {
        if (core.early && !core.early->quiescent())
            ++core.early_retire_wait_calls;
        else if (core.engine->diagnostic_recovery_waiting())
            ++core.retire_recovery_wait_calls;
        else
            ++core.retire_credit_decode_wait_calls;
    }
    // OBSERVATION_END
    return ready;
}
void CpuFiniteTAGE::seuReserveRetire(gem5::ThreadID tid, void *history) {
    fatal_if(tid, "finite TAGE single thread");
    if (history)
        fatal_if(!core.retire(static_cast<TageBranchInfo *>(history)->tageBranchInfo->nGhist),
                 "finite TAGE retirement without actual source credit");
}
void CpuFiniteTAGE::retireOutcome(gem5::ThreadID tid, void *history, bool actual, gem5::Addr pc) {
    fatal_if(tid, "finite TAGE single-thread retirement");
    if (!history)
        return;
    auto *info = static_cast<TageBranchInfo *>(history);
    fatal_if(!core.retire_with_outcome(info->tageBranchInfo->nGhist, actual, pc),
             "finite TAGE retirement without same-cycle source/ingress credit");
}
void finiteRetireOutcome(gem5::branch_prediction::ConditionalPredictor *predictor,
                         gem5::ThreadID tid, void *history, bool actual, gem5::Addr pc) {
    if (auto *finite = dynamic_cast<CpuFiniteTAGE *>(predictor))
        finite->retireOutcome(tid, history, actual, pc);
    else
        predictor->seuReserveRetire(tid, history);
}
void CpuFiniteTAGE::update(gem5::ThreadID tid, gem5::Addr pc, bool taken, void *&history,
                           bool squashed, const gem5::StaticInstPtr &inst, gem5::Addr target) {
    fatal_if(!history, "finite TAGE training has no owned BI");
    auto *info = static_cast<TageBranchInfo *>(history);
    auto *bi = info->tageBranchInfo;
    if (squashed) {
        core.squash(tid, taken, target, inst, bi);
        return;
    }
    int draw = rng->random<int>() & 3;
    ++core.predictor_rng_draws;
    core.predictor_rng_hash ^= uint64_t(draw);
    core.predictor_rng_hash *= 1099511628211ULL;
    if (bi->condBranch) {
        core.updateStats(taken, bi);
        core.condBranchUpdate(tid, pc, taken, bi, draw, target, bi->tagePred);
    }
    core.updateHistories(tid, pc, false, taken, target, inst, bi);
    delete info;
    history = nullptr;
}
void CpuFiniteTAGE::seuAuditCommit(uint64_t, uint64_t pc, unsigned micro, bool last, bool control,
                                   void *) {
    ++core.committed_ops;
    core.committed_controls += control;
    for (uint64_t value : {pc, uint64_t(micro), uint64_t(last), uint64_t(control)}) {
        core.committed_identity ^= value;
        core.committed_identity *= 1099511628211ULL;
    }
}
void CpuFiniteTAGE::branchPlaceholder(gem5::ThreadID, gem5::Addr, bool, void *&) {
    fatal("finite TAGE decoupled frontend not supported");
}

void CpuFiniteTAGEBase::load_faults() {
    if (!event_path_.empty()) {
        event_output_.open(event_path_);
        fatal_if(!event_output_, "finite TAGE event log unavailable");
        event_output_ << "event,tick,token,logical_id,before,after,conditional_gate,stage_phase,"
                         "stage_lookup,lower_tick\n";
        detector_output_.open(event_path_ + ".detector.csv");
        fatal_if(!detector_output_, "finite TAGE detector log unavailable");
        detector_output_ << "tick,detected,corrected,due,resets,epoch,refill,fallback\n";
    }
    if (schedule_path_.empty())
        return;
    std::ifstream in(schedule_path_);
    fatal_if(!in, "finite TAGE schedule unavailable");
    std::string line;
    gem5::Tick previous = 0;
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#')
            continue;
        std::istringstream input(line);
        Fault f;
        std::string sites, extra;
        fatal_if(!(input >> f.tick >> sites) || bool(input >> extra) || !f.tick ||
                     f.tick < previous,
                 "finite TAGE malformed schedule");
        previous = f.tick;
        f.lower_tick = f.tick;
        std::stringstream tokens(sites);
        std::string token;
        while (std::getline(tokens, token, ';')) {
            fatal_if(token.empty(), "finite TAGE empty event site");
            if (token.rfind("G1R:", 0) == 0 || token.rfind("GU:", 0) == 0)
                f.gated = true;
            f.sites.push_back(token);
        }
        fatal_if(f.sites.empty(), "finite TAGE empty atomic event");
        faults_.push_back(std::move(f));
    }
}
size_t CpuFiniteTAGEBase::resolve_site(const std::string &token) const {
    if (token.rfind("G1R:", 0) == 0)
        return resolve_site(token.substr(4));
    if (token.rfind("GU:", 0) == 0)
        return resolve_site(token.substr(3));
    const size_t n = table_bits();
    if (token[0] == 'R') {
        size_t used = 0;
        auto age = std::stoul(token.substr(1), &used);
        fatal_if(used != token.size() - 1 || age >= 130, "finite TAGE invalid raw-age alias");
        return n + engine->port.source.active_raw_site(age);
    }
    if (token[0] == 'W') {
        auto colon = token.find(':');
        fatal_if(colon == std::string::npos, "finite TAGE invalid S* word alias");
        size_t a = 0, b = 0;
        auto word = std::stoul(token.substr(1, colon - 1), &a),
             bit = std::stoul(token.substr(colon + 1), &b);
        auto widths = engine->port.source.selected_widths();
        fatal_if(a != colon - 1 || b != token.size() - colon - 1 || word >= 23 ||
                     bit >= widths[word],
                 "finite TAGE invalid canonical word bit");
        if (word == 21)
            return n + engine->port.source.active_raw_site(bit);
        if (word == 22)
            return n + 1130 + bit;
        fatal_if(mode_ == pipeline::Mode::Direct, "finite TAGE Direct has no stored fold");
        size_t id = n + 1146;
        for (unsigned w = 0; w < word; ++w)
            id += widths[w];
        return id + bit;
    }
    size_t used = 0;
    auto id = std::stoull(token, &used);
    fatal_if(used != token.size() || id >= n + model_bits(),
             "finite TAGE invalid physical logical site");
    return id;
}
void CpuFiniteTAGEBase::inject_next() {
    fatal_if(faults_frozen_ || fault_index_ >= faults_.size() ||
                 faults_[fault_index_].tick != gem5::curTick(),
             "finite TAGE injection lifecycle");
    auto &f = faults_[fault_index_];
    unsigned phase = unsigned(protection()->unit.logical_bit(0)) |
                     (unsigned(protection()->unit.logical_bit(1)) << 1);
    bool lookup = protection()->unit.logical_bit(144);
    const bool late = f.sites[0].rfind("GU:", 0) == 0;
    const bool publication_pending = protection()->logical_bit(protection()->unit.bits());
    if (f.gated && (late ? (phase != 0 || !publication_pending) : (phase != 1 || lookup))) {
        f.tick = ((gem5::curTick() / period) + 1) * period + 1;
        schedule(injection_, f.tick);
        return;
    }
    std::vector<size_t> ids;
    std::vector<bool> before;
    std::set<size_t> unique;
    for (auto &token : f.sites) {
        auto id = resolve_site(token);
        fatal_if(!unique.insert(id).second,
                 "finite TAGE duplicate physical bit in one atomic event");
        ids.push_back(id);
        before.push_back(logical_bit(id));
    }
    corrupt(ids);
    for (unsigned i = 0; i < ids.size(); ++i) {
        bool after = logical_bit(ids[i]);
        fatal_if(after == before[i], "finite TAGE XOR event did not change logical bit");
        if (event_output_)
            event_output_ << applied_events_ << ',' << gem5::curTick() << ',' << f.sites[i] << ','
                          << ids[i] << ',' << before[i] << ',' << after << ',' << f.gated << ','
                          << phase << ',' << lookup << ',' << f.lower_tick << '\n';
    }
    if (event_output_)
        event_output_.flush();
    ++applied_events_;
    applied_flips_ += ids.size();
    ++fault_index_;
    if (fault_index_ < faults_.size()) {
        auto &next = faults_[fault_index_];
        if (next.gated && next.tick <= gem5::curTick())
            next.tick = gem5::curTick() + 1;
        schedule(injection_, next.tick);
    }
}
} // namespace bp
namespace bp::frontend {
bool RecoveryBridge::ready(gem5::o3::BAC &bac) {
    auto *pred = dynamic_cast<bp::CpuFiniteTAGE *>(bac.bpu->cPred);
    if (!pred)
        return true;
    fatal_if(bac.numThreads != 1 || bac.decoupledFrontEnd,
             "finite TAGE requires one thread coupled frontend");
    bool incoming = bac.fromCommit->commitInfo[0].squash || bac.fromDecode->decodeInfo[0].squash;
    if (!incoming)
        return true;
    if (!pred->core.prepare_recovery()) {
        ++pred->core.recovery_hold_cycles;
        return false;
    }
    return true;
}
} // namespace bp::frontend
