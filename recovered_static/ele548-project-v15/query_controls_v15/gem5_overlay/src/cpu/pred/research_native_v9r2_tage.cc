#include "cpu/pred/research_native_v9r2_tage.hh"
#include "cpu/o3/bac.hh"
#include "cpu/pred/bpred_unit.hh"
#include "base/logging.hh"
namespace bp {
static v15::Mode mode(const std::string&s){if(s=="recurrent")return v15::Mode::Recurrent;if(s=="direct")return v15::Mode::Direct;if(s=="overwrite")return v15::Mode::Overwrite;throw std::invalid_argument("v14 supports recurrent/direct/overwrite");}
CpuPipelineV9R2TAGEBase::CpuPipelineV9R2TAGEBase(const gem5::PipelineV9R2TAGEBaseParams&p):v15::SourceAccess<RoundAccess>(p),mode_(mode(p.representation)),update_L_(p.rmw_latency),query_L_(p.pipeline_latency),early_enabled_(p.role_policy=="V15_EARLY_UNCONDITIONAL"),summary_path_(p.summary_file),manifest_path_(p.manifest_file),clock_([this]{run_clock();},name()+".finite_source_v15",false,gem5::Event::CPU_Tick_Pri-2),period(p.cycle_ticks){
 fatal_if(!period||p.numThreads!=1||!p.speculativeHistUpdate||p.takenOnlyHistory||p.scheme!="P0"||p.pipeline_mode!="pipeline"||p.pipeline_ii!=1||p.rmw_ii!=1||p.lookup_latency||p.inspection_interval||p.maintenance_cycles||p.check_cycles||p.repair_cycles||(p.role_policy!="LEGACY"&&!early_enabled_)||p.resource_mode!="LEGACY"||p.cost_remove!="NONE"||!p.schedule_file.empty(),"V15 first integration is plain speculative P0 finite pipeline, no old schedule/protection modes");
}
CpuPipelineV9R2TAGEBase::~CpuPipelineV9R2TAGEBase(){if(clock_.scheduled())deschedule(clock_);}
void CpuPipelineV9R2TAGEBase::init(){v15::SourceAccess<RoundAccess>::init();configure(mode_,update_L_,query_L_);if(early_enabled_)enable_early();write_manifest();}
void CpuPipelineV9R2TAGEBase::startup(){fatal_if(gem5::curTick()!=0,"V15 requires tick0 reset; checkpoint import not implemented");schedule(clock_,period);}
void CpuPipelineV9R2TAGEBase::run_clock(){advance();
 // OBSERVATION_BEGIN
 max_lookup_pending=std::max(max_lookup_pending,engine->port.pending());max_source_pending=std::max(max_source_pending,engine->port.source.pending());
 // OBSERVATION_END
 schedule(clock_,gem5::curTick()+period);}
size_t CpuPipelineV9R2TAGEBase::table_bits()const{auto all=sites();size_t n=0;for(auto&s:all)if(s.kind<4)++n;return n;}
bool CpuPipelineV9R2TAGEBase::logical_bit(size_t id)const{auto all=sites();auto n=table_bits();if(id<n){const auto&s=all[id];return(payload(s)>>s.bit)&1;}return model_bit(id-n);}
void CpuPipelineV9R2TAGEBase::corrupt(const std::vector<size_t>&ids){auto n=table_bits();std::set<size_t> unique;std::vector<size_t> table,source;for(auto id:ids){if(id>=n+model_bits()||!unique.insert(id).second)throw std::invalid_argument("invalid v14 atomic logical fault sites");(id<n?table:source).push_back(id<n?id:id-n);}RoundAccess::corrupt(table);corrupt_model(source);}
void CpuPipelineV9R2TAGEBase::write_manifest(){
 if(manifest_path_.empty())return;std::ofstream out(manifest_path_);fatal_if(!out,"V15 manifest output unavailable");auto n=table_bits();
 out<<"{\"model\":\"V15_FINITE_SOURCE_INGRESS_PROVIDER_P0\",\"scope\":\"predictor tables plus finite source/controller; original allocator/RNG/CPU architectural storage excluded\",\"table_bits\":"<<n<<",\"total_logical_bits\":"<<n+model_bits()<<",\"source_update_L\":"<<(mode_==v15::Mode::Direct?1:update_L_)<<",\"source_query_L\":"<<query_L_<<",\"early_unconditional\":"<<(early?"true":"false")<<",\"early_checkpoint_bits\":"<<(early?early->bits():0)<<",\"provider_extra_L\":1,\"II\":1,\"ingress_capacity\":4,\"squash_reserved_commands\":2,\"regions\":[{\"name\":\"original_logical_tables_in_pinned_Site_order\",\"start\":0,\"bits\":"<<n<<'}';
 for(auto&r:model_manifest())out<<",{\"name\":\""<<r.name<<"\",\"start\":"<<n+r.start<<",\"bits\":"<<r.bits<<'}';
 out<<"],\"clock\":\"free-running actual gem5 events from reset; source reduction then additional actual provider edge\",\"squash_backpressure\":\"when incoming commit/decode squash cannot reserve two ingress cells, hold all O3 stages and existing time buffers; source/cache events continue; conservative global recovery hold; claimed late checkpoints finish before source cancellation/squash\",\"retirement\":\"one actual credit release per cycle; recovery-tagged source ACKs and every claimed late path checkpoint must complete before release\",\"source_interface\":\"1130bit retained register ring with actual pre/post130 taps; not one-port SRAM\",\"exclusions\":[\"provider helper history arrays are combinational operands only\",\"host pointer associations to four token-bound CPU-owned BranchInfo objects; binding token/PC/valid is included; CPU-owned BranchInfo/expected-token/BTB/RAS and original time-buffer/architectural state; no extra squash message copy\",\"absolute software cycle/hold helpers, elaboration constants and diagnostic counters\",\"old native allocator/aging/RNG metadata and combinational SET\"],\"assumptions\":[\"declared source L1/2 and provider1 are model timing, not measured clock\",\"actual two-copy SECDED parallel encode/decode including four extra97-bit early binding words and cancel control stage fit assumed\"],\"not_implemented\":[\"new protection controllers\",\"CPU fault schedule binding\",\"checkpoint restore\",\"decoupled/multithread frontend\"]}\n";
}
void CpuPipelineV9R2TAGEBase::dumpSeu(){
 if(summary_path_.empty())return;std::ofstream out(summary_path_);fatal_if(!out,"V15 summary unavailable");auto&s=engine->port.source.stats;
 out<<"{\"early_enabled\":"<<(early?"true":"false")<<",\"early_claimed\":"<<(early?early->claims:0)<<",\"early_delivered\":"<<(early?early->delivered:0)<<",\"early_pending\":"<<(early?early->pending():0)<<",\"early_metadata_repairs\":"<<(early?early->metadata_repairs:0)<<",\"early_cancel_requests\":"<<(early?early->deferred_cancels:0)<<",\"early_retire_wait_calls\":"<<early_retire_wait_calls<<',';
 // OBSERVATION_BEGIN
 out<<"\"max_lookup_pending\":"<<max_lookup_pending<<",\"max_source_pending\":"<<max_source_pending<<",\"retire_recovery_wait_calls\":"<<retire_recovery_wait_calls<<",\"retire_credit_decode_wait_calls\":"<<retire_credit_decode_wait_calls<<',';
 // OBSERVATION_END
 out<<"\"model\":\"V15_FINITE_SOURCE_P0\",\"representation\":\""<<(mode_==v15::Mode::Recurrent?"recurrent":mode_==v15::Mode::Direct?"direct":"overwrite")<<"\",\"tick\":"<<gem5::curTick()<<",\"source_cycles\":"<<engine->port.source.cycle()<<",\"lookups\":"<<lookups<<",\"read_stalls\":"<<read_stalls<<",\"recovery_core_hold_cycles\":"<<recovery_hold_cycles<<",\"ingress_enqueued\":"<<engine->enqueued<<",\"ingress_issued\":"<<engine->issued<<",\"ingress_max_count\":"<<engine->max_count<<",\"recovery_admission_waits\":"<<engine->recovery_waits<<",\"source_issue_waits\":"<<engine->source_issue_waits<<",\"read_ingress_waits\":"<<engine->read_ingress_waits<<",\"source_accepted\":"<<s.accepted<<",\"source_completed\":"<<s.completed<<",\"source_cancelled\":"<<s.cancelled<<",\"source_pending\":"<<engine->port.source.pending()<<",\"source_dependency_stalls\":"<<s.dependency_stalls<<",\"source_ordering_stalls\":"<<s.ordering_stalls<<",\"source_queue_stalls\":"<<s.input_full_stalls<<",\"source_response_stalls\":"<<s.response_stalls<<",\"source_II_stalls\":"<<s.II_stalls<<",\"bulk_undos\":"<<s.bulk_undos<<",\"bulk_bits\":"<<s.bulk_bits<<",\"metadata_repairs\":"<<s.metadata_repairs+engine->metadata_repairs+engine->port.metadata_repairs+(early?early->metadata_repairs:0)<<",\"wrap_completions\":"<<s.wrap_completions<<",\"lookup_accepted\":"<<engine->port.accepted<<",\"lookup_produced\":"<<engine->port.produced<<",\"lookup_consumed\":"<<engine->port.consumed<<",\"lookup_cancelled\":"<<engine->port.cancelled<<",\"lookup_pending\":"<<engine->port.pending()<<",\"predictor_rng_draws\":"<<predictor_rng_draws<<",\"predictor_rng_hash\":"<<predictor_rng_hash<<",\"committed_ops\":"<<committed_ops<<",\"committed_controls\":"<<committed_controls<<",\"committed_identity\":"<<committed_identity<<",\"conserved\":"<<(conserved()?"true":"false")<<",\"applied_faults\":0,\"timing_qualification\":\"MODEL_ONLY\"}\n";
}
CpuPipelineV9R2TAGE::CpuPipelineV9R2TAGE(const gem5::PipelineV9R2TAGEParams&p):TAGE(p),core(*dynamic_cast<CpuPipelineV9R2TAGEBase*>(p.tage)){}
bool CpuPipelineV9R2TAGE::seuFrontendBlocked(gem5::ThreadID tid,bool){fatal_if(tid,"V15 single thread");return false;}
bool CpuPipelineV9R2TAGE::seuPredictionRequest(gem5::ThreadID tid,gem5::Addr pc,bool conditional,uint32_t& token){
 fatal_if(tid,"V15 single thread");if(!token){auto t=core.request(pc,conditional);if(!t){++core.read_stalls;return false;}token=t->packed();core.max_lookup_pending=std::max(core.max_lookup_pending,core.engine->port.pending());core.max_source_pending=std::max(core.max_source_pending,core.engine->port.source.pending());}
 if(core.early&&!core.early->ready()){++core.read_stalls;return false;}
 if(!conditional&&core.early_ready(v15::Token::unpack(token),pc))return true;
 auto r=core.engine->peek(v15::Token::unpack(token));if(!r){++core.read_stalls;return false;}
 fatal_if(r->pc!=pc||r->conditional!=conditional,"V15 actual PC/type response ownership");return true;
}
bool CpuPipelineV9R2TAGE::seuPredictionReady(gem5::ThreadID tid,gem5::Addr pc,bool conditional){fatal_if(tid,"V15 single thread");
 if(core.early){if(!core.early->ready())return false;if(!conditional){for(const auto&d:core.engine->port.descriptors())if(core.early_ready(d.token,pc))return true;return false;}}
 auto r=core.engine->head();return r&&r->pc==pc&&r->conditional==conditional;
}
bool CpuPipelineV9R2TAGE::predict(gem5::ThreadID tid,gem5::Addr pc,bool conditional,void*&history){
 fatal_if(tid||history,"V15 response consumer");
 if(!conditional&&core.early){auto*info=new TageBranchInfo(core,pc,false);core.consume_early(pc,info->tageBranchInfo);history=info;++core.lookups;return true;}
 auto r=core.engine->head();fatal_if(!r||r->pc!=pc||r->conditional!=conditional,"V15 response not actually ready");auto out=core.engine->take(r->token);fatal_if(!out,"V15 response disappeared within non-yielding consume");
 auto*info=new TageBranchInfo(core,pc,conditional);out->payload.restore_response(*info->tageBranchInfo);info->tageBranchInfo->pathHist=out->path;history=info;++core.lookups;return out->payload.get(25);
}
void CpuPipelineV9R2TAGE::seuCancelPending(gem5::ThreadID tid){fatal_if(tid,"V15 single thread");core.cancel();}
void CpuPipelineV9R2TAGE::seuSquashBegin(gem5::ThreadID tid){fatal_if(tid,"V15 single thread");core.engine->begin();}
void CpuPipelineV9R2TAGE::seuSquashEnd(gem5::ThreadID tid){fatal_if(tid,"V15 single thread");core.engine->end();}
bool CpuPipelineV9R2TAGE::seuPipelineDrained()const{return core.engine&&core.drained();}
bool CpuPipelineV9R2TAGE::seuCanRetire(gem5::ThreadID tid,void*history){fatal_if(tid,"V15 single thread");if(!history)return true;const bool ready=core.can_retire(static_cast<TageBranchInfo*>(history)->tageBranchInfo->nGhist);
 // OBSERVATION_BEGIN
 if(!ready){if(core.early&&!core.early->quiescent())++core.early_retire_wait_calls;else if(core.engine->diagnostic_recovery_waiting())++core.retire_recovery_wait_calls;else ++core.retire_credit_decode_wait_calls;}
 // OBSERVATION_END
 return ready;}
void CpuPipelineV9R2TAGE::seuReserveRetire(gem5::ThreadID tid,void*history){fatal_if(tid,"V15 single thread");if(history)fatal_if(!core.retire(static_cast<TageBranchInfo*>(history)->tageBranchInfo->nGhist),"V15 retirement without actual source credit");}
void CpuPipelineV9R2TAGE::update(gem5::ThreadID tid,gem5::Addr pc,bool taken,void*&history,bool squashed,const gem5::StaticInstPtr&inst,gem5::Addr target){
 fatal_if(!history,"V15 training has no owned BI");auto* info=static_cast<TageBranchInfo*>(history);auto*bi=info->tageBranchInfo;if(squashed){core.squash(tid,taken,target,inst,bi);return;}
 int draw=rng->random<int>()&3;++core.predictor_rng_draws;core.predictor_rng_hash^=uint64_t(draw);core.predictor_rng_hash*=1099511628211ULL;
 if(bi->condBranch){core.updateStats(taken,bi);core.condBranchUpdate(tid,pc,taken,bi,draw,target,bi->tagePred);}core.updateHistories(tid,pc,false,taken,target,inst,bi);delete info;history=nullptr;
}
void CpuPipelineV9R2TAGE::seuAuditCommit(uint64_t,uint64_t pc,unsigned micro,bool last,bool control,void*){++core.committed_ops;core.committed_controls+=control;for(uint64_t value:{pc,uint64_t(micro),uint64_t(last),uint64_t(control)}){core.committed_identity^=value;core.committed_identity*=1099511628211ULL;}}
void CpuPipelineV9R2TAGE::branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void*&){fatal("V15 decoupled frontend not supported");}
}
namespace bp::v15 {
bool RecoveryBridge::ready(gem5::o3::BAC& bac){
 auto*pred=dynamic_cast<bp::CpuPipelineV9R2TAGE*>(bac.bpu->cPred);if(!pred)return true;
 fatal_if(bac.numThreads!=1||bac.decoupledFrontEnd,"V15 requires one thread coupled frontend");
 bool incoming=bac.fromCommit->commitInfo[0].squash||bac.fromDecode->decodeInfo[0].squash;if(!incoming)return true;
 if(!pred->core.prepare_recovery()){++pred->core.recovery_hold_cycles;return false;}return true;
}
}
