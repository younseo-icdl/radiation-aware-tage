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
template <class Range> void list(std::ostream &out, const Range &values) {
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
                 gem5::Event::CPU_Tick_Pri-2),
      lease_publication_([this] {
          if(frozen_) return;
          if(!owner) throw std::logic_error("lease publication has no actual owner");
          owner->completeLease();
          if(maintenance_) maintenance_<<"publish,"<<gem5::curTick()<<','<<lease.age()<<','
              <<owner->liveHistoryOwners()<<','<<lease.ready_time()<<'\n';
      },name()+".lease_publish",false,gem5::Event::CPU_Tick_Pri-1),
      lease(p.lease_period,p.lease_latency_ticks) {
    if (p.numThreads != 1) throw std::invalid_argument("native observation currently supports one thread");
    if(p.nHistoryTables!=7 || p.maxHist!=130 || p.pathHistBits!=16 || p.takenOnlyHistory)
        throw std::invalid_argument("native integrated study requires the frozen plain TAGE geometry");
    direct_queries = p.direct_queries;
    direct_bank_mask = p.direct_bank_mask;
    if(direct_bank_mask>127 || (lease.enabled() && effective_direct_mask()))
        throw std::invalid_argument("invalid mask or unadmitted combined lease/hybrid");
    if(!p.lease_log_file.empty()) {
        maintenance_.open(p.lease_log_file);
        if(!maintenance_) throw std::runtime_error("cannot open lease event trace");
        maintenance_<<"event,tick,age,live_owners,ready_tick\n";
    }
    if (!p.origin_file.empty()) {
        origins_.open(p.origin_file);
        if (!origins_) throw std::runtime_error("cannot open raw origin trace");
        origins_ << "callback_ordinal,tick,raw_history_writes,conditional_history_writes,"
            "active_origin_bits,restorable_origin_bits,head,buffer_epoch,reason\n";
    }
    if (!p.history_activity_file.empty()) {
        if (!p.history_activity_end_tick || !schedule_path_.empty())
            throw std::invalid_argument("history activity requires a bounded clean run");
        activity_end_=p.history_activity_end_tick;
        activity_.open(p.history_activity_file);
        if (!activity_) throw std::runtime_error("cannot open history activity trace");
        activity_ << "# capture_end_tick=" << activity_end_ << "\ntick,operation,owner,value,auxiliary\n";
    }
}
NativeTAGEBase::~NativeTAGEBase() {
    if (injection_.scheduled()) deschedule(injection_);
    if(lease_publication_.scheduled()) deschedule(lease_publication_);
}
void NativeTAGEBase::armLeasePublication() {
    if(frozen_ || !lease.busy() || lease_publication_.scheduled()) return;
    if(lease.ready_time()<=gem5::curTick()) throw std::logic_error("lease publication was not armed on time");
    schedule(lease_publication_,lease.ready_time());
    historyActivity("service_start",0,lease.ready_time(),lease.age());
    if(maintenance_) maintenance_<<"start,"<<gem5::curTick()<<','<<lease.age()<<','
        <<(owner ? owner->liveHistoryOwners() : 0)<<','<<lease.ready_time()<<'\n';
}
bool NativeTAGEBase::activityOpen() const {
    return activity_.is_open() && !frozen_ && gem5::curTick()<activity_end_;
}
void NativeTAGEBase::historyActivity(const char *op, uint64_t id, uint64_t value, uint64_t auxiliary) {
    if (!activityOpen()) return;
    activity_ << gem5::curTick()<<','<<op<<','<<id<<','<<value<<','<<auxiliary<<'\n';
    if (!activity_) throw std::runtime_error("history activity trace write failed");
}
void NativeTAGEBase::activityRelease(const Base::BranchInfo *bi) {
    if (!activityOpen()) return;
    auto prior=activity_owners_.find(bi);
    if(prior==activity_owners_.end()) return; // A placeholder need not have appended.
    historyActivity("release",prior->second,0,0);
    activity_owners_.erase(prior);
}
void NativeTAGEBase::noteHistoryChange() {
    ++history_generation_;
    history_change_tick_=gem5::curTick();
}
NativeQueryOperands NativeTAGEBase::captureOperands(gem5::ThreadID tid, gem5::Addr pc) const {
    NativeQueryOperands operands;
    for (unsigned bank=1; bank<=nHistoryTables; ++bank) {
        operands.indices[bank]=gindex(tid,pc,bank);
        operands.tags[bank]=gtag(tid,pc,bank);
    }
    return operands;
}
NativeReturnedRows NativeTAGEBase::captureRows(gem5::Addr pc, const NativeQueryOperands &operands) const {
    NativeReturnedRows rows;
    rows.bimodal=btablePrediction[bindex(pc)];
    rows.prefer_longest=useAltPredForNewlyAllocated.at(0)<0;
    for (unsigned bank=1; bank<=nHistoryTables; ++bank) {
        const auto &entry=gtable[bank][operands.indices[bank]];
        rows.tags[bank-1]=entry.tag;
        rows.counters[bank-1]=unsigned(entry.ctr)&7;
        rows.bank_mask|=unsigned(noSkip[bank])<<(bank-1);
    }
    return rows;
}
void NativeTAGEBase::calculateIndicesAndTags(gem5::ThreadID tid, gem5::Addr pc, Base::BranchInfo *bi) {
    if (!staged_operands_) {
        Base::calculateIndicesAndTags(tid,pc,bi);
        return;
    }
    const auto &operands=*staged_operands_;
    staged_operands_=nullptr;
    for (unsigned bank=1; bank<=nHistoryTables; ++bank) {
        tableIndices[bank]=bi->tableIndices[bank]=operands.indices[bank];
        tableTags[bank]=bi->tableTags[bank]=operands.tags[bank];
    }
    bi->valid=true;
}
bool NativeTAGEBase::predictWithOperands(gem5::ThreadID tid, gem5::Addr pc, Base::BranchInfo *bi,
                                          const NativeQueryOperands &operands) {
    if (staged_operands_ || !bi->condBranch)
        throw std::logic_error("unexpected staged hash consumer");
    staged_operands_=&operands;
    bool predicted=tagePredict(tid,pc,true,bi);
    if (staged_operands_)
        throw std::logic_error("row selection did not consume the registered hashes");
    return predicted;
}
void NativeTAGEBase::init() {
    Base::init();
    sites_ = sites();
    words_ = history_words();
    loadFaults();
    if (!event_path_.empty()) {
        events_.open(event_path_);
        if (!events_) throw std::runtime_error("cannot open injection trace");
        events_ << "event_ordinal,requested_tick,applied_tick,multiplicity,logical_site_ids,raw_physical_indices,bit_values_before,bit_values_after\n";
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
            pos=line.find("horizon=");
            if(pos!=std::string::npos) {
                std::istringstream header(line.substr(pos+8));
                std::string value;header>>value;declared_horizon_=integer(value);
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
    auto checked=[&](size_t id) {
        if(id>=sites_.size()) {
            if(id-sites_.size()>=lease.age_bits()) throw std::out_of_range("logical site id");
        } else if(sites_[id].kind==5 && uses_direct(sites_[id].bank))
            throw std::invalid_argument("direct bank has no consumed stored-fold target");
        return id;
    };
    if(mark.rfind("L:AGE:",0)==0) return checked(sites_.size()+integer(mark.substr(6)));
    if (mark[0] == 'R') {
        auto age = integer(mark.substr(1));
        if (age >= maxHist) throw std::out_of_range("raw age");
        return checked(words_[nHistoryTables*3].sites.at(age));
    }
    if (mark[0] == 'W') {
        auto colon = mark.find(':');
        if (colon == std::string::npos) throw std::invalid_argument("expected W<word>:<bit>");
        auto word = integer(mark.substr(1, colon-1)), bit = integer(mark.substr(colon+1));
        if (word >= words_.size() || bit >= words_[word].width) throw std::out_of_range("history site");
        return checked(words_[word].sites.at(bit));
    }
    auto id = integer(mark);
    return checked(id);
}
void NativeTAGEBase::injectNext() {
    if (frozen_) return;
    while (next_fault_ < faults_.size() && faults_[next_fault_].tick == gem5::curTick()) {
        observeOrigins("before_injection", true);
        auto &fault = faults_[next_fault_];
        std::vector<size_t> ids, ordinary;
        std::vector<int> physical;
        for (const auto &mark : fault.sites) {
            auto id = resolve(mark); ids.push_back(id);
            if(id>=sites_.size()) continue;
            ordinary.push_back(id);
            const auto &site = sites_[id];
            if (site.kind == 4 && site.bank == 0)
                physical.push_back(history_cursor()+site.row);
        }
        auto value=[&](size_t id) {
            return id<sites_.size() ? ((payload(sites_[id])>>sites_[id].bit)&1u)
                 : ((lease.age()>>(id-sites_.size()))&1u);
        };
        std::vector<unsigned> before,after;
        for(auto id:ids) before.push_back(value(id));
        // All members were validated before any write; no callback/yield inside
        // the atomic group. No fold/code refresh is part of injection.
        if(!ordinary.empty()) corrupt(ordinary);
        for(auto id:ids) if(id>=sites_.size()) lease.xor_age(id-sites_.size());
        for(auto id:ids) after.push_back(value(id));
        for (int cell : physical) raw_origins_[cell].insert(++origin_id_);
        if (events_) {
            events_ << next_fault_+1 << ',' << fault.tick << ',' << gem5::curTick() << ',' << ids.size() << ',';
            list(events_, ids); events_ << ','; list(events_, physical); events_ << ',';
            list(events_,before);events_<<',';list(events_,after);events_<<'\n';
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
    lease.append(n);
    if(gem5::curTick()!=append_tick_) {append_tick_=gem5::curTick();appends_this_tick_=0;}
    appends_this_tick_+=n;
    maximum_raw_appends_per_tick=std::max(maximum_raw_appends_per_tick,appends_this_tick_);
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
    if (n && activityOpen()) {
        if (!activity_append_context_ || n!=1)
            throw std::logic_error("history activity requires a single-bit append owner");
        auto [entry, inserted]=activity_owners_.try_emplace(activity_append_context_,activity_next_owner_+1);
        activity_next_owner_+=inserted;
        historyActivity("append",entry->second,bits&1,threadHistory[tid].pathHist&1);
    }
    if (n) {
        noteHistoryChange();
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
    if(activityOpen()) activity_append_context_=bi;
    Base::updateHistories(tid, pc, speculative, taken, target, inst, bi);
    activity_append_context_=nullptr;
    conditional_context_ = previous;
    ++source_epoch;
    observeOrigins("history_callback");
}
void NativeTAGEBase::restoreHistState(gem5::ThreadID tid, Base::BranchInfo *bi) {
    if(gem5::curTick()!=restore_tick_) {restore_tick_=gem5::curTick();restores_this_tick_=0;}
    if(bi->modified) restores_this_tick_+=bi->nGhist;
    maximum_raw_restores_per_tick=std::max(maximum_raw_restores_per_tick,restores_this_tick_);
    if (activityOpen() && bi->modified && bi->nGhist) {
        auto prior=activity_owners_.find(bi);
        if (prior==activity_owners_.end()) throw std::logic_error("history undo activity missing owner");
        historyActivity("undo",prior->second,bi->nGhist,0);
    }
    Base::restoreHistState(tid, bi);
    if (bi->modified)
        noteHistoryChange();
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
        unsigned fold = uses_direct(w/3+1) ? direct_word(w) : read_history_word(w).limb[0], canonical = 0;
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
    unsigned direct_mask=effective_direct_mask();
    unsigned dead_fold_bits=0;
    for(unsigned w=0;w<21;++w) if(uses_direct(w/3+1)) dead_fold_bits+=words_[w].width;
    out << "{\"method\":\"" << (direct_mask ? "direct_or_hybrid_query_TAGE" : "ordinary_recurrent_TAGE")
        << "\",\"direct_bank_mask\":" << direct_mask
        << ",\"consumed_stored_folds\":" << (direct_mask==127 ? "false" : "true")
        << ",\"fault_coordinate\":\"ticks\","
        "\"placement\":\"logical stored fields; raw age resolves once at injection\","
        "\"physical_hardware_mapping\":\"UNKNOWN\",\"WHOLE_coverage\":false,"
        "\"excluded\":[\"head\",\"pending/checkpoint fields\",\"chooser/RNG\",\"observer storage\"],"
        "\"logical_sites_including_dead_software_folds\":" << sites_.size()+lease.age_bits()
        << ",\"logical_sites\":" << sites_.size()+lease.age_bits()
        << ",\"enumerated_active_fault_bits\":" << sites_.size()-dead_fold_bits+lease.age_bits()
        << ",\"lease_age_sites_start\":" << sites_.size()
        << ",\"lease_age_bits\":" << lease.age_bits()
        << ",\"lease_control_coverage\":\"age exposed; busy/timer not exposed; not WHOLE coverage\""
        << ",\"selected_history_bits_legacy\":" << selected
        << ",\"selected_history_bits\":" << selected
        << ",\"active_selected_history_bits\":" << selected-dead_fold_bits << ",\"words\":[";
    for (size_t w = 0; w < words_.size(); ++w) {
        if (w) out << ',';
        out << "{\"word\":" << w << ",\"name\":\"" << words_[w].id << "\",\"width\":"
            << words_[w].width << ",\"consumed\":" << ((w<21 && uses_direct(w/3+1)) ? "false" : "true")
            << ",\"site_ids\":[";
        for (size_t i = 0; i < words_[w].sites.size(); ++i) { if (i) out << ','; out << words_[w].sites[i]; }
        out << "]}";
    }
    out << "],\"regions\":[";
    unsigned region=0;
    for(size_t first=0;first<sites_.size();) {
        const auto &s=sites_[first];size_t end=first+1;
        while(end<sites_.size()) {
            const auto &t=sites_[end];
            if(t.kind!=s.kind || t.bank!=s.bank || t.width!=s.width ||
               (s.kind==5 && t.row!=s.row)) break;
            ++end;
        }
        if(region++) out<<',';
        out<<"{\"kind\":"<<s.kind<<",\"field\":\""<<field_name(s.kind)
           <<"\",\"bank\":"<<s.bank<<",\"first_row\":"<<s.row
           <<",\"width\":"<<s.width<<",\"start\":"<<first<<",\"bits\":"<<end-first
           <<",\"consumed\":"<<((s.kind==5 && uses_direct(s.bank)) ? "false" : "true")<<'}';
        first=end;
    }
    out << "]}\n";
}
void NativeTAGEBase::dumpResearch() {
    if (frozen_) return;
    observeOrigins("program_exit", true);
    frozen_ = true; exit_tick_ = gem5::curTick();
    if (injection_.scheduled()) deschedule(injection_);
    bool lease_censored=lease_publication_.scheduled();
    if(lease_censored) deschedule(lease_publication_);
    if (events_) events_.flush();
    if (origins_) origins_.flush();
    if(maintenance_) maintenance_.flush();
    if(activity_.is_open()) {
        activity_.flush();
        if(!activity_) throw std::runtime_error("history activity flush failed");
    }
    if (owner) owner->flushTrace();
    if (summary_path_.empty()) return;
    uint64_t fingerprint = 14695981039346656037ULL;
    for (const auto &site : sites_) mix(fingerprint, (payload(site) >> site.bit) & 1u);
    mix(fingerprint, uint64_t(tCounter));
    for (auto value : useAltPredForNewlyAllocated) mix(fingerprint, uint8_t(value));
    std::ofstream out(summary_path_);
    if (!out) throw std::runtime_error("cannot open native summary");
    const char *method=lease.enabled() ? "LEASE_REBASE" :
        effective_direct_mask()==127 ? "D_QUERY" : effective_direct_mask() ? "HYBRID_QUERY" : "U_NATIVE";
    out << "{\"method\":\"" << method
        << "\",\"direct_bank_mask\":" << effective_direct_mask()
        << ",\"protection\":\"" << (lease.enabled() ? "periodic quiescent own-history rebase" :
            effective_direct_mask() ? "direct own-history folds" : "NONE") << "\","
        "\"target_checker_stages\":0,\"additional_lookup_hold\":" << (owner ? owner->queryLatency() : 0)
        << ",\"additional_retirement_hold\":0,"
        "\"periodic_service_clock\":false,\"tick\":" << exit_tick_
        << ",\"scheduled_events\":" << faults_.size() << ",\"applied_events\":" << next_fault_
        << ",\"applied_flips\":" << flips_ << ",\"future_events_censored\":" << faults_.size()-next_fault_
        << ",\"declared_tape_horizon_tick\":" << declared_horizon_
        << ",\"schedule_exhausted_before_exit\":" << (declared_horizon_ && exit_tick_>declared_horizon_ ? "true" : "false")
        << ",\"faults_frozen\":true,\"semantic_base_fingerprint\":" << fingerprint
        << ",\"fingerprint_scope\":\"active base state; not exhaustive checkpoint/RNG equality\","
        "\"origin_scope\":\"single-event raw identities; actual append/undo/rollover, no extra XOR\","
        "\"multi_event_recovery_partitioned\":false,\"raw_history_writes\":" << raw_writes;
    out << ",\"lease_publications\":" << lease.publications
        << ",\"lease_completion_censored_at_exit\":" << (lease_censored ? "true" : "false")
        << ",\"same_tick_order\":\"injection before lease publication before CPU tick\""
        << ",\"maximum_raw_appends_per_tick\":" << maximum_raw_appends_per_tick
        << ",\"maximum_raw_restores_per_tick\":" << maximum_raw_restores_per_tick
        << ",\"lease_drain_wait_calls\":" << lease.drain_wait_calls
        << ",\"lease_service_wait_calls\":" << lease.service_wait_calls
        << ",\"lease_age_at_exit\":" << lease.age()
        << ",\"lease_busy_at_exit\":" << (lease.busy() ? "true" : "false")
        << ",\"physical_stage_qualification\":\"NOT_ESTABLISHED_BY_THIS_CPU_MODEL\"";
    if (owner) out << ",\"lookups\":" << owner->lookups << ",\"committed_updates\":" << owner->commit_updates
        << ",\"prediction_output_forced_base\":" << (owner->force_base ? "true" : "false")
        << ",\"additional_query_latency_cycles\":" << owner->queryLatency()
        << ",\"query_wait_calls\":" << owner->query_wait_calls
        << ",\"delayed_requests\":" << owner->delayed_requests
        << ",\"canceled_query_requests\":" << owner->canceled_requests
        << ",\"conditional_updates\":" << owner->conditional_updates << ",\"retired_ops\":" << owner->retired_ops
        << ",\"retired_instructions\":" << owner->retired_instructions << ",\"retired_controls\":" << owner->retired_controls
        << ",\"retired_pc_identity\":" << owner->retired_pc_identity << ",\"lookup_identity\":" << owner->lookup_identity
        << ",\"missing_lookup_mapping\":" << owner->missing_lookup_mapping
        << ",\"missing_retirement_mapping\":" << owner->missing_retirement_mapping
        << ",\"missing_bpu_mapping\":" << owner->missing_bpu_mapping
        << ",\"missing_bpu_prediction_mapping\":" << owner->missing_bpu_prediction_mapping
        << ",\"maximum_actual_restore_owners\":" << owner->max_inflight
        << ",\"maximum_all_live_history_owners\":" << owner->max_live_owners
        << ",\"all_live_history_owners_at_exit\":" << owner->liveHistoryOwners()
        << ",\"maximum_lookups_per_tick\":" << owner->maximum_lookups_per_tick
        << ",\"maximum_conditional_lookups_per_tick\":" << owner->maximum_conditional_lookups_per_tick
        << ",\"lease_frontend_wait_calls\":" << owner->lease_frontend_wait_calls
        << ",\"native_branch_history_observation_frames_at_exit\":" << owner->pendingObservationFrames();
    if (owner && owner->queryInterval())
        out << ",\"conditional_query_interval_cycles\":" << owner->queryInterval()
            << ",\"query_interval_wait_calls\":" << owner->query_interval_wait_calls;
    if (owner && owner->queryPipeline())
        out << ",\"staged_query_hash_cycles\":1"
            << ",\"staged_query_row_cycles\":1"
            << ",\"staged_query_captures\":" << owner->staged_captures
            << ",\"staged_query_responses\":" << owner->staged_responses
            << ",\"staged_query_retries\":" << owner->staged_retries
            << ",\"staged_query_same_tick_holds\":" << owner->staged_operand_holds
            << ",\"staged_responses_after_fault\":" << owner->staged_responses_after_fault
            << ",\"staged_responses_with_changed_hash\":" << owner->staged_responses_with_changed_hash
            << ",\"first_staged_issue_tick\":" << owner->first_staged_issue_tick
            << ",\"first_staged_capture_tick\":" << owner->first_staged_capture_tick
            << ",\"first_staged_hash_identity\":" << owner->first_staged_hash_identity
            << ",\"first_staged_response_tick\":" << owner->first_staged_response_tick;
    if (owner && owner->singleTrainingPort())
        out << ",\"conditional_training_port_capacity\":1"
            << ",\"conditional_training_port_reservations\":" << owner->training_port_reservations
            << ",\"conditional_training_port_waits\":" << owner->training_port_waits;
    out << ",\"RNG_observation\":\"upstream TAGE::update unchanged; observer draws none; full RNG not exported\"}\n";
}

NativeTAGEBase &NativeTAGE::checkedCore(gem5::branch_prediction::TAGEBase *base) {
    auto *value = dynamic_cast<NativeTAGEBase *>(base);
    if (!value) throw std::invalid_argument("NativeTAGE requires NativeTAGEBase");
    return *value;
}
NativeTAGE::NativeTAGE(const gem5::NativeTAGEParams &p)
    : TAGE(p),
      query_hash_latch_([this] { latchQueryHash(); }, name()+".hash_latch", false,
                        gem5::Event::CPU_Tick_Pri-1),
      core(checkedCore(p.tage)) {
    query_latency_ = p.query_latency; cycle_ticks_ = p.cycle_ticks;
    query_ii_cycles_ = p.query_ii_cycles;
    query_pipeline_ = p.query_pipeline;
    single_training_port_ = p.single_training_port;
    if (single_training_port_ && !query_pipeline_)
        throw std::invalid_argument("single training port requires registered query mode");
    if (query_ii_cycles_>32 || (query_ii_cycles_ && query_latency_)
            || (query_ii_cycles_ && cycle_ticks_>UINT64_MAX/query_ii_cycles_))
        throw std::invalid_argument("invalid or combined native query interval");
    force_base = p.force_base;
    restore_capacity_=p.max_restore_owners;
    if (!cycle_ticks_ || query_latency_ > 32)
        throw std::invalid_argument("invalid native query latency or clock");
    if(!restore_capacity_ || (core.lease.enabled() && (query_latency_ || force_base)))
        throw std::invalid_argument("invalid restore capacity or unadmitted combined lease policy");
    core.owner = this;
    observing_ = !p.commit_trace_file.empty() || core.originObservationEnabled();
    if (query_pipeline_ && (query_latency_ || query_ii_cycles_ || force_base ||
                            core.effective_direct_mask() || observing_))
        throw std::invalid_argument("staged hashing requires matched recurrent operands and stage-aware observation");
    if (!p.row_activity_file.empty()) {
        if (!query_pipeline_ || !core.capturingActivity())
            throw std::invalid_argument("returned-row capture requires bounded staged history activity");
        row_activity_.open(p.row_activity_file);
        if (!row_activity_)
            throw std::runtime_error("cannot open returned-row activity trace");
        row_activity_ << "tick,token,pc,indices,query_tags,row_tags,counters,bank_mask,"
                         "bimodal,prefer_longest,target_valid,direction\n";
    }
    if (!p.commit_trace_file.empty()) {
        trace_ = gzopen(p.commit_trace_file.c_str(), "wb1");
        if (!trace_) throw std::runtime_error("cannot open native commit trace");
        const char *header = "branch_id,retire_tick,training_tick,pc,target,taken,conditional,tage_prediction,"
            "lookup_id,lookup_tick,source_epoch,buffer_epoch,head,raw_limb0,raw_limb1,raw_limb2,"
            "path,nonspec_path,fold_invariant_distance,folds,indices,query_tags,provider_type,hit_bank,alternate_bank,sampling_phase,"
            "bpu_pred_taken,bpu_cond_pred,bpu_btb_hit,bpu_mispredicted,bpu_target_provider,bpu_predicted_target\n";
        gzwrite(trace_, header, unsigned(std::char_traits<char>::length(header)));
    }
}
NativeTAGE::~NativeTAGE() {
    clearPendingQuery();
    if (trace_) gzclose(trace_);
}
void NativeTAGE::clearPendingQuery() {
    if (query_hash_latch_.scheduled()) deschedule(query_hash_latch_);
    pending_=false;
    pending_hash_captured_=false;
}
void NativeTAGE::cancelPendingQuery() {
    if (query_pipeline_)
        core.activityQueryStage("query_cancel",pending_token_,pending_pc_);
    clearPendingQuery();
}
void NativeTAGE::latchQueryHash() {
    if (!pending_ || pending_hash_captured_)
        throw std::logic_error("hash latch has no matching request");
    if (pending_generation_ != core.historyGeneration() || core.lease.due())
        return; // Its owner will cancel or retry before a provider can consume it.
    pending_operands_=core.captureOperands(0,pending_pc_);
    pending_fault_count_=core.appliedFaults();
    pending_hash_captured_=true;
    core.activityQueryStage("hash_capture",pending_token_,pending_pc_);
    if (++staged_captures == 1) {
        first_staged_capture_tick=gem5::curTick();
        first_staged_hash_identity=14695981039346656037ULL;
        for (unsigned bank=1; bank<pending_operands_.indices.size(); ++bank) {
            mix(first_staged_hash_identity,pending_operands_.indices[bank]);
            mix(first_staged_hash_identity,pending_operands_.tags[bank]);
        }
    }
}
void NativeTAGE::flushTrace() {
    if (row_activity_.is_open()) {
        if (row_observation_.history)
            throw std::logic_error("returned-row observation still awaiting its BPU callback");
        row_activity_.flush();
        if (!row_activity_)
            throw std::runtime_error("returned-row activity trace flush failed");
    }
    if (trace_) {
        int result = gzclose(trace_); trace_ = nullptr;
        if (result != Z_OK) throw std::runtime_error("native trace close failed");
    }
}
bool NativeTAGE::predict(gem5::ThreadID tid, gem5::Addr pc, bool conditional, void *&history) {
    if (conditional && query_ii_cycles_) {
        const auto now=gem5::curTick();
        const auto interval=cycle_ticks_*query_ii_cycles_;
        if (now<next_query_tick_ || now>UINT64_MAX-interval)
            throw std::logic_error("conditional query violated its issue interval");
        next_query_tick_=now+interval;
    }
    if (conditional && query_latency_) {
        if (!pending_ || pending_pc_ != pc || gem5::curTick() < ready_tick_)
            throw std::logic_error("delayed direct query consumed before readiness");
        pending_ = false;
    }
    bool predicted;
    if (conditional && query_pipeline_) {
        if (!pending_ || !pending_hash_captured_ || pending_pc_ != pc || gem5::curTick() < ready_tick_ ||
            pending_generation_ != core.historyGeneration() || core.lease.due())
            throw std::logic_error("staged query consumed before matching readiness");
        if (pending_fault_count_ != core.appliedFaults()) {
            ++staged_responses_after_fault;
            const auto current=core.captureOperands(tid,pc);
            if (current.indices!=pending_operands_.indices || current.tags!=pending_operands_.tags)
                ++staged_responses_with_changed_hash;
        }
        auto *bi=new TageBranchInfo(core,pc,true);
        history=bi;
        if (row_activity_.is_open() && core.capturingActivity()) {
            if (row_observation_.history)
                throw std::logic_error("returned-row observation lost its BPU callback");
            row_observation_={history,pc,pending_token_,pending_operands_,
                              core.captureRows(pc,pending_operands_),false};
        }
        predicted=core.predictWithOperands(tid,pc,bi->tageBranchInfo,pending_operands_);
        if (row_observation_.history)
            row_observation_.direction=predicted;
        core.activityQueryStage("row_response",pending_token_,pc);
        clearPendingQuery();
        next_query_tick_=gem5::curTick();
        if (++staged_responses == 1)
            first_staged_response_tick=gem5::curTick();
    } else {
        predicted = TAGE::predict(tid, pc, conditional, history);
    }
    if(!live_.insert(history).second) throw std::logic_error("duplicate live history owner");
    max_live_owners=std::max(max_live_owners,uint64_t(live_.size()));
    if(live_.size()>restore_capacity_) throw std::logic_error("live history-owner capacity exceeded");
    if(gem5::curTick()!=lookup_tick_) {
        lookup_tick_=gem5::curTick();lookups_this_tick_=conditionals_this_tick_=0;
    }
    ++lookups_this_tick_;conditionals_this_tick_+=conditional;
    maximum_lookups_per_tick=std::max(maximum_lookups_per_tick,lookups_this_tick_);
    maximum_conditional_lookups_per_tick=std::max(maximum_conditional_lookups_per_tick,conditionals_this_tick_);
    auto &bi = *static_cast<TageBranchInfo *>(history)->tageBranchInfo;
    if(conditional && !query_pipeline_) core.activityQuery(pc);
    ++lookups; mix(lookup_identity, pc); mix(lookup_identity, predicted); mix(lookup_identity, conditional);
    if (observing_) frames_[history] = core.sample(bi, lookups);
    return conditional && force_base ? core.basePrediction(pc, bi) : predicted;
}
bool NativeTAGE::seuPredictionRequest(gem5::ThreadID tid, gem5::Addr pc,
                                    bool conditional, uint32_t &token) {
    if (tid) throw std::invalid_argument("query admission single thread");
    if(core.lease.due()) return false;
    if (conditional && query_ii_cycles_ && gem5::curTick()<next_query_tick_) {
        ++query_interval_wait_calls;
        return false;
    }
    if (!conditional || (!query_latency_ && !query_pipeline_)) return true;
    if (query_pipeline_) {
        // A redirect normally clears the fetch token. An older history
        // mutation or maintenance may instead invalidate a retained request.
        if (token && token==pending_token_ && (!pending_ || pending_generation_!=core.historyGeneration())) {
            if (pending_) {
                ++staged_retries;
                cancelPendingQuery();
            }
            token=0;
        }
        if (core.historyChangedThisTick() || (staged_responses && gem5::curTick()==next_query_tick_)) {
            ++staged_operand_holds;
            return false;
        }
    }
    if (!token) {
        if (pending_) throw std::logic_error("duplicate pending query owner");
        const auto stages=query_pipeline_ ? 2u : query_latency_;
        if (cycle_ticks_>UINT64_MAX/stages)
            throw std::overflow_error("query delay exceeds tick range");
        const auto delay=cycle_ticks_*stages;
        if (gem5::curTick()>UINT64_MAX-delay)
            throw std::overflow_error("staged query deadline exceeds tick range");
        pending_ = true; pending_pc_ = pc;
        if (!++next_token_) ++next_token_;
        token = pending_token_ = next_token_;
        ready_tick_ = gem5::curTick()+delay;
        if (query_pipeline_) {
            pending_generation_=core.historyGeneration();
            schedule(query_hash_latch_,gem5::curTick()+cycle_ticks_);
            core.activityQueryStage("query_request",pending_token_,pc);
            if (!delayed_requests)
                first_staged_issue_tick=gem5::curTick();
        }
        ++delayed_requests;
    }
    if (!pending_ || token != pending_token_ || pending_pc_ != pc)
        throw std::logic_error("query ownership mismatch");
    if (gem5::curTick() < ready_tick_) { ++query_wait_calls; return false; }
    if (query_pipeline_ && !pending_hash_captured_)
        throw std::logic_error("row response reached readiness without a valid captured hash");
    return true;
}
void NativeTAGE::seuCancelPending(gem5::ThreadID) {
    if (pending_) {
        ++canceled_requests;
        cancelPendingQuery();
    }
}
bool NativeTAGE::seuCanRetire(gem5::ThreadID tid, void *history) {
    if (!single_training_port_ || !history ||
        !static_cast<const TageBranchInfo *>(history)->tageBranchInfo->condBranch)
        return true;
    if (tid)
        throw std::invalid_argument("native training reservation requires one thread");
    if (training_port_reservations && last_training_reservation_tick_==gem5::curTick()) {
        ++training_port_waits;
        return false;
    }
    return true;
}
void NativeTAGE::seuReserveRetire(gem5::ThreadID tid, void *history) {
    if (!single_training_port_ || !history ||
        !static_cast<const TageBranchInfo *>(history)->tageBranchInfo->condBranch)
        return;
    if (tid || (training_port_reservations && last_training_reservation_tick_==gem5::curTick()))
        throw std::logic_error("conditional retirement exceeded training port capacity");
    ++training_port_reservations;
    last_training_reservation_tick_=gem5::curTick();
}
bool NativeTAGE::seuFrontendBlocked(gem5::ThreadID tid, bool empty) {
    if(tid) throw std::invalid_argument("lease frontend single thread");
    if (query_pipeline_ && core.lease.due())
        seuCancelPending(tid);
    bool ready=core.lease.service(gem5::curTick(),empty && live_.empty() && !pending_,
                                 [&] {core.publishLeaseFolds();});
    if(core.lease.busy()) core.armLeasePublication();
    if(!ready) ++lease_frontend_wait_calls;
    return !ready;
}
void NativeTAGE::completeLease() {
    if(!core.lease.busy() || !live_.empty() || pending_)
        throw std::logic_error("autonomous lease completion is not quiescent");
    if(!core.lease.service(gem5::curTick(),true,[&] {core.publishLeaseFolds();}))
        throw std::logic_error("autonomous lease completed before ready");
}
void NativeTAGE::seuAuditInflight(unsigned n) {
    max_inflight=std::max(max_inflight,uint64_t(n));
    if(n>restore_capacity_) throw std::logic_error("actual predictor restore-owner capacity exceeded");
    if(core.lease.busy() && n) throw std::logic_error("lease quiescence violated by live restore owner");
}
void NativeTAGE::branchPlaceholder(gem5::ThreadID tid,gem5::Addr pc,bool uncond,void *&history) {
    if(core.lease.busy()) throw std::logic_error("placeholder entered quiescent worker");
    TAGE::branchPlaceholder(tid,pc,uncond,history);
    if(!live_.insert(history).second) throw std::logic_error("duplicate placeholder owner");
    max_live_owners=std::max(max_live_owners,uint64_t(live_.size()));
    if(live_.size()>restore_capacity_) throw std::logic_error("placeholder capacity exceeded");
}
void NativeTAGE::seuAuditPrediction(void *info,uint64_t target,bool target_valid) {
    if (row_observation_.history) {
        const auto &observation=row_observation_;
        if (observation.history!=info)
            throw std::logic_error("returned-row observation has the wrong BPU owner");
        row_activity_ << gem5::curTick() << ',' << observation.token << ',' << observation.pc << ',';
        list(row_activity_,observation.operand.indices); row_activity_ << ',';
        list(row_activity_,observation.operand.tags); row_activity_ << ',';
        list(row_activity_,observation.rows.tags); row_activity_ << ',';
        list(row_activity_,observation.rows.counters);
        row_activity_ << ',' << observation.rows.bank_mask << ',' << observation.rows.bimodal
                      << ',' << observation.rows.prefer_longest << ',' << target_valid
                      << ',' << observation.direction << '\n';
        if (!row_activity_)
            throw std::runtime_error("returned-row activity trace write failed");
        row_observation_=RowObservation{};
    }
    if(!observing_) return;
    auto i=frames_.find(info);
    if(i==frames_.end()) {++missing_bpu_prediction_mapping;return;}
    i->second.bpu_target_observed=true;i->second.bpu_predicted_target=target;
}
void NativeTAGE::seuAuditCommit(uint64_t, uint64_t pc, unsigned micro, bool last, bool control, void *info) {
    ++retired_ops; retired_instructions += last; retired_controls += control;
    mix(retired_pc_identity, pc); mix(retired_pc_identity, micro);
    mix(retired_pc_identity, last); mix(retired_pc_identity, control);
    if (observing_ && control && info && !retired_.count(info))
        retired_[info] = {gem5::curTick(), ++next_retired_branch_};
}
void NativeTAGE::seuAuditBranch(void *info,bool taken,bool conditional,bool btb,
                              bool wrong,unsigned provider) {
    if(!observing_ || !info) return;
    auto i=retired_.find(info);
    if(i==retired_.end()) {++missing_bpu_mapping;return;}
    auto &r=i->second;
    r.bpu_observed=true;r.pred_taken=taken;r.cond_pred=conditional;
    r.btb_hit=btb;r.mispredicted=wrong;r.target_provider=provider;
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
        << (sample ? "AFTER_QUERY_BEFORE_SPEC_APPEND" : "NOT_OBSERVED");
    if(retired && retired->bpu_observed)
        out<<','<<retired->pred_taken<<','<<retired->cond_pred<<','<<retired->btb_hit
           <<','<<retired->mispredicted<<','<<retired->target_provider;
    else out<<",NOT_OBSERVED,NOT_OBSERVED,NOT_OBSERVED,NOT_OBSERVED,NOT_OBSERVED";
    out<<','<<(sample && sample->bpu_target_observed ? std::to_string(sample->bpu_predicted_target) : "NOT_OBSERVED")<<'\n';
    auto line = out.str();
    if (gzwrite(trace_, line.data(), unsigned(line.size())) != int(line.size()))
        throw std::runtime_error("native trace write failed");
}
void NativeTAGE::update(gem5::ThreadID tid, gem5::Addr pc, bool taken, void *&history,
        bool squashed, const gem5::StaticInstPtr &inst, gem5::Addr target) {
    if (squashed) { TAGE::update(tid, pc, taken, history, true, inst, target); return; }
    auto *key = history;
    auto &bi = *static_cast<TageBranchInfo *>(history)->tageBranchInfo;
    if (single_training_port_ && bi.condBranch) {
        if (conditional_updates >= training_port_reservations ||
            (conditional_updates && last_conditional_training_tick_==gem5::curTick()))
            throw std::logic_error("conditional training exceeded the reserved port contract");
        last_conditional_training_tick_=gem5::curTick();
    }
    ++commit_updates; conditional_updates += bi.condBranch;
    if (observing_) {
        auto frame = frames_.find(key); auto retired = retired_.find(key);
        missing_lookup_mapping += frame == frames_.end();
        missing_retirement_mapping += retired == retired_.end();
        missing_bpu_mapping += retired==retired_.end() || !retired->second.bpu_observed;
        writeTrace(frame == frames_.end() ? nullptr : &frame->second,
                   retired == retired_.end() ? nullptr : &retired->second,
                   pc, taken, bi.condBranch, target, bi);
    }
    // Keep upstream RNG draw, stats, training, history update, and deletion order.
    core.activityRelease(&bi);
    TAGE::update(tid, pc, taken, history, false, inst, target);
    if(live_.erase(key)!=1) throw std::logic_error("committed history owner was not live");
    frames_.erase(key); retired_.erase(key);
    core.observeOrigins("commit");
}
void NativeTAGE::squash(gem5::ThreadID tid, void *&history) {
    auto *key = history;
    auto *bi = static_cast<TageBranchInfo *>(history)->tageBranchInfo;
    TAGE::squash(tid, history);
    core.activityRelease(bi);
    if(live_.erase(key)!=1) throw std::logic_error("squashed history owner was not live");
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
