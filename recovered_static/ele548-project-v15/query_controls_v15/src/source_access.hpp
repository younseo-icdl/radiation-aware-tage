#pragma once
#include "controller.hpp"
#include "early_receiver.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/history_access.hpp"
#include <memory>
namespace bp::v15 {
// Shared implementation used by real gem5 core and standalone reference gate.
// Parent's fold/path fields are provider combinational scratch only. There is
// no authoritative second raw/fold source or saved recovery payload there.
template<class Parent>class SourceAccess:public Parent {
 public:
 std::unique_ptr<Controller> engine;
 std::unique_ptr<EarlyReceiver> early;
 std::array<Base::BranchInfo*,4> host_owners{};
 template<class Params>explicit SourceAccess(const Params&p):Parent(p){}
 void configure(Mode mode,unsigned UL,unsigned QL,unsigned id=16,unsigned epoch=16){
  if(engine||this->nHistoryTables!=7||this->pathHistBits!=16||this->takenOnlyHistory)throw std::invalid_argument("finite plain TAGE scope");
  std::vector<Geometry> geometry;auto words=this->history_words();for(unsigned w=0;w<21;++w)geometry.push_back({this->fold_length(w),words[w].width});engine=std::make_unique<Controller>(mode,geometry,UL,QL,id,epoch);
 }
 void enable_early(){if(!engine||early)throw IntegrityError("early configuration");early=std::make_unique<EarlyReceiver>(*engine);}
 v9::Payload provider(uint64_t pc,bool conditional,const std::array<unsigned,21>&fold,unsigned path){
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
 bool can_retire(unsigned n){return (!early||early->quiescent())&&engine->can_retire(n);}
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
  if(tid)throw std::invalid_argument("single-thread finite TAGE");bi->ghist=taken?1:0;bi->nGhist=1;engine->append(1,bi->ghist,(pc>>this->instShiftAmt)&1);
 }
 void updateGHist(gem5::ThreadID,uint64_t,uint8_t)override{throw IntegrityError("finite source requires atomic path/global command");}
 void restoreHistState(gem5::ThreadID tid,Base::BranchInfo*bi)override{
  if(tid)throw std::invalid_argument("single-thread finite TAGE");if(!this->speculativeHistUpdate||!bi->modified)return;
  unsigned n=bi->nGhist;engine->restore(n,bi->pathHist);if(n){bi->nGhist=0;bi->modified=false;}
 }
};
}
