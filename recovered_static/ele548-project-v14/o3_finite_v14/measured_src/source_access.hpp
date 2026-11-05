#pragma once
#include "controller.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/history_access.hpp"
#include <memory>
namespace bp::v14 {
// Shared implementation used by real gem5 core and standalone reference gate.
// Parent's fold/path fields are provider combinational scratch only. There is
// no authoritative second raw/fold source or saved recovery payload there.
template<class Parent>class SourceAccess:public Parent {
 public:
 std::unique_ptr<Controller> engine;
 template<class Params>explicit SourceAccess(const Params&p):Parent(p){}
 void configure(Mode mode,unsigned UL,unsigned QL){
  if(engine||this->nHistoryTables!=7||this->pathHistBits!=16||this->takenOnlyHistory)throw std::invalid_argument("finite plain TAGE scope");
  std::vector<Geometry> geometry;auto words=this->history_words();for(unsigned w=0;w<21;++w)geometry.push_back({this->fold_length(w),words[w].width});engine=std::make_unique<Controller>(mode,geometry,UL,QL);
 }
 v9::Payload provider(uint64_t pc,bool conditional,const std::array<unsigned,21>&fold,unsigned path){
  for(unsigned w=0;w<21;++w){Word value;value.limb[0]=fold[w];this->write_history_word(w,value);}Word value;value.limb[0]=path;this->write_history_word(22,value);
  auto* bi=this->makeBranchInfo(pc,conditional);bi->pathHist=path;
  bool prediction=this->tagePredict(0,pc,conditional,bi);v9::Payload result;result.capture_response(*bi);result.put(25,prediction);delete bi;return result;
 }
 void advance(){engine->advance([this](auto pc,auto conditional,const auto&fold,auto path){return provider(pc,conditional,fold,path);});}
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
