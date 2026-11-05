#pragma once
#include "periodic_history.hpp"
#include "spec_history.hpp"
namespace bp {

// CPU schedule policy, shared by real gem5 wrapper and standalone invariant
// tests. Base history/hash/allocation algorithms remain the pinned upstream.
class PeriodicSpecHistoryProtocol {
    TageAccess& core;
    PeriodicHistoryController& protection;
 public:
    uint64_t stale_restores_suppressed=0,stale_training_suppressed=0;
    uint64_t speculative_writes=0,committed_refill_writes=0,drains_completed=0;
    PeriodicSpecHistoryProtocol(TageAccess& c,PeriodicHistoryController& p):core(c),protection(p){
        if(!p.cpu_protocol)throw std::invalid_argument("CPU protection protocol required");}
    EpochRecord capture(){protection.check(true);protection.prediction();return {protection.epoch,protection.fallback()};}
    bool current(const EpochRecord& record)const{return record.epoch==protection.epoch;}
    bool bypass(const EpochRecord& record)const{return !current(record)||record.fallback||protection.fallback();}
    void speculative(gem5::ThreadID tid,uint64_t pc,bool taken,uint64_t target,
                     const gem5::StaticInstPtr& inst,Base::BranchInfo* bi,const EpochRecord& record){
        protection.check();
        if(bypass(record))return;
        protection.begin_history_write();
        core.Base::updateHistories(tid,pc,true,taken,target,inst,bi);
        protection.synchronize();++speculative_writes;
    }
    void corrected(gem5::ThreadID tid,bool actual,uint64_t target,
                   const gem5::StaticInstPtr& inst,Base::BranchInfo* bi,const EpochRecord& record){
        protection.check();
        if(bypass(record)){++stale_restores_suppressed;return;}
        protection.begin_history_write();
        core.Base::squash(tid,actual,target,inst,bi);
        protection.synchronize();++speculative_writes;
    }
    void discard(gem5::ThreadID tid,Base::BranchInfo* bi,const EpochRecord& record){
        protection.check();
        if(bypass(record)){++stale_restores_suppressed;return;}
        bool changed=bi->modified;
        if(changed)protection.begin_history_write();
        core.Base::restoreHistState(tid,bi);
        if(changed)protection.synchronize(); // Never re-encode a no-op/read.
    }
    void commit(gem5::ThreadID tid,uint64_t pc,bool actual,uint64_t target,
                const gem5::StaticInstPtr& inst,Base::BranchInfo* bi,const EpochRecord& record,int nrand){
        protection.check();bool fallback=bypass(record);
        if(bi->condBranch){
            core.updateStats(actual,bi);
            if(fallback){core.fallback_update(pc,actual,bi,nrand);++stale_training_suppressed;}
            else core.condBranchUpdate(tid,pc,actual,bi,nrand,target,bi->tagePred);
        }
        if(fallback){
            // Actual committed order only while history is invalid. The
            // temporary fresh BI calls the upstream speculative history path
            // exactly once; it is not inserted into the CPU rollback queue.
            auto* actual_bi=core.makeBranchInfo(pc,bi->condBranch);
            protection.begin_history_write();
            core.Base::updateHistories(tid,pc,true,actual,target,inst,actual_bi);
            core.Base::updateHistories(tid,pc,false,actual,target,inst,actual_bi);
            delete actual_bi;protection.after_history_write();++committed_refill_writes;
        }else core.Base::updateHistories(tid,pc,false,actual,target,inst,bi);
    }
    bool frontend_blocked(bool cpu_history_empty){
        if(!protection.fallback()||protection.refill)return false;
        if(!cpu_history_empty)return true;
        protection.complete_cpu_drain();++drains_completed;return false;
    }
};
}
