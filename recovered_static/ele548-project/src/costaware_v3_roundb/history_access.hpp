#pragma once
#include "../predictor/tage_access.hpp"
namespace bp {
class RoundAccess : public TageAccess {
 public:
 explicit RoundAccess(const gem5::TAGEBaseParams& p):TageAccess(p){}
 bool raw_bit(unsigned age)const {if(age>maxHist)throw std::out_of_range("raw transition age");return threadHistory[0].globalHist.at(threadHistory[0].ptGhist+age)&1;}
 unsigned fold_length(unsigned word)const {if(word>=21)throw std::out_of_range("fold word");return histLengths[word/3+1];}
 Word phi(unsigned word)const {Word v;auto specs=history_words();auto width=specs.at(word).width;for(unsigned age=0;age<fold_length(word);++age)if(raw_bit(age))v.flip(age%width);return v;}
 void admitted(unsigned mask){for(unsigned i=1;i<=nHistoryTables;++i)noSkip[i]=(mask>>(i-1))&1;}
 protected:
 void handleAllocAndUReset(bool alloc,bool taken,Base::BranchInfo* bi,int nrand) override {
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
 auto*info=static_cast<CpuInfo*>(history);return core.can_retire(info->handle,needs_commit_job(info));
}
void CpuRoundBV3TAGE::seuReserveRetire(gem5::ThreadID tid,void*history){if(core.endpoint()&&history){auto*info=static_cast<CpuInfo*>(history);core.reserve_commit(needs_commit_job(info),core.decouple_shadow);}}
void CpuRoundBV3TAGE::cleanup_cancelled(){
 for(unsigned id=0;id<core.metadata_pool.size();++id){auto*info=static_cast<CpuInfo*>(core.metadata_pool[id]);if(info&&info->released){core.metadata_pool[id]=nullptr;delete info;}}
}
void CpuRoundBV3TAGE::complete_job(const Word&w){
 auto handle=tok(w,0,10),kind=tok(w,10,3);if(!w.bit(49)||kind>3||handle>=core.metadata_pool.size()||!core.metadata_pool[handle])throw QueueIntegrityError("invalid history operand reference");
 auto*info=static_cast<CpuInfo*>(core.metadata_pool[handle]);EpochRecord r{tok(w,14,32),w.bit(46)};bool actual=w.bit(13);auto before=core.protection->stats.detected;
 if(kind==0)core.protocol->speculative(0,info->tageBranchInfo->branchPC,actual,0,{},info->tageBranchInfo,r);
 else if(kind==1)core.protocol->corrected(0,actual,0,{},info->tageBranchInfo,r);
 else if(kind==2)core.protocol->discard(0,info->tageBranchInfo,r);
 else core.protocol->commit(0,info->tageBranchInfo->branchPC,actual,0,{},info->tageBranchInfo,r,tok(w,47,2));
 core.account_repairs(before,kind==0?2:kind==1?4:kind==2?5:3);
 core.credits.decrement(handle);
 if(core.resource_output&&(core.hot_queue.completed<=256||!(core.hot_queue.completed%4096)))core.resource_output<<gem5::curTick()<<",PUBLISH,HOT_SOURCE,"<<core.protection->epoch<<','<<core.hot_queue.count()<<','<<0<<','<<1<<",FUNCTIONAL_EFFECT_ONLY_AT_SERVICE_COMPLETION\n";
 if(info->released&&!core.credits.get(handle)){core.release_metadata(handle);delete info;}
}

void CpuRoundBV3TAGE::branchPlaceholder(gem5::ThreadID,gem5::Addr,bool,void*&){fatal("Decoupled frontend unsupported in fixed CPU research scope");}
}
