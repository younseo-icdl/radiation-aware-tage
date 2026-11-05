#pragma once
#include "state.hpp"
#include "role_history.hpp"
namespace bp {
class RoleAdapter {
 public:
 ContinuationState core;std::mt19937_64 predictor_rng{548};RoleHistoryController protection;
 RoleAdapter(Scheme s,RolePolicy p=RolePolicy::LEGACY,unsigned k=0):core(),protection(core,s,false,p,k){}
 struct Snapshot {ContinuationState::Snapshot state;std::mt19937_64 rng;RoleHistoryController::Snapshot protection;};
 Snapshot snapshot()const{return {core.save(),predictor_rng,protection.snapshot()};}
 void restore(const Snapshot& s){core.load(s.state);predictor_rng=s.rng;protection.restore(s.protection);}
 void warm(const TageAdapter::Snapshot& s){core.load(s.state);predictor_rng=s.rng;protection.refill=protection.progress=0;protection.epoch=0;protection.recovery_active=false;protection.synchronize();core.tagged_enabled(true);}
 bool step(const Branch& b){
  protection.check(true);protection.prediction();auto* bi=core.makeBranchInfo(b.pc,b.conditional);bool p=core.tagePredict(0,b.pc,b.conditional,bi);
  int n=int(predictor_rng()%std::numeric_limits<int>::max())&3;
  if(b.conditional){if(protection.fallback())core.fallback_update(b.pc,b.taken,bi,n);else core.condBranchUpdate(0,b.pc,b.taken,bi,n,b.target,p);}
  protection.check();protection.begin(Transition::Forward,b.pc,b.taken,bi);core.updateHistories(0,b.pc,false,b.taken,b.target,{},bi);protection.finish(true);protection.commit_source(b.pc,b.taken);delete bi;return p;
 }
};
}
