#pragma once
#include "cpu/pred/tage.hh"
#include "params/PipelineV9R2TAGE.hh"
#include "params/PipelineV9R2TAGEBase.hh"
#include "sim/eventq.hh"
#include "/home/youns/workspace/ele548-project-v14/o3_finite_v14/src/source_access.hpp"
#include <fstream>
namespace gem5::o3 {class BAC;}
namespace bp::v14 {struct RecoveryBridge {static bool ready(gem5::o3::BAC&);};}
namespace bp {
class CpuPipelineV9R2TAGEBase:public v14::SourceAccess<RoundAccess> {
 const v14::Mode mode_;const unsigned update_L_,query_L_;
 const std::string summary_path_,manifest_path_;
 gem5::EventFunctionWrapper clock_;
 void run_clock();
 public:
 const gem5::Tick period;
 uint64_t recovery_hold_cycles=0,predictor_rng_draws=0,predictor_rng_hash=14695981039346656037ULL,committed_ops=0,committed_controls=0,committed_identity=14695981039346656037ULL,read_stalls=0,lookups=0;
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
