#ifndef BP_PERIODIC_TAGE_HH
#define BP_PERIODIC_TAGE_HH
#include "cpu/pred/tage.hh"
#include "params/RateStateV5TAGE.hh"
#include "params/RateStateV5TAGEBase.hh"
#include "sim/eventq.hh"
#include "sim/cur_tick.hh"
#include "../../../../../src/rate_state_v5_r5_support/role_spec_history.hpp"
#include "../../../../../src/rate_state_v5_r5_support/work_counter.hpp"
#include <fstream>
#include <memory>
#include <functional>
#define BP_V5_CPU_CONTEXT
#include "../../../../../src/rate_state_v5_r5/representation.hpp"
#undef BP_V5_CPU_CONTEXT
#include "../../../../../src/rate_state_v5_r5/batch_undo.hpp"
#include "../../../../../src/rate_state_v5_r5_support/finite_fifo.hpp"
#include "../../../../../src/rate_state_v5_r5_support/ready_credits.hpp"
#include "../../../../../src/rate_state_v5_r5_support/protected_counter.hpp"
namespace bp {
class CpuRateStateV5TAGEBase: public v5::RepresentationAccess<RoundAccess> {
 public:
    const unsigned lookup_latency,lookup_ii;
    const bool journal_service,journal_merge_undo;
    const unsigned undo_batch_latency;
    v5::UndoBatch undo_batch;
    uint64_t primitive_undos=0,undo_packets=0,coalesced_undo_operations=0;
    FiniteRmwQueue journal_queue;
    gem5::EventFunctionWrapper journal_clock;
    void enqueue_journal(bool,unsigned,uint64_t,unsigned);
    void push_journal(bool,unsigned,uint64_t,unsigned);
    void finish_undo_batch();
    void run_journal();
    gem5::Tick next_lookup_issue=0;
    uint64_t lookup_issues=0;
    std::function<bool(unsigned)> pending_bit;
    std::function<void(unsigned)> flip_pending;
    size_t internal_bits()const{return protection->exposed_bits()+(endpoint()?endpoint_bits():(maintenance_cycles?BurstWorkCounter::width:0));}
    size_t active_base_bits()const{return sites().size()-(direct()?200:0);}
    size_t representation_bits()const{return direct()?1011+68+(journal_service?journal_queue.bits():0):0;}
    size_t to_internal(size_t id)const{return direct()&&id>=active_base_bits()?id+200:id;}
    struct EventSpec {gem5::Tick tick;std::vector<size_t> ids;};
    const gem5::Tick period;
    const unsigned check_cycles,repair_cycles,inspection_interval,maintenance_cycles;
    const std::string cost_remove;const bool full_delta,reset_recovery;
    const RoundPolicy role_policy;
    const std::string resource_mode;const bool decouple_shadow;
    const unsigned rmw_latency,rmw_ii;
    const unsigned promotion_group;const bool sham_wait;
    const std::string audit_path;const unsigned audit_limit;
    std::ofstream phase_output,audit_output,training_output;
    std::array<uint64_t,5> unique_waits{};
    std::array<gem5::Tick,5> wait_tick{{~0ULL,~0ULL,~0ULL,~0ULL,~0ULL}};
    uint64_t audit_ops=0,audit_insts=0,audit_controls=0,audit_identity=14695981039346656037ULL;
    uint64_t audit_predictions=0,audit_inflight=0,observed_squash_calls=0,observed_correct_calls=0;
    bool drain_open=false;unsigned drain_epoch=0,drain_target=0;
    std::function<bool()> audit_pending;
    uint64_t history_fingerprint()const;
    uint64_t table_fingerprint(Base::BranchInfo*)const;
    void wait(unsigned kind);
    void phase(const char* event,const char* reason,bool history_empty=false);
    void phase_pre(bool history_empty);void phase_complete(bool history_empty);
    FiniteRmwQueue hot_queue,shadow_queue;ReadyCredits credits{1024};
    ProtectedCounter32 issued_sequence,published_sequence;ProtectedCounter32 reservations{16};
    std::vector<void*> metadata_pool=std::vector<void*>(1024,nullptr);
    std::function<void(const Word&)> complete_hot;
    std::function<void()> reclaim_cancelled;
    bool fair_turn=false;uint64_t queue_failures=0,retire_block_cycles=0,early_publish=0;
    std::ofstream resource_output;
    gem5::EventFunctionWrapper work_clock;
    bool endpoint()const{return resource_mode!="LEGACY";}
    void arm_clock();void run_clock();void start_work();void queue_failure();
    void reserve_commit(bool hot,bool shadow);void consume_reservation(bool hot,bool shadow);
    uint16_t allocate_metadata(void*);void release_metadata(unsigned);
    void enqueue_hot(unsigned kind,unsigned handle,bool actual,const EpochRecord&,unsigned nrand=0);
    void enqueue_shadow(uint64_t pc,bool actual);
    bool can_retire(unsigned handle,bool needs_hot);
    size_t endpoint_bits()const;
    bool endpoint_bit(size_t)const;void flip_endpoint(size_t);

    gem5::Tick last_rebuild_advance=~gem5::Tick(0);
    BurstWorkCounter maintenance;
    size_t exposed_bits()const{return internal_bits()-(direct()?200:0)+representation_bits();}
    bool logical_bit(size_t id)const;
    bool logical_bit_at(size_t id,unsigned pre_event_head)const;
    void corrupt(const std::vector<size_t>& ids);
    uint64_t max_update_queue=0,update_jobs=0,maintenance_hold_cycles=0;
    uint64_t last_write_count=0,last_shadow_encode=0,cost_seq=0,source_jobs=0,shadow_jobs=0;
    std::ofstream cost_output;
    void account_update_work();
    void advance_rebuild_clock();
    std::unique_ptr<RoundHistory> protection;
    std::unique_ptr<RoundProtocol> protocol;
    uint64_t applied_events=0,applied_flips=0,prediction_reads=0;
    uint64_t response_hold_cycles=0,drain_hold_cycles=0,cancelled_responses=0,retried_responses=0;
    uint64_t lookups_at_fault_tick=0;
    uint64_t predictor_rng_draws=0,predictor_rng_hash=14695981039346656037ULL;
    gem5::Tick repair_busy_until=0; // Explicit excluded simulator timing tag.
    uint64_t repair_batches=0;
    std::array<uint64_t,7> repairs_by_origin{};
    gem5::Tick last_fault_tick=~gem5::Tick(0);
    explicit CpuRateStateV5TAGEBase(const gem5::RateStateV5TAGEBaseParams& p);
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
    std::ofstream rebuild_output;
    gem5::EventFunctionWrapper injection;
    void inject_next();
    void write_manifest();
};
class CpuRateStateV5TAGE: public gem5::branch_prediction::TAGE {
    CpuRateStateV5TAGEBase& core;
    struct CpuInfo: public TageBranchInfo {
        EpochRecord record;unsigned handle=1024;bool released=false;
        // Observational provenance only; never read by production decisions.
        uint64_t audit_id=0,audit_read_tick=0,audit_history=0,audit_table=0,audit_index=0,audit_rng=0,audit_draws=0;
        unsigned audit_hit=0,audit_alt=0;bool audit_pred=false;
        unsigned audit_hot=0,audit_live=0;
        CpuInfo(Base& base,gem5::Addr pc,bool cond,EpochRecord r):TageBranchInfo(base,pc,cond),record(r){}
    };
    struct Pending {
        bool active=false,read=false,conditional=false,prediction=false;
        gem5::Addr pc=0;
        gem5::Tick check_due=0,response_due=0;
        CpuInfo* info=nullptr;
    } pending;
    bool read_pending(gem5::ThreadID tid);
    void complete_job(const Word&);void cleanup_cancelled();
    bool needs_commit_job(CpuInfo*)const;
 protected:
    bool predict(gem5::ThreadID tid,gem5::Addr pc,bool conditional,void*& history) override;
 public:
    explicit CpuRateStateV5TAGE(const gem5::RateStateV5TAGEParams& p);
    ~CpuRateStateV5TAGE() override;
    bool seuFrontendBlocked(gem5::ThreadID tid,bool history_empty) override;
    bool seuPredictionReady(gem5::ThreadID tid,gem5::Addr pc,bool conditional) override;
    void seuCancelPending(gem5::ThreadID tid) override;
    void updateHistories(gem5::ThreadID tid,gem5::Addr pc,bool uncond,bool taken,gem5::Addr target,
                        const gem5::StaticInstPtr& inst,void*& history) override;
    void update(gem5::ThreadID tid,gem5::Addr pc,bool taken,void*& history,bool squashed,
                const gem5::StaticInstPtr& inst,gem5::Addr target) override;
    void squash(gem5::ThreadID tid,void*& history) override;
    bool seuCanRetire(gem5::ThreadID,void*) override;
    void seuReserveRetire(gem5::ThreadID,void*) override;
    void branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void*&) override;
    void seuAuditCommit(uint64_t,uint64_t,unsigned,bool,bool,void*) override;
    void seuAuditInflight(unsigned count) override {core.audit_inflight=count;}
    void seuSquashBegin(gem5::ThreadID) override {if(core.journal_merge_undo)core.undo_batch.begin();}
    void seuSquashEnd(gem5::ThreadID) override {if(core.journal_merge_undo)core.finish_undo_batch();}
};
}
#endif
