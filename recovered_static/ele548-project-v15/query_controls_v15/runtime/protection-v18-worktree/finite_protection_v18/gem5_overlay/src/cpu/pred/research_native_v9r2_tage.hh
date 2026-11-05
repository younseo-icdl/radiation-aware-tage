#pragma once
#include "cpu/pred/tage.hh"
#include "params/PipelineV9R2TAGE.hh"
#include "params/PipelineV9R2TAGEBase.hh"
#include "sim/eventq.hh"
#include "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/protection-v18-worktree/finite_protection_v18/src/source_access.hpp"
#include <fstream>
namespace gem5::o3 {class BAC;}
namespace bp::v15 {struct RecoveryBridge {static bool ready(gem5::o3::BAC&);};}
namespace bp {
class CpuPipelineV9R2TAGEBase:public v18::SourceAccess<RoundAccess> {
 const v18::Mode mode_;const unsigned update_L_,query_L_;
 const bool early_enabled_;
 const std::string summary_path_,manifest_path_,scheme_name_,schedule_path_,event_path_;
 const unsigned inspection_;
 struct Fault {gem5::Tick tick,lower_tick;std::vector<std::string> sites;bool gated=false;};
 std::vector<Fault> faults_;size_t fault_index_=0;bool faults_frozen_=false;gem5::Tick censor_tick_=0;
 uint64_t applied_events_=0,applied_flips_=0;
 std::ofstream event_output_,detector_output_;uint64_t previous_detected_=0,previous_resets_=0;bool previous_fallback_=false;gem5::EventFunctionWrapper injection_;
 void load_faults();void inject_next();size_t resolve_site(const std::string&)const;
 gem5::EventFunctionWrapper clock_;
 void run_clock();
 public:
 const gem5::Tick period;
 uint64_t recovery_hold_cycles=0,predictor_rng_draws=0,predictor_rng_hash=14695981039346656037ULL,committed_ops=0,committed_controls=0,committed_identity=14695981039346656037ULL,read_stalls=0,lookups=0;
 // OBSERVATION_BEGIN
 uint64_t max_lookup_pending=0,max_source_pending=0,retire_recovery_wait_calls=0,retire_credit_decode_wait_calls=0,early_retire_wait_calls=0;
 // OBSERVATION_END
 explicit CpuPipelineV9R2TAGEBase(const gem5::PipelineV9R2TAGEBaseParams&);
 ~CpuPipelineV9R2TAGEBase()override;
 void init()override;void startup()override;void dumpSeu();
 void write_manifest();
 size_t table_bits()const;bool logical_bit(size_t)const;void corrupt(const std::vector<size_t>&);
};
class CpuPipelineV9R2TAGE:public gem5::branch_prediction::TAGE {
 public:
 CpuPipelineV9R2TAGEBase& core;
 explicit CpuPipelineV9R2TAGE(const gem5::PipelineV9R2TAGEParams&);
 bool seuPredictionRequest(gem5::ThreadID,gem5::Addr,bool,uint32_t&)override;
 bool seuPredictionReady(gem5::ThreadID,gem5::Addr,bool)override;
 bool seuFrontendBlocked(gem5::ThreadID,bool)override;
 bool seuPipelineDrained()const override;
 void seuCancelPending(gem5::ThreadID)override;
 void seuSquashBegin(gem5::ThreadID)override;void seuSquashEnd(gem5::ThreadID)override;
 bool seuCanRetire(gem5::ThreadID,void*)override;void seuReserveRetire(gem5::ThreadID,void*)override;
 void seuAuditCommit(uint64_t,uint64_t,unsigned,bool,bool,void*)override;
 void update(gem5::ThreadID,gem5::Addr,bool,void*&,bool,const gem5::StaticInstPtr&,gem5::Addr)override;
 void branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void*&)override;
 protected:
 bool predict(gem5::ThreadID,gem5::Addr,bool,void*&)override;
};
}
