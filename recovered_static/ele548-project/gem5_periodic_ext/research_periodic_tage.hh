#ifndef BP_PERIODIC_TAGE_HH
#define BP_PERIODIC_TAGE_HH
#include "cpu/pred/tage.hh"
#include "params/PeriodicTAGE.hh"
#include "params/PeriodicTAGEBase.hh"
#include "sim/eventq.hh"
#include "sim/cur_tick.hh"
#include "../../../../../src/protection/periodic_spec_history.hpp"
#include <fstream>
#include <memory>
namespace bp {
class CpuPeriodicTAGEBase: public TageAccess {
 public:
    struct EventSpec {gem5::Tick tick;std::vector<size_t> ids;};
    const gem5::Tick period;
    const unsigned check_cycles,repair_cycles,inspection_interval;
    std::unique_ptr<PeriodicHistoryController> protection;
    std::unique_ptr<PeriodicSpecHistoryProtocol> protocol;
    uint64_t applied_events=0,applied_flips=0,prediction_reads=0;
    uint64_t response_hold_cycles=0,drain_hold_cycles=0,cancelled_responses=0,retried_responses=0;
    uint64_t lookups_at_fault_tick=0;
    uint64_t predictor_rng_draws=0,predictor_rng_hash=14695981039346656037ULL;
    gem5::Tick repair_busy_until=0; // Explicit excluded simulator timing tag.
    uint64_t repair_batches=0;
    std::array<uint64_t,6> repairs_by_origin{};
    gem5::Tick last_fault_tick=~gem5::Tick(0);
    explicit CpuPeriodicTAGEBase(const gem5::PeriodicTAGEBaseParams& p);
    void init() override;
    void startup() override;
    void dumpSeu();
    void note_prediction_read(gem5::Addr pc,bool conditional);
    void account_repairs(uint64_t detected_before,unsigned origin);
 private:
    Scheme selected;
    std::string schedule_path,event_path,summary_path,manifest_path,read_path;
    unsigned read_limit;
    std::vector<EventSpec> events;
    size_t cursor=0;
    std::ofstream event_output;
    std::ofstream read_output;
    std::ofstream repair_output;
    gem5::EventFunctionWrapper injection;
    void inject_next();
    void write_manifest();
};
class CpuPeriodicTAGE: public gem5::branch_prediction::TAGE {
    CpuPeriodicTAGEBase& core;
    struct CpuInfo: public TageBranchInfo {
        EpochRecord record;
        CpuInfo(Base& base,gem5::Addr pc,bool cond,EpochRecord r):TageBranchInfo(base,pc,cond),record(r){}
    };
    struct Pending {
        bool active=false,read=false,conditional=false,prediction=false;
        gem5::Addr pc=0;
        gem5::Tick check_due=0,response_due=0;
        CpuInfo* info=nullptr;
    } pending;
    bool read_pending(gem5::ThreadID tid);
 protected:
    bool predict(gem5::ThreadID tid,gem5::Addr pc,bool conditional,void*& history) override;
 public:
    explicit CpuPeriodicTAGE(const gem5::PeriodicTAGEParams& p);
    ~CpuPeriodicTAGE() override;
    bool seuFrontendBlocked(gem5::ThreadID tid,bool history_empty) override;
    bool seuPredictionReady(gem5::ThreadID tid,gem5::Addr pc,bool conditional) override;
    void seuCancelPending(gem5::ThreadID tid) override;
    void updateHistories(gem5::ThreadID tid,gem5::Addr pc,bool uncond,bool taken,gem5::Addr target,
                        const gem5::StaticInstPtr& inst,void*& history) override;
    void update(gem5::ThreadID tid,gem5::Addr pc,bool taken,void*& history,bool squashed,
                const gem5::StaticInstPtr& inst,gem5::Addr target) override;
    void squash(gem5::ThreadID tid,void*& history) override;
    void branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void*&) override;
};
}
#endif
