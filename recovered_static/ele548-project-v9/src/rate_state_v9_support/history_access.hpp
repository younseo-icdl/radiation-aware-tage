#pragma once
#include "../predictor/tage_access.hpp"
namespace bp {
class RoundAccess : public TageAccess {
 public:
 uint64_t observation_training_calls=0,observation_allocation_requests=0;
 void condBranchUpdate(gem5::ThreadID tid,gem5::Addr pc,bool taken,Base::BranchInfo*bi,int nrand,gem5::Addr target,bool pred,bool pre=false)override{++observation_training_calls;Base::condBranchUpdate(tid,pc,taken,bi,nrand,target,pred,pre);}
 explicit RoundAccess(const gem5::TAGEBaseParams& p):TageAccess(p){}
 bool raw_bit(unsigned age)const {if(age>maxHist)throw std::out_of_range("raw transition age");return threadHistory[0].globalHist.at(threadHistory[0].ptGhist+age)&1;}
 unsigned fold_length(unsigned word)const {if(word>=21)throw std::out_of_range("fold word");return histLengths[word/3+1];}
 Word phi(unsigned word)const {Word v;auto specs=history_words();auto width=specs.at(word).width;for(unsigned age=0;age<fold_length(word);++age)if(raw_bit(age))v.flip(age%width);return v;}
 void admitted(unsigned mask){for(unsigned i=1;i<=nHistoryTables;++i)noSkip[i]=(mask>>(i-1))&1;}
 protected:
 void handleAllocAndUReset(bool alloc,bool taken,Base::BranchInfo* bi,int nrand) override {
  if(alloc)++observation_allocation_requests;
  bool all=true;for(unsigned i=1;i<=nHistoryTables;++i)all&=noSkip[i];
  if(all){Base::handleAllocAndUReset(alloc,taken,bi,nrand);return;}
  if(alloc){
   uint8_t minimum=1;for(int i=nHistoryTables;i>bi->hitBank;--i)if(noSkip[i])minimum=std::min(minimum,gtable[i][bi->tableIndices[i]].u);
   int Y=nrand&((1ULL<<(nHistoryTables-bi->hitBank-1))-1);int X=bi->hitBank+1;if(Y&1){++X;if(Y&2)++X;}
   while(X<=int(nHistoryTables)&&!noSkip[X])++X;
   if(X<=int(nHistoryTables)){
    if(minimum>0)gtable[X][bi->tableIndices[X]].u=0;
    unsigned allocated=0;for(int i=X;i<=int(nHistoryTables);++i)if(noSkip[i]&&gtable[i][bi->tableIndices[i]].u==0){gtable[i][bi->tableIndices[i]].tag=bi->tableTags[i];gtable[i][bi->tableIndices[i]].ctr=taken?0:-1;if(++allocated==maxNumAlloc)break;}
   }
  }
  // Keep the upstream aging schedule; only invalid-bank allocations are blocked.
  Base::handleAllocAndUReset(false,taken,bi,nrand);
 }

};
}
