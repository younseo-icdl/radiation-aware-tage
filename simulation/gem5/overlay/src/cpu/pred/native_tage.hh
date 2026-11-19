#pragma once
#include "cpu/pred/tage.hh"
#include "params/NativeTAGE.hh"
#include "params/NativeTAGEBase.hh"
#include "sim/eventq.hh"
#include "tage/predictor/tage_access.hpp"
#include "tage/history/direct_access.hpp"
#include "tage/history/lease.hpp"
#include "tage/protection/history_controller.hpp"
#include <array>
#include <fstream>
#include <map>
#include <memory>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <zlib.h>

namespace bp {
class NativeTAGE;
struct NativeQueryOperands {
    std::array<int, 8> indices{}, tags{};
};
struct NativeReturnedRows {
    std::array<unsigned, 7> tags{}, counters{};
    unsigned bank_mask=0;
    bool bimodal=false, prefer_longest=false;
};
struct NativeSample {
    uint64_t lookup_id = 0, lookup_tick = 0, epoch = 0, buffer_epoch = 0;
    int head = 0, restore_head = 0;
    Word raw;
    unsigned path = 0, nonspec_path = 0, invariant_distance = 0;
    std::vector<unsigned> folds, indices, tags;
    bool bpu_target_observed=false;
    uint64_t bpu_predicted_target=0;
};

// Native O3 path without the finite-source transport.
class NativeTAGEBase : public DirectAccess<TageAccess> {
    struct Fault {
        gem5::Tick tick;
        std::vector<std::string> sites;
    };
    std::vector<Fault> faults_;
    std::vector<Site> sites_;
    std::vector<HistoryWord> words_;
    const std::string history_protection_;
    std::unique_ptr<HistoryController> protection_;
    std::unordered_map<std::string, size_t> protection_sites_;
    bool protection_dirty_ = false;
    bool protection_halted_ = false;
    enum class RefillPhase { Normal, DrainBefore, Refill, DrainAfter };
    RefillPhase refill_phase_ = RefillPhase::Normal;
    bool refill_base_only_ = false;
    unsigned refill_remaining_ = 0;
    uint64_t refill_resets_ = 0, refill_completed_ = 0, refill_publications_ = 0;
    uint64_t refill_drain_checks_ = 0;
    std::string schedule_path_, event_path_, summary_path_, manifest_path_;
    std::ofstream events_, origins_;
    std::ofstream maintenance_;
    std::ofstream activity_;
    gem5::Tick activity_end_=0;
    std::unordered_map<const Base::BranchInfo *, uint64_t> activity_owners_;
    const Base::BranchInfo *activity_append_context_=nullptr;
    uint64_t activity_next_owner_=0;
    std::map<int, std::set<uint64_t>> raw_origins_;
    size_t next_fault_ = 0;
    uint64_t flips_ = 0, origin_id_ = 0, observation_ordinal_ = 0;
    unsigned last_active_ = 0, last_live_ = 0;
    bool frozen_ = false, conditional_context_ = false;
    gem5::Tick exit_tick_ = 0;
    gem5::Tick declared_horizon_=0;
    gem5::Tick append_tick_=0, restore_tick_=0;
    uint64_t appends_this_tick_=0, restores_this_tick_=0;
    uint64_t history_generation_=0;
    gem5::Tick history_change_tick_=0;
    const NativeQueryOperands *staged_operands_=nullptr;
    gem5::EventFunctionWrapper injection_;
    gem5::EventFunctionWrapper lease_publication_;
    void loadFaults();
    void injectNext();
    size_t resolve(const std::string &) const;
    void writeManifest() const;
    bool activityOpen() const;
    void historyActivity(const char *op, uint64_t owner, uint64_t value, uint64_t auxiliary);
    void noteHistoryChange();
    void calculateIndicesAndTags(gem5::ThreadID, gem5::Addr, Base::BranchInfo *) override;
    void updatePathAndGlobalHistory(gem5::ThreadID, int, bool, gem5::Addr, gem5::Addr,
                                    Base::BranchInfo *) override;
    void condBranchUpdate(gem5::ThreadID, gem5::Addr, bool, Base::BranchInfo *, int,
                          gem5::Addr, bool, bool) override;

  public:
    QuiescentLease lease;
    NativeTAGE *owner = nullptr;
    uint64_t source_epoch = 0, buffer_epoch = 0, raw_writes = 0, conditional_writes = 0;
    uint64_t maximum_raw_appends_per_tick=0, maximum_raw_restores_per_tick=0;
    explicit NativeTAGEBase(const gem5::NativeTAGEBaseParams &);
    ~NativeTAGEBase() override;
    void init() override;
    void startup() override;
    void dumpResearch();
    bool protectionReady();
    bool refillDraining() const {
        return refill_phase_ == RefillPhase::DrainBefore || refill_phase_ == RefillPhase::DrainAfter;
    }
    bool refillPublishing() const {
        return refill_phase_ == RefillPhase::Refill || refill_phase_ == RefillPhase::DrainAfter;
    }
    void advanceRefillDrain(bool empty);
    void armLeasePublication();
    void publishLeaseFolds() {
        publish_own_folds(*this,words_);
        historyActivity("publish",0,0,0);
    }
    void activityQuery(gem5::Addr pc) { historyActivity("query",0,pc,0); }
    void activityQueryStage(const char *operation, uint32_t token, gem5::Addr pc) {
        historyActivity(operation,token,pc,0);
    }
    void activityRelease(const Base::BranchInfo *bi);
    void updateGHist(gem5::ThreadID, uint64_t, uint8_t) override;
    void updateHistories(gem5::ThreadID, gem5::Addr, bool, bool, gem5::Addr,
                         const gem5::StaticInstPtr &, Base::BranchInfo *) override;
    void restoreHistState(gem5::ThreadID, Base::BranchInfo *) override;
    std::set<uint64_t> originLabels(int head) const;
    void observeOrigins(const char *reason, bool force = false);
    bool originObservationEnabled() const { return origins_.is_open(); }
    bool basePrediction(gem5::Addr pc, const Base::BranchInfo &bi) const {
        return getBimodePred(pc, const_cast<Base::BranchInfo *>(&bi));
    }
    NativeSample sample(const Base::BranchInfo &, uint64_t lookup_id) const;
    NativeQueryOperands captureOperands(gem5::ThreadID, gem5::Addr) const;
    NativeReturnedRows captureRows(gem5::Addr, const NativeQueryOperands &) const;
    bool capturingActivity() const { return activityOpen(); }
    bool predictWithOperands(gem5::ThreadID, gem5::Addr, Base::BranchInfo *,
                             const NativeQueryOperands &);
    uint64_t historyGeneration() const { return history_generation_; }
    size_t appliedFaults() const { return next_fault_; }
    bool historyChangedThisTick() const {
        return history_generation_ && history_change_tick_ == gem5::curTick();
    }
};

class NativeTAGE : public gem5::branch_prediction::TAGE {
    struct Retired {
        uint64_t tick, logical_id;
        bool bpu_observed=false, pred_taken=false, cond_pred=false, btb_hit=false, mispredicted=false;
        unsigned target_provider=0;
    };
    std::unordered_map<void *, NativeSample> frames_;
    std::unordered_map<void *, Retired> retired_;
    std::unordered_set<void *> live_;
    struct RowObservation {
        const void *history=nullptr;
        gem5::Addr pc=0;
        uint32_t token=0;
        NativeQueryOperands operand;
        NativeReturnedRows rows;
        bool direction=false;
    };
    RowObservation row_observation_;
    std::ofstream row_activity_;
    gzFile trace_ = nullptr;
    bool observing_ = false;
    unsigned query_latency_ = 0;
    unsigned query_ii_cycles_ = 0;
    bool query_pipeline_ = false;
    bool single_training_port_ = false;
    bool pending_hash_captured_ = false;
    gem5::EventFunctionWrapper query_hash_latch_;
    NativeQueryOperands pending_operands_;
    uint64_t pending_generation_ = 0;
    size_t pending_fault_count_ = 0;
    gem5::Tick cycle_ticks_ = 500, ready_tick_ = 0;
    gem5::Tick next_query_tick_ = 0;
    gem5::Addr pending_pc_ = 0;
    uint32_t next_token_ = 0, pending_token_ = 0;
    bool pending_ = false;
    gem5::Tick lookup_tick_=0;
    uint64_t lookups_this_tick_=0, conditionals_this_tick_=0;
    unsigned restore_capacity_=512;
    uint64_t next_retired_branch_ = 0;
    gem5::Tick last_training_reservation_tick_=0, last_conditional_training_tick_=0;
    void writeTrace(const NativeSample *, const Retired *, gem5::Addr, bool, bool,
                    gem5::Addr, const Base::BranchInfo &);
    void latchQueryHash();
    void clearPendingQuery();
    void cancelPendingQuery();
    static NativeTAGEBase &checkedCore(gem5::branch_prediction::TAGEBase *);

  public:
    NativeTAGEBase &core;
    uint64_t lookups = 0, commit_updates = 0, conditional_updates = 0;
    uint64_t retired_ops = 0, retired_instructions = 0, retired_controls = 0;
    uint64_t retired_pc_identity = 14695981039346656037ULL, lookup_identity = 14695981039346656037ULL;
    uint64_t missing_lookup_mapping = 0, missing_retirement_mapping = 0;
    uint64_t missing_bpu_mapping=0, max_inflight=0, lease_frontend_wait_calls=0;
    uint64_t max_live_owners=0, missing_bpu_prediction_mapping=0;
    uint64_t maximum_lookups_per_tick=0, maximum_conditional_lookups_per_tick=0;
    uint64_t query_wait_calls = 0, delayed_requests = 0, canceled_requests = 0;
    unsigned queryLatency() const { return query_latency_; }
    unsigned queryInterval() const { return query_ii_cycles_; }
    bool queryPipeline() const { return query_pipeline_; }
    bool singleTrainingPort() const { return single_training_port_; }
    uint64_t training_port_reservations=0, training_port_waits=0;
    uint64_t refill_port_reservations=0, refill_port_waits=0;
    gem5::Tick last_refill_reservation_tick=0;
    uint64_t staged_responses=0, staged_retries=0, staged_operand_holds=0;
    uint64_t staged_responses_after_fault=0, staged_responses_with_changed_hash=0;
    uint64_t staged_captures=0, first_staged_hash_identity=0;
    gem5::Tick first_staged_issue_tick=0, first_staged_response_tick=0;
    gem5::Tick first_staged_capture_tick=0;
    uint64_t query_interval_wait_calls=0;
    bool force_base = false;
    explicit NativeTAGE(const gem5::NativeTAGEParams &);
    ~NativeTAGE() override;
    void update(gem5::ThreadID, gem5::Addr, bool, void *&, bool,
                const gem5::StaticInstPtr &, gem5::Addr) override;
    void squash(gem5::ThreadID, void *&) override;
    void seuAuditCommit(uint64_t, uint64_t, unsigned, bool, bool, void *) override;
    void seuAuditBranch(void*,bool,bool,bool,bool,unsigned) override;
    void seuAuditPrediction(void*,uint64_t,bool) override;
    void branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void *&) override;
    void seuAuditInflight(unsigned) override;
    bool seuFrontendBlocked(gem5::ThreadID, bool) override;
    bool seuHistoryReady() override { return core.protectionReady(); }
    void completeLease();
    void rebaseFrames(int offset);
    unsigned restorableOriginCount() const;
    void flushTrace();
    size_t pendingObservationFrames() const { return frames_.size(); }
    size_t liveHistoryOwners() const { return live_.size(); }
    bool seuPredictionRequest(gem5::ThreadID, gem5::Addr, bool, uint32_t &) override;
    bool seuCanRetire(gem5::ThreadID, void *) override;
    void seuReserveRetire(gem5::ThreadID, void *) override;
    void seuCancelPending(gem5::ThreadID) override;
    bool seuPipelineDrained() const override { return !pending_ && live_.empty(); }

  protected:
    bool predict(gem5::ThreadID, gem5::Addr, bool, void *&) override;
};
} // namespace bp
