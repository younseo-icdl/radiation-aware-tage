#pragma once
#include "tage_adapter.hpp"
#include "../protection/periodic_history.hpp"
namespace bp {
class PeriodicAdapter {
 public:
    TageAdapter predictor;
    PeriodicHistoryController protection;
    explicit PeriodicAdapter(Scheme s,unsigned k=0):predictor(548),protection(predictor.core,s,false,k){}
    struct Snapshot {TageAdapter::Snapshot predictor;PeriodicHistoryController::Snapshot protection;};
    Snapshot snapshot()const{return {predictor.snapshot(),protection.snapshot()};}
    void restore(const Snapshot& s){predictor.restore(s.predictor);protection.restore(s.protection);}
    void load_clean_warmup(const TageAdapter::Snapshot& s){
        predictor.restore(s);protection.refill=0;protection.epoch=0;protection.progress=0;
        protection.stats={};protection.synchronize();predictor.core.tagged_enabled(true);
    }
    bool step(const Branch& b){
        protection.check(true);protection.prediction();
        auto* bi=predictor.core.makeBranchInfo(b.pc,b.conditional);
        bool p=predictor.core.tagePredict(0,b.pc,b.conditional,bi);
        int nrand=int(predictor.predictor_rng()%std::numeric_limits<int>::max())&3;
        if(b.conditional){
            if(protection.fallback())predictor.core.fallback_update(b.pc,b.taken,bi,nrand);
            else predictor.core.condBranchUpdate(0,b.pc,b.taken,bi,nrand,b.target,p);
        }
        protection.check();protection.begin_history_write();
        predictor.core.updateHistories(0,b.pc,false,b.taken,b.target,{},bi);
        protection.after_history_write();delete bi;return p;
    }
};
}
