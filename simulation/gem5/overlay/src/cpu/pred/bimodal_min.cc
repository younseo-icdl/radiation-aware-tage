#include "cpu/pred/bimodal_min.hh"
#include "sim/cur_tick.hh"
#include <fstream>

namespace bp {
BimodalMin::BimodalMin(const gem5::BimodalMinParams &p)
    : ConditionalPredictor(p), table_(p.log_size, p.hysteresis_ratio),
      summary_path_(p.summary_file), fault_tick_(p.fault_tick), fault_site_(p.fault_site),
      injection_([this] { table_.flip(fault_site_); ++applied_; }, name()+".base_xor",
                 false, gem5::Event::CPU_Tick_Pri-1) {
    if (fault_tick_ && fault_site_ >= table_.bits())
        throw std::out_of_range("base fault site");
}
void BimodalMin::startup() {
    ConditionalPredictor::startup();
    if (fault_tick_) schedule(injection_, fault_tick_);
}
bool BimodalMin::lookup(gem5::ThreadID tid, gem5::Addr pc, void *&history) {
    if (tid || history) throw std::logic_error("base lookup ownership");
    history = new Info{true}; ++lookups_;
    return table_.predict(pc>>instShiftAmt);
}
void BimodalMin::branchPlaceholder(gem5::ThreadID tid, gem5::Addr, bool uncond, void *&history) {
    if (tid || history) throw std::logic_error("base placeholder ownership");
    history = new Info{!uncond};
}
void BimodalMin::updateHistories(gem5::ThreadID tid, gem5::Addr pc, bool uncond,
        bool, gem5::Addr, const gem5::StaticInstPtr &, void *&history) {
    if (!history) branchPlaceholder(tid, pc, uncond, history);
}
void BimodalMin::squash(gem5::ThreadID, void *&history) {
    delete static_cast<Info *>(history); history = nullptr;
}
void BimodalMin::update(gem5::ThreadID tid, gem5::Addr pc, bool taken, void *&history,
        bool squashed, const gem5::StaticInstPtr &, gem5::Addr) {
    if (tid || !history) throw std::logic_error("base commit ownership");
    if (squashed) return;
    if (static_cast<Info *>(history)->conditional) {
        table_.update(pc>>instShiftAmt, taken); ++updates_;
    }
    squash(tid, history);
}
void BimodalMin::seuAuditCommit(uint64_t, uint64_t pc, unsigned micro, bool last, bool control, void *) {
    ++retired_ops_; retired_inst_ += last;
    for (uint64_t value : {pc, uint64_t(micro), uint64_t(last), uint64_t(control)})
        identity_ = (identity_^value)*1099511628211ULL;
}
void BimodalMin::dumpResearch() {
    if (frozen_) return;
    frozen_ = true;
    if (injection_.scheduled()) deschedule(injection_);
    std::ofstream out(summary_path_);
    if (!out) throw std::runtime_error("cannot open base summary");
    out << "{\"method\":\"BASE_MIN\",\"tick\":" << gem5::curTick()
        << ",\"logical_counter_bits\":" << table_.bits()
        << ",\"prediction_bits\":" << table_.prediction.size()
        << ",\"hysteresis_bits\":" << table_.hysteresis.size()
        << ",\"history_fold_tagged_chooser_state\":false,\"extra_lookup_cycles\":0,"
        "\"timing_contract\":\"ordinary single base lookup/update; no added history service; physical timing UNKNOWN\","
        "\"checkpoint_scope\":\"per-branch conditional marker only; no history checkpoint\","
        "\"physical_control_cost\":\"UNKNOWN\",\"WHOLE_coverage\":false,"
        "\"fault_site_order\":\"prediction bits then shared hysteresis bits\","
        "\"scheduled_events\":" << bool(fault_tick_) << ",\"applied_events\":" << applied_
        << ",\"fault_tick\":" << fault_tick_ << ",\"fault_site\":" << fault_site_
        << ",\"retired_ops\":" << retired_ops_ << ",\"retired_instructions\":" << retired_inst_
        << ",\"retired_pc_identity\":" << identity_ << ",\"lookups\":" << lookups_
        << ",\"conditional_updates\":" << updates_ << "}\n";
}
} // namespace bp
