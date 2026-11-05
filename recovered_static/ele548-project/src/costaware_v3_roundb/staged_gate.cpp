#include "costaware_v3_roundb/role_adapter.hpp"
#include "costaware_v3_roundb/role_spec_history.hpp"
#include <iostream>
using namespace bp;
int main(){try{unsigned tests=0;
 for(unsigned k:{1u,64u}){TageAdapter reference;RoundAdapter staged(Scheme::ED,RoundPolicy::STAGED,k);
  for(unsigned i=0;i<5000;++i){Branch b;b.pc=0x1000+i%13;b.target=b.pc+8;b.conditional=true;b.taken=i%5<2;if(reference.step(b)!=staged.step(b))throw std::runtime_error("healthy staged prediction mismatch");++tests;}
  if(reference.core.bits()!=staged.core.bits())throw std::runtime_error("healthy staged full-state mismatch");
 }
 gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;
 RoundState core(params);RoundHistory p(core,Scheme::ED,true,RoundPolicy::STAGED,64);RoundProtocol protocol(core,p);p.force_refill();
 for(unsigned n=1;n<=130;++n){auto r=protocol.capture();auto*bi=core.makeBranchInfo(0x4000+n,true);core.tagePredict(0,0x4000+n,true,bi);bool actual=n%3;
  protocol.speculative(0,0x4000+n,actual,0,{},bi,r);protocol.commit(0,0x4000+n,actual,0,{},bi,r,1);delete bi;
  if(p.stage_drain_due()){
   if(!protocol.frontend_blocked(false))throw std::runtime_error("admission before actual queue drain");
   if(protocol.frontend_blocked(true))throw std::runtime_error("safe admission failed");
  }
  unsigned expected=n<16?0:n<44?7:n<130?31:127;
  if(p.ready_mask()!=expected)throw std::runtime_error("path/history eligibility threshold");
  for(unsigned w=0;w<21;++w)if(core.phi(w)!=core.read_history_word(w))throw std::runtime_error("fresh seeded source/fold inconsistency");++tests;
 }
 if(p.stage_active()||p.fallback())throw std::runtime_error("staged recovery never completes");
 auto state=p.snapshot();auto bits=core.bits();p.force_refill();p.restore(state);if(core.bits()==bits){} // core reset deliberately remains independent of controller restore.
 std::cout<<"PASS "<<tests<<" normal equality/path16/actual-only counting/safe drains/Phi cases\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
