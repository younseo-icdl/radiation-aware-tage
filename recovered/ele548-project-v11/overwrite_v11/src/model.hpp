#pragma once
#include "rate_state_v9/representation.hpp"
#include "rate_state_v9_support/state.hpp"
#include "rate_state_v9_support/role_history.hpp"
#include "overwrite.hpp"
#include <type_traits>

namespace bp::v11 {
using State=OverwriteAccess<bp::RoundState>;
template<class Core> class ReferenceAdapter {
 public:
  Core core;
  std::mt19937_64 rng{548};
  bp::RoundHistory protection;
  explicit ReferenceAdapter(bp::Scheme scheme=bp::Scheme::P0,
      bp::RoundPolicy policy=bp::RoundPolicy::LEGACY,unsigned interval=0):
    core(),protection(core,scheme,false,policy,interval) {}
  template<class Observer> bool step(const bp::Branch& b,Observer observe) {
    protection.check(true);protection.prediction();
    if constexpr(std::is_same_v<Core,State>) core.observe_lookup(b.conditional);
    auto* bi=core.makeBranchInfo(b.pc,b.conditional);
    bool pred=core.tagePredict(0,b.pc,b.conditional,bi);
    observe(*bi);
    int n=int(rng()%std::numeric_limits<int>::max())&3;
    if(b.conditional) {
      if(protection.fallback())core.fallback_update(b.pc,b.taken,bi,n);
      else core.condBranchUpdate(0,b.pc,b.taken,bi,n,b.target,pred);
    }
    protection.check();protection.begin(bp::RoundTransition::Forward,b.pc,b.taken,bi);
    core.updateHistories(0,b.pc,false,b.taken,b.target,{},bi);
    protection.finish(true);protection.commit_source(b.pc,b.taken);
    delete bi;return pred;
  }
  bool step(const bp::Branch& b) {
    return step(b,[](const bp::Base::BranchInfo&){});
  }
};
using OverwriteAdapter=ReferenceAdapter<State>;
using BaselineAdapter=ReferenceAdapter<bp::RoundState>;
} // namespace bp::v11
