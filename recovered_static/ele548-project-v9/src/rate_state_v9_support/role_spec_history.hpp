#pragma once
#include "role_history.hpp"
#include "../protection/spec_history.hpp"
namespace bp {

// CPU schedule policy, shared by real gem5 wrapper and standalone invariant
// tests. Base history/hash/allocation algorithms remain the pinned upstream.
class RoundProtocol {
    RoundAccess& core;
    RoundHistory& protection;
 public:
    uint64_t stale_restores_suppressed=0,stale_training_suppressed=0;
    uint64_t speculative_writes=0,committed_refill_writes=0,drains_completed=0;
    RoundProtocol(RoundAccess& c,RoundHistory& p):core(c),protection(p){
        if(!p.cpu_protocol)throw std::invalid_argument("CPU protection protocol required");}
    EpochRecord capture(){protection.check(true);protection.prediction();return {protection.epoch,protection.fallback()};}
    bool current(const EpochRecord& record)const{return record.epoch==protection.epoch;}
    bool bypass(const EpochRecord& record)const{return !current(record)||record.fallback||protection.fallback();}
    void speculative(gem5::ThreadID tid,uint64_t pc,bool taken,uint64_t target,
                     const gem5::StaticInstPtr& inst,Base::BranchInfo* bi,const EpochRecord& record){
        protection.check();
        if(bypass(record))return;
        protection.begin(RoundTransition::Forward,pc,taken,bi);
        core.Base::updateHistories(tid,pc,true,taken,target,inst,bi);
        protection.finish(false);++speculative_writes;
    }
    void corrected(gem5::ThreadID tid,bool actual,uint64_t target,
                   const gem5::StaticInstPtr& inst,Base::BranchInfo* bi,const EpochRecord& record){
        protection.check();
        if(bypass(record)){++stale_restores_suppressed;return;}
        protection.begin(RoundTransition::Correct,bi->branchPC,actual,bi);
        core.Base::squash(tid,actual,target,inst,bi);
        protection.finish(false);++speculative_writes;
    }
    void discard(gem5::ThreadID tid,Base::BranchInfo* bi,const EpochRecord& record){
        protection.check();
        if(bypass(record)){++stale_restores_suppressed;return;}
        bool changed=bi->modified;
        if(changed)protection.begin(RoundTransition::Undo,bi->branchPC,false,bi);
        core.restoreHistState(tid,bi);
        if(changed)protection.finish(false); // No read re-encode.
    }
    void commit(gem5::ThreadID tid,uint64_t pc,bool actual,uint64_t target,
                const gem5::StaticInstPtr& inst,Base::BranchInfo* bi,const EpochRecord& record,int nrand){
        protection.check();
        protection.commit_source(pc,actual);bool fallback=bypass(record);
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
            protection.begin(RoundTransition::Forward,pc,actual,actual_bi);
            core.Base::updateHistories(tid,pc,true,actual,target,inst,actual_bi);
            core.Base::updateHistories(tid,pc,false,actual,target,inst,actual_bi);
            delete actual_bi;protection.finish(true);++committed_refill_writes;
        }else core.Base::updateHistories(tid,pc,false,actual,target,inst,bi);
    }
    bool frontend_blocked(bool cpu_history_empty){
        if(protection.policy==RoundPolicy::STAGED){protection.validate_stage();if(protection.stage_drain_due()){if(!cpu_history_empty)return true;protection.complete_cpu_drain();++drains_completed;return false;}}
        if(protection.policy==RoundPolicy::H1&&protection.phase>=2){protection.advance_rebuild_step();return protection.phase!=0;}
        if(!protection.fallback()||protection.refill)return false;
        if(!cpu_history_empty)return true;
        protection.complete_cpu_drain();++drains_completed;return protection.phase!=0;
    }
};
}
