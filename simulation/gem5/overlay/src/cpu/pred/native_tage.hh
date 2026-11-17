#pragma once
#include "cpu/pred/tage.hh"
#include "params/NativeTAGE.hh"
#include "params/NativeTAGEBase.hh"
#include "sim/eventq.hh"
#include "tage/predictor/tage_access.hpp"
#include "tage/history/direct_access.hpp"
#include "tage/history/lease.hpp"
#include <fstream>
#include <map>
#include <set>
#include <unordered_map>
#include <unordered_set>
#include <zlib.h>

namespace bp {
class NativeTAGE;
struct NativeSample {
    uint64_t lookup_id = 0, lookup_tick = 0, epoch = 0, buffer_epoch = 0;
    int head = 0, restore_head = 0;
    Word raw;
    unsigned path = 0, nonspec_path = 0, invariant_distance = 0;
    std::vector<unsigned> folds, indices, tags;
    bool bpu_target_observed=false;
    uint64_t bpu_predicted_target=0;
};

// No finite-source controller, codec, periodic service clock, or extra
// retirement/lookup delay is inserted into the ordinary TAGE path.
class NativeTAGEBase : public DirectAccess<TageAccess> {
    struct Fault {
        gem5::Tick tick;
        std::vector<std::string> sites;
    };
    std::vector<Fault> faults_;
    std::vector<Site> sites_;
    std::vector<HistoryWord> words_;
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
    gem5::EventFunctionWrapper injection_;
    gem5::EventFunctionWrapper lease_publication_;
    void loadFaults();
    void injectNext();
    size_t resolve(const std::string &) const;
    void writeManifest() const;
    bool activityOpen() const;
    void historyActivity(const char *op, uint64_t owner, uint64_t value, uint64_t auxiliary);

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
    void armLeasePublication();
    void publishLeaseFolds() {
        publish_own_folds(*this,words_);
        historyActivity("publish",0,0,0);
    }
    void activityQuery(gem5::Addr pc) { historyActivity("query",0,pc,0); }
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
    gzFile trace_ = nullptr;
    bool observing_ = false;
    unsigned query_latency_ = 0;
    gem5::Tick cycle_ticks_ = 500, ready_tick_ = 0;
    gem5::Addr pending_pc_ = 0;
    uint32_t next_token_ = 0, pending_token_ = 0;
    bool pending_ = false;
    gem5::Tick lookup_tick_=0;
    uint64_t lookups_this_tick_=0, conditionals_this_tick_=0;
    unsigned restore_capacity_=512;
    uint64_t next_retired_branch_ = 0;
    void writeTrace(const NativeSample *, const Retired *, gem5::Addr, bool, bool,
                    gem5::Addr, const Base::BranchInfo &);
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
    bool force_base = false;
    explicit NativeTAGE(const gem5::NativeTAGEParams &);
    ~NativeTAGE() override;
    void update(gem5::ThreadID, gem5::Addr, bool, void *&, bool,
                const gem5::StaticInstPtr &, gem5::Addr) override;
    void squash(gem5::ThreadID, void *&) override;
    void seuAuditCommit(uint64_t, uint64_t, unsigned, bool, bool, void *) override;
    void seuAuditBranch(void*,bool,bool,bool,bool,unsigned) override;
    void seuAuditPrediction(void*,uint64_t) override;
    void branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void *&) override;
    void seuAuditInflight(unsigned) override;
    bool seuFrontendBlocked(gem5::ThreadID, bool) override;
    void completeLease();
    void rebaseFrames(int offset);
    unsigned restorableOriginCount() const;
    void flushTrace();
    size_t pendingObservationFrames() const { return frames_.size(); }
    size_t liveHistoryOwners() const { return live_.size(); }
    bool seuPredictionRequest(gem5::ThreadID, gem5::Addr, bool, uint32_t &) override;
    void seuCancelPending(gem5::ThreadID) override;
    bool seuPipelineDrained() const override { return !pending_ && live_.empty(); }

  protected:
    bool predict(gem5::ThreadID, gem5::Addr, bool, void *&) override;
};
} // namespace bp
