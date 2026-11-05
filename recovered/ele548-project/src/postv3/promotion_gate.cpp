#include "postv3/role_adapter.hpp"
#include "postv3/role_spec_history.hpp"
#include <iostream>
using namespace bp;
void check(bool value,const char*message){if(!value)throw std::runtime_error(message);}
unsigned eligible(unsigned group,unsigned n){if(n>=130)return 127;if(group==0)return 0;if(group==1)return n>=16?7:0;if(group==2)return n>=44?31:0;return n>=44?31:n>=16?7:0;}
int main(){try{unsigned tests=0;
 for(unsigned group=0;group<4;++group){
  TageAdapter ref;RoundAdapter a(Scheme::ED,RoundPolicy::STAGED,64,false,false,group);
  for(unsigned n=0;n<3000;++n){Branch b;b.pc=0x8000+n%31;b.target=b.pc+8;b.conditional=true;b.taken=n%7<3;check(ref.step(b)==a.step(b),"clean grouping prediction changed");++tests;}
  check(ref.core.bits()==a.core.bits(),"clean grouping state changed");
  gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;RoundState c(params);RoundHistory p(c,Scheme::ED,true,RoundPolicy::STAGED,64,false,false,false,group);RoundProtocol protocol(c,p);p.force_refill();unsigned promotions=0;
  for(unsigned n=1;n<=130;++n){auto r=protocol.capture();auto*bi=c.makeBranchInfo(0x4000+n,true);bool actual=n%3;c.tagePredict(0,0x4000+n,true,bi);protocol.speculative(0,0x4000+n,actual,0,{},bi,r);protocol.commit(0,0x4000+n,actual,0,{},bi,r,1);delete bi;
   if(p.stage_drain_due()){check(protocol.frontend_blocked(false),"promotion ignored live CPU history");check(!protocol.frontend_blocked(true),"safe handoff did not publish");++promotions;}
   check(p.ready_mask()==eligible(group,n),"wrong static promotion grouping");
   for(unsigned w=0;w<21;++w){check(c.phi(w)==c.read_history_word(w),"inactive fold lost coherence");if(p.ready_mask()&(1u<<(w/3)))check(c.fold_length(w)<=n,"bank admitted before enough source history");}
   check(n<16||!p.ready_mask()||n>=16,"path history boundary violated");++tests;
  }
  check(!p.stage_active()&&!p.fallback(),"grouping recovery never completes");check(promotions==(group==0?1:group==3?3:2),"wrong number of safe drains");
  auto snap=a.snapshot();auto before=a.core.bits();a.protection.force_refill();a.restore(snap);check(a.core.bits()==before,"joint grouped snapshot restore failed");
  // Code boundary counterexamples remain present under every grouping.
  auto word=a.protection.specs()[0];a.protection.corrupt({word.sites[0],word.sites[1]});auto detections=a.protection.stats.detected;for(unsigned i=0;i<70;++i){Branch b;b.pc=0x9000+i;b.target=b.pc+8;b.conditional=true;b.taken=i%2;a.step(b);}check(a.protection.stats.detected==detections,"same-word even parity limit changed");
 }
 std::cout<<"PASS "<<tests<<" grouped normal/actual-only/fold/path/safe-drain cases; expected even-parity blind spot retained\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
