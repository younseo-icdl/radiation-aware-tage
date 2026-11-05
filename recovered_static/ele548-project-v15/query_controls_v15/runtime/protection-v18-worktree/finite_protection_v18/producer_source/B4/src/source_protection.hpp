#pragma once
#include "vector_protection.hpp"
namespace bp::v18b4 {
// Finite source integration. Fault-triggered recovery keeps stale CPU BIs in
// fallback until committed refill AND an actual full receiver/CPU drain ACK.
// It does not need to trust stale rollback operands during this interval.
class FiniteProtection:public SourceGuard {
 struct Action {bool pending=false,authorized=false;uint32_t token=0,residual=0,authorized_token=0;};
 Cell action_{89};bool hold_=false;Words sampled_{};bool direct_;
 static Word pack(Action a){Word w;w.set(0,a.pending);put(w,1,32,a.token);put(w,33,23,a.residual);w.set(56,a.authorized);put(w,57,32,a.authorized_token);return w;}
 Action load(){bool fixed=false;auto w=action_.load(fixed);if(fixed){hold_=true;++metadata_repairs;}return {w.bit(0),w.bit(56),get(w,1,32),get(w,33,23),get(w,57,32)};}
 void store(Action a){action_.store(pack(a));}
 unsigned payload_bits()const{return direct_?146:346;}
 bool payload_bit(unsigned n)const{auto widths=unit_widths_;for(unsigned w=0;w<23;++w)if(!direct_||w>=21){if(n<widths[w])return sampled_[w].bit(n);n-=widths[w];}throw std::out_of_range("authorized source payload");}
 void payload_flip(unsigned n){for(unsigned w=0;w<23;++w)if(!direct_||w>=21){if(n<unit_widths_[w]){sampled_[w].flip(n);return;}n-=unit_widths_[w];}throw std::out_of_range("authorized source payload");}
 std::array<unsigned,23>unit_widths_;
 public:
 VectorProtection unit;
 uint64_t source_checks=0,source_repair_publications=0,suppressed_stale_source_ops=0,committed_refill_publications=0,publication_waits=0,metadata_repairs=0;
 FiniteProtection(std::array<unsigned,23>w,Protect p,bool direct=false,unsigned epoch_bits=32):direct_(direct),unit_widths_(w),unit(w,p,direct,epoch_bits){store({});}
 std::unique_ptr<SourceGuard> clone()const override{return std::make_unique<FiniteProtection>(*this);}
 bool authorize(const std::function<void(unsigned,const Word&)>&write,uint32_t token,bool lookup,unsigned kind,uint32_t version,const Words&actual)override{
  auto a=load();if(hold_)return false;
  if(a.authorized){if(a.authorized_token!=token||!unit.ready())return false;a.authorized=false;store(a);return true;}
  if(a.pending)return false;
  if(auto out=unit.take(token,version)){
   sampled_=out->words;++source_checks;
   for(unsigned w=0;w<23;++w)if((out->reset||((out->repair_mask>>w)&1))&&(!direct_||w>=21)){write(w,out->words[w]);++source_repair_publications;}
   if(lookup&&out->reset){if(!unit.publish(token,version,sampled_,0,false))throw IntegrityError("reset encode without owned check slot");a.authorized=true;a.authorized_token=token;store(a);return false;}
   if(!lookup){a.pending=true;a.token=token;a.residual=out->residual;store(a);if(unit.fallback()&&(kind==unsigned(Kind::Append)||kind==unsigned(Kind::Undo)))++suppressed_stale_source_ops;}
   return true;
  }
  if(unit.ready())unit.sample(token,version,lookup,actual);return false;
 }
 const Words&sampled()const override{return sampled_;}
 void prefetch(uint32_t token,bool lookup,uint32_t version,const Words&actual)override{auto a=load();if(!hold_&&!a.pending&&!a.authorized&&unit.ready())unit.sample(token,version,lookup,actual);}
 bool can_publish(uint32_t token)override{auto a=load();const bool result=!hold_&&a.pending&&a.token==token&&unit.ready();if(!result)++publication_waits;return result;}
 void published(uint32_t token,unsigned kind,uint32_t version,const Words&actual)override{
  auto a=load();const bool history_update=kind==unsigned(Kind::CommittedHistory)||!unit.fallback()&&(kind==unsigned(Kind::Append)||kind==unsigned(Kind::Undo));if(hold_||!a.pending||a.token!=token||!unit.publish(token,version,actual,a.residual,history_update))throw IntegrityError("source publication did not own finite encoder");
  a.pending=false;store(a);if(kind==unsigned(Kind::CommittedHistory)){unit.committed_refill();++committed_refill_publications;}
 }
 void advance()override{if(hold_){hold_=false;return;}unit.advance();}
 void cancel_reads()override{unit.cancel_lookup();auto a=load();a.authorized=false;store(a);}
 bool fallback()override{return unit.fallback();}
 uint32_t epoch()override{return unit.epoch();}
 bool drained()override{auto a=load();return !hold_&&!a.pending&&!a.authorized&&unit.drained();}
 void acknowledge_refill_and_epoch_drained(){if(!drained())throw IntegrityError("protection ACK before source drain");if(unit.wrap_waiting())unit.acknowledge_epoch_drained();unit.acknowledge_refill_drained();}
 std::vector<Region> manifest()const override{
  std::vector<Region> out;size_t at=0;for(auto&r:unit.manifest()){out.push_back({r.name,at,r.bits});at+=r.bits;}
  out.push_back({"protect_source_action_mirrored_SECDED",at,action_.bits()});at+=action_.bits();out.push_back({"protect_source_action_hold",at++,1});out.push_back({"protect_authorized_source_payload",at,payload_bits()});return out;
 }
 size_t bits()const override{auto m=manifest();return m.back().start+m.back().bits;}
 bool logical_bit(size_t n)const override{if(n>=bits())throw std::out_of_range("finite source protection bit");if(n<unit.bits())return unit.logical_bit(n);n-=unit.bits();if(n<action_.bits())return action_.bit(n);n-=action_.bits();if(!n)return hold_;return payload_bit(n-1);}
 void corrupt(const std::vector<size_t>&ids)override{
  std::set<size_t> unique;for(auto n:ids)if(n>=bits()||!unique.insert(n).second)throw std::invalid_argument("finite source protection atomic sites");
  for(auto n:ids){if(n<unit.bits()){unit.corrupt({n});continue;}n-=unit.bits();if(n<action_.bits()){action_.flip(n);continue;}n-=action_.bits();if(!n)hold_=!hold_;else payload_flip(n-1);}
 }
};
}
#include "cpu/pred/research_native_v9r2_tage.hh"
#include "cpu/o3/bac.hh"
#include "cpu/pred/bpred_unit.hh"
#include "base/logging.hh"
#include <sstream>
#include <iomanip>
namespace bp {
static v18b4::Mode mode(const std::string&s){if(s=="recurrent")return v18b4::Mode::Recurrent;if(s=="direct")return v18b4::Mode::Direct;if(s=="overwrite")return v18b4::Mode::Overwrite;throw std::invalid_argument("v14 supports recurrent/direct/overwrite");}
CpuPipelineV9R2TAGEBase::CpuPipelineV9R2TAGEBase(const gem5::PipelineV9R2TAGEBaseParams&p):v18b4::SourceAccess<RoundAccess>(p),mode_(mode(p.representation)),update_L_(p.rmw_latency),query_L_(p.pipeline_latency),early_enabled_(p.role_policy=="V18_EARLY_UNCONDITIONAL"),summary_path_(p.summary_file),manifest_path_(p.manifest_file),scheme_name_(p.scheme),schedule_path_(p.schedule_file),event_path_(p.event_log),inspection_(p.inspection_interval),injection_([this]{inject_next();},name()+".logical_SEU",false,gem5::Event::CPU_Tick_Pri-1),clock_([this]{run_clock();},name()+".finite_protection_v18",false,gem5::Event::CPU_Tick_Pri-2),period(p.cycle_ticks){
 fatal_if(period!=500||p.numThreads!=1||!p.speculativeHistUpdate||p.takenOnlyHistory||p.pipeline_mode!="pipeline"||p.pipeline_ii!=1||p.rmw_ii!=1||p.lookup_latency||p.maintenance_cycles||p.check_cycles||p.repair_cycles||(p.role_policy!="LEGACY"&&!early_enabled_)||p.resource_mode!="LEGACY"||p.cost_remove!="NONE","V18 common finite pipeline contract");
 fatal_if((p.scheme!="P0"&&p.scheme!="P_ED"&&p.scheme!="P_ECC"&&p.scheme!="P_TMR")||(inspection_&&!(p.scheme=="P_ED"&&inspection_==64))||(mode_==v18b4::Mode::Direct&&p.scheme!="P0")||mode_==v18b4::Mode::Overwrite,"V18 fixed six-method scope");
}
CpuPipelineV9R2TAGEBase::~CpuPipelineV9R2TAGEBase(){if(clock_.scheduled())deschedule(clock_);if(injection_.scheduled())deschedule(injection_);}
void CpuPipelineV9R2TAGEBase::init(){v18b4::SourceAccess<RoundAccess>::init();configure(mode_,update_L_,query_L_);auto protect=scheme_name_=="P_ED"?(inspection_?v18b4::Protect::Periodic:v18b4::Protect::Parity):scheme_name_=="P_ECC"?v18b4::Protect::Ecc:scheme_name_=="P_TMR"?v18b4::Protect::Tmr:v18b4::Protect::P0;enable_protection(protect,mode_);if(early_enabled_)enable_early();write_manifest();load_faults();}
void CpuPipelineV9R2TAGEBase::startup(){fatal_if(gem5::curTick()!=0,"V15 requires tick0 reset; checkpoint import not implemented");schedule(clock_,period);if(!faults_.empty())schedule(injection_,faults_[0].tick);}
void CpuPipelineV9R2TAGEBase::run_clock(){advance();
 auto*g=protection();auto&ps=g->unit.stats;bool fallback=g->fallback();if(detector_output_&&(ps.detected!=previous_detected_||ps.resets!=previous_resets_||fallback!=previous_fallback_)){detector_output_<<gem5::curTick()<<','<<ps.detected<<','<<ps.corrected<<','<<ps.due<<','<<ps.resets<<','<<g->unit.epoch()<<','<<g->unit.refill_remaining()<<','<<fallback<<'\n';detector_output_.flush();}previous_detected_=ps.detected;previous_resets_=ps.resets;previous_fallback_=fallback;

 // OBSERVATION_BEGIN
 max_lookup_pending=std::max(max_lookup_pending,engine->port.pending());max_source_pending=std::max(max_source_pending,engine->port.source.pending());
 // OBSERVATION_END
 schedule(clock_,gem5::curTick()+period);}
size_t CpuPipelineV9R2TAGEBase::table_bits()const{auto all=sites();size_t n=0;for(auto&s:all)if(s.kind<4)++n;return n;}
bool CpuPipelineV9R2TAGEBase::logical_bit(size_t id)const{auto all=sites();auto n=table_bits();if(id<n){const auto&s=all[id];return(payload(s)>>s.bit)&1;}return model_bit(id-n);}
void CpuPipelineV9R2TAGEBase::corrupt(const std::vector<size_t>&ids){auto n=table_bits();std::set<size_t> unique;std::vector<size_t> table,source;for(auto id:ids){if(id>=n+model_bits()||!unique.insert(id).second)throw std::invalid_argument("invalid v14 atomic logical fault sites");(id<n?table:source).push_back(id<n?id:id-n);}RoundAccess::corrupt(table);corrupt_model(source);}
void CpuPipelineV9R2TAGEBase::write_manifest(){
 if(manifest_path_.empty())return;std::ofstream out(manifest_path_);fatal_if(!out,"V15 manifest output unavailable");auto n=table_bits();
 out<<"{\"scheme\":\""<<scheme_name_<<"\",\"inspection_interval\":"<<inspection_<<",\"protection_check_L\":1,\"encode_L\":1,\"repair_holding_capacity\":1,\"word_widths\":[";auto widths=engine->port.source.selected_widths();for(unsigned w=0;w<23;++w)out<<(w?",":"")<<widths[w];out<<"],\"model\":\"V18_COMMON_FINITE_PROTECTION\",\"scope\":\"predictor tables plus finite source/controller; original allocator/RNG/CPU architectural storage excluded\",\"table_bits\":"<<n<<",\"total_logical_bits\":"<<n+model_bits()<<",\"source_update_L\":"<<(mode_==v18b4::Mode::Direct?1:update_L_)<<",\"source_query_L\":"<<query_L_<<",\"early_unconditional\":"<<(early?"true":"false")<<",\"early_checkpoint_bits\":"<<(early?early->bits():0)<<",\"provider_extra_L\":1,\"II\":1,\"ingress_capacity\":4,\"squash_reserved_commands\":2,\"regions\":[{\"name\":\"original_logical_tables_in_pinned_Site_order\",\"start\":0,\"bits\":"<<n<<'}';
 for(auto&r:model_manifest())out<<",{\"name\":\""<<r.name<<"\",\"start\":"<<n+r.start<<",\"bits\":"<<r.bits<<'}';
 out<<"],\"clock\":\"free-running actual gem5 events from reset; registered vector check then source reduction/provider; actual encoder uses same finite unit\",\"squash_backpressure\":\"when incoming commit/decode squash cannot reserve two ingress cells, hold all O3 stages and existing time buffers; source/cache events continue; conservative global recovery hold; claimed late checkpoints finish before source cancellation/squash\",\"retirement\":\"one actual credit release per cycle; recovery-tagged source ACKs and every claimed late path checkpoint must complete before release\",\"source_interface\":\"1130bit retained register ring with actual pre/post130 taps; not one-port SRAM\",\"exclusions\":[\"provider helper history arrays are combinational operands only\",\"host pointer associations to four token-bound CPU-owned BranchInfo objects; binding token/PC/valid is included; CPU-owned BranchInfo/expected-token/BTB/RAS and original time-buffer/architectural state; no extra squash message copy\",\"absolute software cycle/hold helpers, elaboration constants and diagnostic counters\",\"old native allocator/aging/RNG metadata and combinational SET\"],\"assumptions\":[\"declared source L1/2 and provider1 are model timing, not measured clock\",\"shared23-lane vector check/encode and mirrored metadata stage fit assumed; one decoded repair holding slot; unprotected retention reentry is not codec repair\"],\"not_implemented\":[\"checkpoint restore\",\"decoupled/multithread frontend\"]}\n";
}
void CpuPipelineV9R2TAGEBase::dumpSeu(){
 if(!faults_frozen_){faults_frozen_=true;censor_tick_=gem5::curTick();if(injection_.scheduled())deschedule(injection_);}
 if(summary_path_.empty())return;std::ofstream out(summary_path_);fatal_if(!out,"V15 summary unavailable");auto&s=engine->port.source.stats;
 auto*g=protection();const auto& ps=g->unit.stats;
 out<<"{\"protection_pipeline_drained\":"<<(g->drained()?"true":"false")<<",\"protection_metadata_repairs\":"<<ps.metadata_repairs+g->metadata_repairs<<',';
 out<<"\"scheme\":\""<<scheme_name_<<"\",\"inspection_interval\":"<<inspection_<<",\"applied_events\":"<<applied_events_<<",\"applied_flips\":"<<applied_flips_<<",\"scheduled_events\":"<<faults_.size()<<",\"future_events_censored\":"<<faults_.size()-fault_index_<<",\"censor_tick\":"<<censor_tick_<<",\"faults_frozen\":"<<(faults_frozen_?"true":"false")<<",\"protection_checks\":"<<ps.inspected<<",\"protection_encodes\":"<<ps.encoded<<",\"protection_detected\":"<<ps.detected<<",\"protection_corrected\":"<<ps.corrected<<",\"protection_DUE\":"<<ps.due<<",\"protection_resets\":"<<ps.resets<<",\"protection_epoch\":"<<g->unit.epoch()<<",\"refill_remaining\":"<<g->unit.refill_remaining()<<",\"protection_fallback\":"<<(g->fallback()?"true":"false")<<",\"protection_unit_busy\":"<<ps.unit_busy<<",\"protection_sidecar_reads\":"<<ps.sidecar_reads<<",\"protection_sidecar_writes\":"<<ps.sidecar_writes<<",\"protection_source_repairs\":"<<g->source_repair_publications<<",\"stale_source_ops_suppressed\":"<<g->suppressed_stale_source_ops<<",\"stale_training_suppressed\":"<<stale_training_suppressed<<",\"stale_provider_reissued\":"<<engine->port.stale_protection_responses<<",\"committed_refill_publications\":"<<g->committed_refill_publications<<",\"refill_drains\":"<<refill_drains<<",\"unverified_retention_reentries\":"<<s.unverified_retention_reentries<<',';
 out<<"\"early_enabled\":"<<(early?"true":"false")<<",\"early_claimed\":"<<(early?early->claims:0)<<",\"early_delivered\":"<<(early?early->delivered:0)<<",\"early_pending\":"<<(early?early->pending():0)<<",\"early_metadata_repairs\":"<<(early?early->metadata_repairs:0)<<",\"early_cancel_requests\":"<<(early?early->deferred_cancels:0)<<",\"early_retire_wait_calls\":"<<early_retire_wait_calls<<',';
 // OBSERVATION_BEGIN
 out<<"\"max_lookup_pending\":"<<max_lookup_pending<<",\"max_source_pending\":"<<max_source_pending<<",\"retire_recovery_wait_calls\":"<<retire_recovery_wait_calls<<",\"retire_credit_decode_wait_calls\":"<<retire_credit_decode_wait_calls<<',';
 // OBSERVATION_END
 out<<"\"model\":\"V18_FINITE_PROTECTED_SOURCE\",\"representation\":\""<<(mode_==v18b4::Mode::Recurrent?"recurrent":mode_==v18b4::Mode::Direct?"direct":"overwrite")<<"\",\"tick\":"<<gem5::curTick()<<",\"source_cycles\":"<<engine->port.source.cycle()<<",\"lookups\":"<<lookups<<",\"read_stalls\":"<<read_stalls<<",\"recovery_core_hold_cycles\":"<<recovery_hold_cycles<<",\"ingress_enqueued\":"<<engine->enqueued<<",\"ingress_issued\":"<<engine->issued<<",\"ingress_max_count\":"<<engine->max_count<<",\"recovery_admission_waits\":"<<engine->recovery_waits<<",\"source_issue_waits\":"<<engine->source_issue_waits<<",\"read_ingress_waits\":"<<engine->read_ingress_waits<<",\"source_accepted\":"<<s.accepted<<",\"source_completed\":"<<s.completed<<",\"source_cancelled\":"<<s.cancelled<<",\"source_pending\":"<<engine->port.source.pending()<<",\"source_dependency_stalls\":"<<s.dependency_stalls<<",\"source_ordering_stalls\":"<<s.ordering_stalls<<",\"source_queue_stalls\":"<<s.input_full_stalls<<",\"source_response_stalls\":"<<s.response_stalls<<",\"source_II_stalls\":"<<s.II_stalls<<",\"bulk_undos\":"<<s.bulk_undos<<",\"bulk_bits\":"<<s.bulk_bits<<",\"metadata_repairs\":"<<s.metadata_repairs+engine->metadata_repairs+engine->port.metadata_repairs+(early?early->metadata_repairs:0)<<",\"wrap_completions\":"<<s.wrap_completions<<",\"lookup_accepted\":"<<engine->port.accepted<<",\"lookup_produced\":"<<engine->port.produced<<",\"lookup_consumed\":"<<engine->port.consumed<<",\"lookup_cancelled\":"<<engine->port.cancelled<<",\"lookup_pending\":"<<engine->port.pending()<<",\"predictor_rng_draws\":"<<predictor_rng_draws<<",\"predictor_rng_hash\":"<<predictor_rng_hash<<",\"committed_ops\":"<<committed_ops<<",\"committed_controls\":"<<committed_controls<<",\"committed_identity\":"<<committed_identity<<",\"conserved\":"<<(conserved()?"true":"false")<<",\"applied_faults\":"<<applied_events_<<",\"timing_qualification\":\"MODEL_ONLY\"}\n";
}
CpuPipelineV9R2TAGE::CpuPipelineV9R2TAGE(const gem5::PipelineV9R2TAGEParams&p):TAGE(p),core(*dynamic_cast<CpuPipelineV9R2TAGEBase*>(p.tage)){}
bool CpuPipelineV9R2TAGE::seuFrontendBlocked(gem5::ThreadID tid,bool actual_history_empty){fatal_if(tid,"V15 single thread");return core.frontend_blocked(actual_history_empty);}
bool CpuPipelineV9R2TAGE::seuPredictionRequest(gem5::ThreadID tid,gem5::Addr pc,bool conditional,uint32_t& token){
 if(!token&&core.refill_complete()){++core.read_stalls;return false;}
 fatal_if(tid,"V15 single thread");if(!token){auto t=core.request(pc,conditional);if(!t){++core.read_stalls;return false;}token=t->packed();core.max_lookup_pending=std::max(core.max_lookup_pending,core.engine->port.pending());core.max_source_pending=std::max(core.max_source_pending,core.engine->port.source.pending());}
 if(core.early&&!core.early->ready()){++core.read_stalls;return false;}
 if(!conditional&&core.early_ready(v18b4::Token::unpack(token),pc))return true;
 auto r=core.engine->peek(v18b4::Token::unpack(token));if(!r){++core.read_stalls;return false;}
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

void CpuPipelineV9R2TAGEBase::load_faults(){
 if(!event_path_.empty()){event_output_.open(event_path_);fatal_if(!event_output_,"V18 event log unavailable");event_output_<<"event,tick,token,logical_id,before,after,conditional_gate,stage_phase,stage_lookup,lower_tick\n";detector_output_.open(event_path_+".detector.csv");fatal_if(!detector_output_,"V18 detector log unavailable");detector_output_<<"tick,detected,corrected,due,resets,epoch,refill,fallback\n";}
 if(schedule_path_.empty())return;std::ifstream in(schedule_path_);fatal_if(!in,"V18 schedule unavailable");std::string line;gem5::Tick previous=0;
 while(std::getline(in,line)){
  if(line.empty()||line[0]=='#')continue;std::istringstream input(line);Fault f;std::string sites,extra;fatal_if(!(input>>f.tick>>sites)||bool(input>>extra)||!f.tick||f.tick<previous,"V18 malformed schedule");previous=f.tick;f.lower_tick=f.tick;
  std::stringstream tokens(sites);std::string token;while(std::getline(tokens,token,';')){fatal_if(token.empty(),"V18 empty event site");if(token.rfind("G1R:",0)==0||token.rfind("GU:",0)==0)f.gated=true;f.sites.push_back(token);}fatal_if(f.sites.empty(),"V18 empty atomic event");faults_.push_back(std::move(f));
 }
}
size_t CpuPipelineV9R2TAGEBase::resolve_site(const std::string&token)const{
 if(token.rfind("G1R:",0)==0)return resolve_site(token.substr(4));
 if(token.rfind("GU:",0)==0)return resolve_site(token.substr(3));
 const size_t n=table_bits();if(token[0]=='R'){
  size_t used=0;auto age=std::stoul(token.substr(1),&used);fatal_if(used!=token.size()-1||age>=130,"V18 invalid raw-age alias");return n+engine->port.source.active_raw_site(age);
 }
 if(token[0]=='W'){
  auto colon=token.find(':');fatal_if(colon==std::string::npos,"V18 invalid S* word alias");size_t a=0,b=0;auto word=std::stoul(token.substr(1,colon-1),&a),bit=std::stoul(token.substr(colon+1),&b);auto widths=engine->port.source.selected_widths();fatal_if(a!=colon-1||b!=token.size()-colon-1||word>=23||bit>=widths[word],"V18 invalid canonical word bit");
  if(word==21)return n+engine->port.source.active_raw_site(bit);if(word==22)return n+1130+bit;fatal_if(mode_==v18b4::Mode::Direct,"V18 Direct has no stored fold");size_t id=n+1146;for(unsigned w=0;w<word;++w)id+=widths[w];return id+bit;
 }
 size_t used=0;auto id=std::stoull(token,&used);fatal_if(used!=token.size()||id>=n+model_bits(),"V18 invalid physical logical site");return id;
}
void CpuPipelineV9R2TAGEBase::inject_next(){
 fatal_if(faults_frozen_||fault_index_>=faults_.size()||faults_[fault_index_].tick!=gem5::curTick(),"V18 injection lifecycle");auto&f=faults_[fault_index_];unsigned phase=unsigned(protection()->unit.logical_bit(0))|(unsigned(protection()->unit.logical_bit(1))<<1);bool lookup=protection()->unit.logical_bit(144);
 const bool late=f.sites[0].rfind("GU:",0)==0;const bool publication_pending=protection()->logical_bit(protection()->unit.bits());
 if(f.gated&&(late?(phase!=0||!publication_pending):(phase!=1||lookup))){f.tick=((gem5::curTick()/period)+1)*period+1;schedule(injection_,f.tick);return;}
 std::vector<size_t>ids;std::vector<bool>before;std::set<size_t>unique;
 for(auto&token:f.sites){auto id=resolve_site(token);fatal_if(!unique.insert(id).second,"V18 duplicate physical bit in one atomic event");ids.push_back(id);before.push_back(logical_bit(id));}
 corrupt(ids);
 for(unsigned i=0;i<ids.size();++i){bool after=logical_bit(ids[i]);fatal_if(after==before[i],"V18 XOR event did not change logical bit");if(event_output_)event_output_<<applied_events_<<','<<gem5::curTick()<<','<<f.sites[i]<<','<<ids[i]<<','<<before[i]<<','<<after<<','<<f.gated<<','<<phase<<','<<lookup<<','<<f.lower_tick<<'\n';}
 if(event_output_)event_output_.flush();++applied_events_;applied_flips_+=ids.size();++fault_index_;if(fault_index_<faults_.size()){auto&next=faults_[fault_index_];if(next.gated&&next.tick<=gem5::curTick())next.tick=gem5::curTick()+1;schedule(injection_,next.tick);}
}
}
namespace bp::v15 {
bool RecoveryBridge::ready(gem5::o3::BAC& bac){
 auto*pred=dynamic_cast<bp::CpuPipelineV9R2TAGE*>(bac.bpu->cPred);if(!pred)return true;
 fatal_if(bac.numThreads!=1||bac.decoupledFrontEnd,"V15 requires one thread coupled frontend");
 bool incoming=bac.fromCommit->commitInfo[0].squash||bac.fromDecode->decodeInfo[0].squash;if(!incoming)return true;
 if(!pred->core.prepare_recovery()){++pred->core.recovery_hold_cycles;return false;}return true;
}
}
