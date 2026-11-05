#pragma once
#include "controller.hpp"
#include "early_receiver.hpp"
#include "source_protection.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/history_access.hpp"
#include <memory>
namespace bp::v18 {
// Shared implementation used by real gem5 core and standalone reference gate.
// Parent's fold/path fields are provider combinational scratch only. There is
// no authoritative second raw/fold source or saved recovery payload there.
template<class Parent>class SourceAccess:public Parent {
 public:
 std::unique_ptr<Controller> engine;
 std::unique_ptr<EarlyReceiver> early;
 std::array<Base::BranchInfo*,4> host_owners{};
 uint64_t fallback_commits=0,stale_training_suppressed=0,stale_source_suppressed=0,refill_drains=0;
 template<class Params>explicit SourceAccess(const Params&p):Parent(p){}
 void configure(Mode mode,unsigned UL,unsigned QL,unsigned id=16,unsigned epoch=16){
  if(engine||this->nHistoryTables!=7||this->pathHistBits!=16||this->takenOnlyHistory)throw std::invalid_argument("finite plain TAGE scope");
  std::vector<Geometry> geometry;auto words=this->history_words();for(unsigned w=0;w<21;++w)geometry.push_back({this->fold_length(w),words[w].width});engine=std::make_unique<Controller>(mode,geometry,UL,QL,id,epoch);
 }
 void enable_early(){if(!engine||early)throw IntegrityError("early configuration");early=std::make_unique<EarlyReceiver>(*engine);}
 void enable_protection(Protect p,Mode mode,unsigned epoch_bits=32){auto&source=engine->port.source;source.attach_guard(std::make_unique<FiniteProtection>(source.selected_widths(),p,mode==Mode::Direct,epoch_bits));}
 FiniteProtection*protection(){return dynamic_cast<FiniteProtection*>(engine->port.source.guard());}
 bool fallback(){auto*g=engine->port.source.guard();return g&&g->fallback();}
 bool refill_complete(){auto*g=protection();return g&&g->unit.fallback()&&g->unit.refill_remaining()==0;}
 bool frontend_blocked(bool actual_cpu_history_empty){
  auto*g=protection();if(!g||!g->unit.fallback()||g->unit.refill_remaining())return false;
  // Finish requests already issued before the refill barrier. A token0 NEW
  // request is blocked separately in the actual CPU admission interface.
  if(engine->port.pending()||(early&&early->pending()))return false;
  if(!actual_cpu_history_empty||!drained()||engine->port.source.source_depth())return true;
  g->acknowledge_refill_and_epoch_drained();++refill_drains;this->tagged_enabled(true);return false;
 }
 v9::Payload provider(uint64_t pc,bool conditional,const std::array<unsigned,21>&fold,unsigned path){
  this->tagged_enabled(!fallback());
  for(unsigned w=0;w<21;++w){Word value;value.limb[0]=fold[w];this->write_history_word(w,value);}Word value;value.limb[0]=path;this->write_history_word(22,value);
  auto* bi=this->makeBranchInfo(pc,conditional);bi->pathHist=path;
  bool prediction=this->tagePredict(0,pc,conditional,bi);v9::Payload result;result.capture_response(*bi);result.put(25,prediction);delete bi;return result;
 }
 void advance(){engine->advance([this](auto pc,auto conditional,const auto&fold,auto path){return provider(pc,conditional,fold,path);});
  if(early)early->advance([this](unsigned slot,unsigned path){if(!host_owners[slot])throw IntegrityError("late CPU owner missing");host_owners[slot]->pathHist=path;host_owners[slot]=nullptr;});
 }
 std::optional<Token> request(uint64_t pc,bool conditional){return early&&!early->ready()?std::optional<Token>{}:engine->request(pc,conditional);}
 bool early_ready(Token token,uint64_t pc){return early&&early->claimable(token,pc);}
 Base::BranchInfo* consume_early(uint64_t pc,Base::BranchInfo* existing=nullptr){
  if(!early)throw IntegrityError("early disabled");auto slot=early->claim(pc);if(!slot||host_owners[*slot])throw IntegrityError("early owner slot unavailable");
  auto*bi=existing?existing:this->makeBranchInfo(pc,false);if(bi->branchPC!=pc||bi->condBranch||!this->tagePredict(0,pc,false,bi))throw IntegrityError("pinned unconditional direction/owner changed");host_owners[*slot]=bi;return bi;
 }
 bool prepare_recovery(){return (!early||early->quiescent())&&engine->prepare_recovery();}
 bool can_retire(unsigned n){return (!early||early->quiescent())&&engine->can_retire(n)&&(!fallback()||engine->committed_ready());}
 bool retire(unsigned n){return can_retire(n)&&engine->retire(n);}
 void cancel(){if(early)early->cancel();else engine->cancel();}
 bool drained(){return (!early||early->quiescent())&&engine->drained();}
 bool conserved(){return engine->conserved()&&(!early||early->conserved());}
 std::vector<Service::Region> model_manifest()const{auto r=engine->manifest();if(early){auto more=early->manifest();for(auto&e:more){e.start+=engine->bits();r.push_back(e);}}return r;}
 size_t model_bits()const{return engine->bits()+(early?early->bits():0);}
 bool model_bit(size_t n)const{if(n>=model_bits())throw std::out_of_range("model bit");return n<engine->bits()?engine->logical_bit(n):early->logical_bit(n-engine->bits());}
 void corrupt_model(const std::vector<size_t>&ids){std::set<size_t> unique;std::vector<size_t>a,b;for(auto id:ids){if(id>=model_bits()||!unique.insert(id).second)throw std::invalid_argument("model atomic sites");(id<engine->bits()?a:b).push_back(id<engine->bits()?id:id-engine->bits());}engine->corrupt(a);if(early)early->corrupt(b);}
 Base::BranchInfo* consume(Token token){auto r=engine->take(token);if(!r)throw IntegrityError("consume before owned source/provider response");auto*bi=this->makeBranchInfo(r->pc,r->conditional);r->payload.restore_response(*bi);bi->pathHist=r->path;return bi;}
 void recordHistState(gem5::ThreadID tid,Base::BranchInfo*)override{if(tid)throw std::invalid_argument("single-thread finite TAGE"); /* captured actual path is already in consumed BI */}
 void updatePathAndGlobalHistory(gem5::ThreadID tid,int,bool taken,gem5::Addr pc,gem5::Addr,Base::BranchInfo*bi)override{
  if(tid)throw std::invalid_argument("single-thread finite TAGE");bi->ghist=taken?1:0;if(fallback()){bi->nGhist=0;++stale_source_suppressed;return;}bi->nGhist=1;engine->append(1,bi->ghist,(pc>>this->instShiftAmt)&1);
 }
 void condBranchUpdate(gem5::ThreadID tid,gem5::Addr pc,bool taken,Base::BranchInfo*bi,int nrand,gem5::Addr target,bool pred,bool pre=false)override{
  if(fallback()){this->fallback_update(pc,taken,bi,nrand);++stale_training_suppressed;return;}Parent::condBranchUpdate(tid,pc,taken,bi,nrand,target,pred,pre);
 }
 void updateHistories(gem5::ThreadID tid,gem5::Addr pc,bool speculative,bool taken,gem5::Addr target,const gem5::StaticInstPtr&inst,Base::BranchInfo*bi)override{
  if(!speculative&&fallback()){engine->committed_history(taken,(pc>>this->instShiftAmt)&1);++fallback_commits;}
  Parent::updateHistories(tid,pc,speculative,taken,target,inst,bi);
 }
 void updateGHist(gem5::ThreadID,uint64_t,uint8_t)override{throw IntegrityError("finite source requires atomic path/global command");}
 void restoreHistState(gem5::ThreadID tid,Base::BranchInfo*bi)override{
  if(tid)throw std::invalid_argument("single-thread finite TAGE");if(!this->speculativeHistUpdate||!bi->modified)return;
  unsigned n=bi->nGhist;engine->restore(n,bi->pathHist);if(n){bi->nGhist=0;bi->modified=false;}
 }
};
}
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
  std::stringstream tokens(sites);std::string token;while(std::getline(tokens,token,';')){fatal_if(token.empty(),"V18 empty event site");if(token.rfind("G1R:",0)==0)f.gated=true;f.sites.push_back(token);}fatal_if(f.sites.empty(),"V18 empty atomic event");faults_.push_back(std::move(f));
 }
}
size_t CpuPipelineV9R2TAGEBase::resolve_site(const std::string&token)const{
 if(token.rfind("G1R:",0)==0)return resolve_site(token.substr(4));
 const size_t n=table_bits();if(token[0]=='R'){
  size_t used=0;auto age=std::stoul(token.substr(1),&used);fatal_if(used!=token.size()-1||age>=130,"V18 invalid raw-age alias");return n+engine->port.source.active_raw_site(age);
 }
 if(token[0]=='W'){
  auto colon=token.find(':');fatal_if(colon==std::string::npos,"V18 invalid S* word alias");size_t a=0,b=0;auto word=std::stoul(token.substr(1,colon-1),&a),bit=std::stoul(token.substr(colon+1),&b);auto widths=engine->port.source.selected_widths();fatal_if(a!=colon-1||b!=token.size()-colon-1||word>=23||bit>=widths[word],"V18 invalid canonical word bit");
  if(word==21)return n+engine->port.source.active_raw_site(bit);if(word==22)return n+1130+bit;fatal_if(mode_==v18::Mode::Direct,"V18 Direct has no stored fold");size_t id=n+1146;for(unsigned w=0;w<word;++w)id+=widths[w];return id+bit;
 }
 size_t used=0;auto id=std::stoull(token,&used);fatal_if(used!=token.size()||id>=n+model_bits(),"V18 invalid physical logical site");return id;
}
void CpuPipelineV9R2TAGEBase::inject_next(){
 fatal_if(faults_frozen_||fault_index_>=faults_.size()||faults_[fault_index_].tick!=gem5::curTick(),"V18 injection lifecycle");auto&f=faults_[fault_index_];unsigned phase=unsigned(protection()->unit.logical_bit(0))|(unsigned(protection()->unit.logical_bit(1))<<1);bool lookup=protection()->unit.logical_bit(144);
 if(f.gated&&(phase!=1||lookup)){f.tick=((gem5::curTick()/period)+1)*period+1;schedule(injection_,f.tick);return;}
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
