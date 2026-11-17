#include "cpu/pred/native_tage.hh"
#include "sim/cur_tick.hh"
#include <algorithm>
#include <sstream>
#include <stdexcept>

namespace bp {
namespace {
uint64_t integer(const std::string &text) {
    size_t end = 0;
    if (text.empty() || text[0] == '-') throw std::invalid_argument("invalid unsigned integer");
    auto value = std::stoull(text, &end, 0);
    if (end != text.size()) throw std::invalid_argument("invalid unsigned integer");
    return value;
}
void mix(uint64_t &hash, uint64_t value) { hash = (hash ^ value) * 1099511628211ULL; }
template <class T> void list(std::ostream &out, const std::vector<T> &values) {
    for (size_t i = 0; i < values.size(); ++i) {
        if (i) out << ';';
        out << values[i];
    }
}
} // namespace

NativeTAGEBase::NativeTAGEBase(const gem5::NativeTAGEBaseParams &p)
    : DirectAccess<TageAccess>(p), schedule_path_(p.schedule_file), event_path_(p.event_file),
      summary_path_(p.summary_file), manifest_path_(p.manifest_file),
      injection_([this] { injectNext(); }, name()+".native_xor", false,
                 gem5::Event::CPU_Tick_Pri-1) {
    if (p.numThreads != 1) throw std::invalid_argument("native observation currently supports one thread");
    direct_queries = p.direct_queries;
    if (!p.origin_file.empty()) {
        origins_.open(p.origin_file);
        if (!origins_) throw std::runtime_error("cannot open raw origin trace");
        origins_ << "callback_ordinal,tick,raw_history_writes,conditional_history_writes,"
            "active_origin_bits,restorable_origin_bits,head,buffer_epoch,reason\n";
    }
}
NativeTAGEBase::~NativeTAGEBase() {
    if (injection_.scheduled()) deschedule(injection_);
}
void NativeTAGEBase::init() {
    Base::init();
    sites_ = sites();
    words_ = history_words();
    loadFaults();
    if (!event_path_.empty()) {
        events_.open(event_path_);
        if (!events_) throw std::runtime_error("cannot open injection trace");
        events_ << "event_ordinal,requested_tick,applied_tick,multiplicity,logical_site_ids,raw_physical_indices\n";
    }
    writeManifest();
}
void NativeTAGEBase::startup() {
    Base::startup();
    observeOrigins("startup", true);
    if (!faults_.empty()) schedule(injection_, faults_[0].tick);
}
void NativeTAGEBase::loadFaults() {
    if (schedule_path_.empty()) return;
    std::ifstream in(schedule_path_);
    if (!in) throw std::runtime_error("cannot open native fault schedule");
    bool ticks_declared = false;
    std::string line;
    gem5::Tick previous = 0;
    while (std::getline(in, line)) {
        if (line.empty()) continue;
        if (line[0] == '#') {
            auto pos = line.find("time_unit=");
            if (pos != std::string::npos) {
                std::istringstream header(line.substr(pos));
                std::string unit; header >> unit;
                if (unit != "time_unit=ticks") throw std::invalid_argument("native injector requires ticks");
                ticks_declared = true;
            }
            continue;
        }
        std::istringstream row(line);
        std::string tick, marks, extra;
        if (!(row >> tick >> marks) || row >> extra) throw std::invalid_argument("expected tick and sites");
        Fault fault{integer(tick), {}};
        if (!fault.tick || fault.tick < previous) throw std::invalid_argument("unordered native events");
        previous = fault.tick;
        std::istringstream mark_stream(marks);
        std::string mark;
        std::set<size_t> unique;
        while (std::getline(mark_stream, mark, ';')) {
            if (!unique.insert(resolve(mark)).second) throw std::invalid_argument("duplicate atomic site");
            fault.sites.push_back(mark);
        }
        if (fault.sites.empty() || marks.back() == ';') throw std::invalid_argument("empty atomic group");
        faults_.push_back(std::move(fault));
    }
    if (!ticks_declared) throw std::invalid_argument("schedule must explicitly declare time_unit=ticks");
}
size_t NativeTAGEBase::resolve(const std::string &mark) const {
    if (mark.empty()) throw std::invalid_argument("empty site");
    if (mark[0] == 'R') {
        auto age = integer(mark.substr(1));
        if (age >= maxHist) throw std::out_of_range("raw age");
        return words_[nHistoryTables*3].sites.at(age);
    }
    if (mark[0] == 'W') {
        auto colon = mark.find(':');
        if (colon == std::string::npos) throw std::invalid_argument("expected W<word>:<bit>");
        auto word = integer(mark.substr(1, colon-1)), bit = integer(mark.substr(colon+1));
        if (word >= words_.size() || bit >= words_[word].width) throw std::out_of_range("history site");
        return words_[word].sites.at(bit);
    }
    auto id = integer(mark);
    if (id >= sites_.size()) throw std::out_of_range("logical site id");
    return id;
}
void NativeTAGEBase::injectNext() {
    if (frozen_) return;
    while (next_fault_ < faults_.size() && faults_[next_fault_].tick == gem5::curTick()) {
        observeOrigins("before_injection", true);
        auto &fault = faults_[next_fault_];
        std::vector<size_t> ids;
        std::vector<int> physical;
        for (const auto &mark : fault.sites) {
            auto id = resolve(mark); ids.push_back(id);
            const auto &site = sites_[id];
            if (direct_queries && site.kind == 5)
                throw std::invalid_argument("direct has no consumed stored-fold target");
            if (site.kind == 4 && site.bank == 0)
                physical.push_back(history_cursor()+site.row);
        }
        corrupt(ids); // One validated XOR group. No fold/code refresh or detection.
        for (int cell : physical) raw_origins_[cell].insert(++origin_id_);
        if (events_) {
            events_ << next_fault_+1 << ',' << fault.tick << ',' << gem5::curTick() << ',' << ids.size() << ',';
            list(events_, ids); events_ << ','; list(events_, physical); events_ << '\n';
        }
        ++next_fault_; flips_ += ids.size();
        observeOrigins("after_injection", true);
    }
    if (next_fault_ < faults_.size()) schedule(injection_, faults_[next_fault_].tick);
}
std::set<uint64_t> NativeTAGEBase::originLabels(int head) const {
    std::set<uint64_t> result;
    for (auto i = raw_origins_.lower_bound(head); i != raw_origins_.end() && i->first < head+int(maxHist); ++i)
        result.insert(i->second.begin(), i->second.end());
    return result;
}
void NativeTAGEBase::observeOrigins(const char *reason, bool force) {
    if (!origins_ || frozen_) return;
    ++observation_ordinal_;
    if (!force && !next_fault_ && raw_origins_.empty()) return;
    auto active = originLabels(history_cursor()).size();
    auto live = owner ? owner->restorableOriginCount() : 0;
    if (!force && active == last_active_ && live == last_live_ && observation_ordinal_ % 1024) return;
    origins_ << observation_ordinal_ << ',' << gem5::curTick() << ',' << raw_writes << ','
        << conditional_writes << ',' << active << ',' << live << ',' << history_cursor() << ','
        << buffer_epoch << ',' << reason << '\n';
    last_active_ = active; last_live_ = live;
}
void NativeTAGEBase::updateGHist(gem5::ThreadID tid, uint64_t bits, uint8_t n) {
    if (n && threadHistory[tid].ptGhist < n) {
        const int old = threadHistory[tid].ptGhist;
        const int count = int(maxHist)+1000;
        const int destination = int(histBufferSize)-count;
        std::map<int, std::set<uint64_t>> copies;
        for (auto i = raw_origins_.lower_bound(old); i != raw_origins_.end() && i->first < old+count; ++i)
            copies[destination+i->first-old] = i->second;
        raw_origins_.erase(raw_origins_.lower_bound(destination), raw_origins_.end());
        for (auto &copy : copies) raw_origins_[copy.first] = std::move(copy.second);
        if (owner) owner->rebaseFrames(destination-old);
        ++buffer_epoch;
    }
    Base::updateGHist(tid, bits, n);
    if (n) {
        int head = threadHistory[tid].ptGhist;
        for (unsigned i = 0; i < n; ++i) raw_origins_.erase(head+i);
        raw_writes += n;
        if (conditional_context_) conditional_writes += n;
        ++source_epoch;
        observeOrigins("history_write");
    }
}
void NativeTAGEBase::updateHistories(gem5::ThreadID tid, gem5::Addr pc, bool speculative,
        bool taken, gem5::Addr target, const gem5::StaticInstPtr &inst, Base::BranchInfo *bi) {
    bool previous = conditional_context_;
    conditional_context_ = bi->condBranch;
    Base::updateHistories(tid, pc, speculative, taken, target, inst, bi);
    conditional_context_ = previous;
    ++source_epoch;
    observeOrigins("history_callback");
}
void NativeTAGEBase::restoreHistState(gem5::ThreadID tid, Base::BranchInfo *bi) {
    Base::restoreHistState(tid, bi);
    ++source_epoch;
    observeOrigins("restore");
}
NativeSample NativeTAGEBase::sample(const Base::BranchInfo &bi, uint64_t id) const {
    NativeSample s;
    s.lookup_id = id; s.lookup_tick = gem5::curTick(); s.epoch = source_epoch;
    s.buffer_epoch = buffer_epoch; s.head = s.restore_head = history_cursor();
    s.raw = read_history_word(nHistoryTables*3); s.path = read_history_word(nHistoryTables*3+1).limb[0];
    s.nonspec_path = nonspec_path_history();
    for (unsigned w = 0; w < nHistoryTables*3; ++w) {
        unsigned fold = direct_queries ? direct_word(w) : read_history_word(w).limb[0], canonical = 0;
        for (unsigned age = 0; age < histLengths[w/3+1]; ++age)
            if (s.raw.bit(age)) canonical ^= 1u << (age % words_[w].width);
        s.folds.push_back(fold);
        s.invariant_distance += __builtin_popcount(fold ^ canonical);
    }
    if (bi.condBranch)
        for (unsigned bank = 1; bank <= nHistoryTables; ++bank) {
            s.indices.push_back(bi.tableIndices[bank]); s.tags.push_back(bi.tableTags[bank]);
        }
    return s;
}
void NativeTAGEBase::writeManifest() const {
    if (manifest_path_.empty()) return;
    std::ofstream out(manifest_path_);
    if (!out) throw std::runtime_error("cannot open native target manifest");
    unsigned selected = 0;
    for (const auto &word : words_) selected += word.width;
    out << "{\"method\":\"" << (direct_queries ? "direct_query_TAGE" : "ordinary_unprotected_TAGE")
        << "\",\"consumed_stored_folds\":" << (direct_queries ? "false" : "true")
        << ",\"fault_coordinate\":\"ticks\","
        "\"placement\":\"logical stored fields; raw age resolves once at injection\","
        "\"physical_hardware_mapping\":\"UNKNOWN\",\"WHOLE_coverage\":false,"
        "\"excluded\":[\"head\",\"pending/checkpoint fields\",\"chooser/RNG\",\"observer storage\"],"
        "\"logical_sites\":" << sites_.size() << ",\"selected_history_bits\":" << selected << ",\"words\":[";
    for (size_t w = 0; w < words_.size(); ++w) {
        if (w) out << ',';
        out << "{\"word\":" << w << ",\"name\":\"" << words_[w].id << "\",\"width\":"
            << words_[w].width << ",\"site_ids\":[";
        for (size_t i = 0; i < words_[w].sites.size(); ++i) { if (i) out << ','; out << words_[w].sites[i]; }
        out << "]}";
    }
    out << "]}\n";
}
void NativeTAGEBase::dumpResearch() {
    if (frozen_) return;
    observeOrigins("program_exit", true);
    frozen_ = true; exit_tick_ = gem5::curTick();
    if (injection_.scheduled()) deschedule(injection_);
    if (events_) events_.flush();
    if (origins_) origins_.flush();
    if (owner) owner->flushTrace();
    if (summary_path_.empty()) return;
    uint64_t fingerprint = 14695981039346656037ULL;
    for (const auto &site : sites_) mix(fingerprint, (payload(site) >> site.bit) & 1u);
    mix(fingerprint, uint64_t(tCounter));
    for (auto value : useAltPredForNewlyAllocated) mix(fingerprint, uint8_t(value));
    std::ofstream out(summary_path_);
    if (!out) throw std::runtime_error("cannot open native summary");
    out << "{\"method\":\"" << (direct_queries ? "D_QUERY" : "U_NATIVE")
        << "\",\"protection\":\"" << (direct_queries ? "direct own-history folds" : "NONE") << "\","
        "\"target_checker_stages\":0,\"additional_lookup_hold\":" << (owner ? owner->queryLatency() : 0)
        << ",\"additional_retirement_hold\":0,"
        "\"periodic_service_clock\":false,\"tick\":" << exit_tick_
        << ",\"scheduled_events\":" << faults_.size() << ",\"applied_events\":" << next_fault_
        << ",\"applied_flips\":" << flips_ << ",\"future_events_censored\":" << faults_.size()-next_fault_
        << ",\"faults_frozen\":true,\"semantic_base_fingerprint\":" << fingerprint
        << ",\"fingerprint_scope\":\"active base state; not exhaustive checkpoint/RNG equality\","
        "\"origin_scope\":\"single-event raw identities; actual append/undo/rollover, no extra XOR\","
        "\"multi_event_recovery_partitioned\":false,\"raw_history_writes\":" << raw_writes;
    if (owner) out << ",\"lookups\":" << owner->lookups << ",\"committed_updates\":" << owner->commit_updates
        << ",\"additional_query_latency_cycles\":" << owner->queryLatency()
        << ",\"query_wait_calls\":" << owner->query_wait_calls
        << ",\"delayed_requests\":" << owner->delayed_requests
        << ",\"canceled_query_requests\":" << owner->canceled_requests
        << ",\"conditional_updates\":" << owner->conditional_updates << ",\"retired_ops\":" << owner->retired_ops
        << ",\"retired_instructions\":" << owner->retired_instructions << ",\"retired_controls\":" << owner->retired_controls
        << ",\"retired_pc_identity\":" << owner->retired_pc_identity << ",\"lookup_identity\":" << owner->lookup_identity
        << ",\"missing_lookup_mapping\":" << owner->missing_lookup_mapping
        << ",\"missing_retirement_mapping\":" << owner->missing_retirement_mapping
        << ",\"native_branch_history_observation_frames_at_exit\":" << owner->pendingObservationFrames();
    out << ",\"RNG_observation\":\"upstream TAGE::update unchanged; observer draws none; full RNG not exported\"}\n";
}

NativeTAGEBase &NativeTAGE::checkedCore(gem5::branch_prediction::TAGEBase *base) {
    auto *value = dynamic_cast<NativeTAGEBase *>(base);
    if (!value) throw std::invalid_argument("NativeTAGE requires NativeTAGEBase");
    return *value;
}
NativeTAGE::NativeTAGE(const gem5::NativeTAGEParams &p) : TAGE(p), core(checkedCore(p.tage)) {
    query_latency_ = p.query_latency; cycle_ticks_ = p.cycle_ticks;
    if (!cycle_ticks_ || query_latency_ > 32)
        throw std::invalid_argument("invalid native query latency or clock");
    core.owner = this;
    observing_ = !p.commit_trace_file.empty() || core.originObservationEnabled();
    if (!p.commit_trace_file.empty()) {
        trace_ = gzopen(p.commit_trace_file.c_str(), "wb1");
        if (!trace_) throw std::runtime_error("cannot open native commit trace");
        const char *header = "branch_id,retire_tick,training_tick,pc,target,taken,conditional,tage_prediction,"
            "lookup_id,lookup_tick,source_epoch,buffer_epoch,head,raw_limb0,raw_limb1,raw_limb2,"
            "path,nonspec_path,fold_invariant_distance,folds,indices,query_tags,provider_type,hit_bank,alternate_bank,sampling_phase\n";
        gzwrite(trace_, header, unsigned(std::char_traits<char>::length(header)));
    }
}
NativeTAGE::~NativeTAGE() { if (trace_) gzclose(trace_); }
void NativeTAGE::flushTrace() {
    if (trace_) {
        int result = gzclose(trace_); trace_ = nullptr;
        if (result != Z_OK) throw std::runtime_error("native trace close failed");
    }
}
bool NativeTAGE::predict(gem5::ThreadID tid, gem5::Addr pc, bool conditional, void *&history) {
    if (conditional && query_latency_) {
        if (!pending_ || pending_pc_ != pc || gem5::curTick() < ready_tick_)
            throw std::logic_error("delayed direct query consumed before readiness");
        pending_ = false;
    }
    bool predicted = TAGE::predict(tid, pc, conditional, history);
    auto &bi = *static_cast<TageBranchInfo *>(history)->tageBranchInfo;
    ++lookups; mix(lookup_identity, pc); mix(lookup_identity, predicted); mix(lookup_identity, conditional);
    if (observing_) frames_[history] = core.sample(bi, lookups);
    return predicted;
}
bool NativeTAGE::seuPredictionRequest(gem5::ThreadID tid, gem5::Addr pc,
                                    bool conditional, uint32_t &token) {
    if (tid) throw std::invalid_argument("query admission single thread");
    if (!conditional || !query_latency_) return true;
    if (!token) {
        if (pending_) throw std::logic_error("duplicate pending query owner");
        pending_ = true; pending_pc_ = pc;
        if (!++next_token_) ++next_token_;
        token = pending_token_ = next_token_;
        ready_tick_ = gem5::curTick()+query_latency_*cycle_ticks_;
        ++delayed_requests;
    }
    if (!pending_ || token != pending_token_ || pending_pc_ != pc)
        throw std::logic_error("query ownership mismatch");
    if (gem5::curTick() < ready_tick_) { ++query_wait_calls; return false; }
    return true;
}
void NativeTAGE::seuCancelPending(gem5::ThreadID) {
    if (pending_) { ++canceled_requests; pending_ = false; }
}
void NativeTAGE::seuAuditCommit(uint64_t, uint64_t pc, unsigned micro, bool last, bool control, void *info) {
    ++retired_ops; retired_instructions += last; retired_controls += control;
    mix(retired_pc_identity, pc); mix(retired_pc_identity, micro);
    mix(retired_pc_identity, last); mix(retired_pc_identity, control);
    if (observing_ && control && info && !retired_.count(info))
        retired_[info] = {gem5::curTick(), ++next_retired_branch_};
}
void NativeTAGE::writeTrace(const NativeSample *sample, const Retired *retired,
        gem5::Addr pc, bool taken, bool conditional, gem5::Addr target, const Base::BranchInfo &bi) {
    if (!trace_) return;
    std::ostringstream out;
    out << (retired ? std::to_string(retired->logical_id) : "NOT_OBSERVED") << ','
        << (retired ? std::to_string(retired->tick) : "NOT_OBSERVED") << ',' << gem5::curTick()
        << ',' << pc << ',' << target << ',' << taken << ',' << conditional << ',' << (!conditional || bi.tagePred) << ',';
    if (sample) {
        out << sample->lookup_id << ',' << sample->lookup_tick << ',' << sample->epoch << ','
            << sample->buffer_epoch << ',' << sample->head << ',' << sample->raw.limb[0] << ','
            << sample->raw.limb[1] << ',' << sample->raw.limb[2] << ',' << sample->path << ','
            << sample->nonspec_path << ',' << (conditional ? std::to_string(sample->invariant_distance) : "NOT_APPLICABLE") << ',';
        list(out, sample->folds); out << ','; list(out, sample->indices); out << ','; list(out, sample->tags);
    } else {
        for (unsigned i = 0; i < 14; ++i) { if (i) out << ','; out << "NOT_OBSERVED"; }
    }
    out << ',' << (conditional ? std::to_string(bi.provider) : "NOT_APPLICABLE") << ','
        << bi.hitBank << ',' << bi.altBank << ','
        << (sample ? "AFTER_QUERY_BEFORE_SPEC_APPEND" : "NOT_OBSERVED") << '\n';
    auto line = out.str();
    if (gzwrite(trace_, line.data(), unsigned(line.size())) != int(line.size()))
        throw std::runtime_error("native trace write failed");
}
void NativeTAGE::update(gem5::ThreadID tid, gem5::Addr pc, bool taken, void *&history,
        bool squashed, const gem5::StaticInstPtr &inst, gem5::Addr target) {
    if (squashed) { TAGE::update(tid, pc, taken, history, true, inst, target); return; }
    auto *key = history;
    auto &bi = *static_cast<TageBranchInfo *>(history)->tageBranchInfo;
    ++commit_updates; conditional_updates += bi.condBranch;
    if (observing_) {
        auto frame = frames_.find(key); auto retired = retired_.find(key);
        missing_lookup_mapping += frame == frames_.end();
        missing_retirement_mapping += retired == retired_.end();
        writeTrace(frame == frames_.end() ? nullptr : &frame->second,
                   retired == retired_.end() ? nullptr : &retired->second,
                   pc, taken, bi.condBranch, target, bi);
    }
    // Keep upstream RNG draw, stats, training, history update, and deletion order.
    TAGE::update(tid, pc, taken, history, false, inst, target);
    frames_.erase(key); retired_.erase(key);
    core.observeOrigins("commit");
}
void NativeTAGE::squash(gem5::ThreadID tid, void *&history) {
    auto *key = history;
    TAGE::squash(tid, history);
    frames_.erase(key); retired_.erase(key);
    core.observeOrigins("squash");
}
void NativeTAGE::rebaseFrames(int offset) {
    for (auto &frame : frames_) frame.second.restore_head += offset;
}
unsigned NativeTAGE::restorableOriginCount() const {
    std::set<uint64_t> labels;
    for (const auto &frame : frames_) {
        auto one = core.originLabels(frame.second.restore_head);
        labels.insert(one.begin(), one.end());
    }
    return unsigned(labels.size());
}
} // namespace bp
