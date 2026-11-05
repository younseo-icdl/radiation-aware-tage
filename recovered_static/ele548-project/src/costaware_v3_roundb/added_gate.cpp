#include "costaware_v3_roundb/role_adapter.hpp"
#include "costaware_v3/ready_credits.hpp"
#include <iostream>
using namespace bp;
Branch branch(unsigned i){Branch b;b.pc=0x9000+i%31;b.target=b.pc+4;b.conditional=true;b.taken=i%7<3;return b;}
int main(){try{unsigned cases=0;
 RoundAdapter origin(Scheme::ED,RoundPolicy::STAGED,64);origin.protection.force_refill();for(unsigned i=0;i<50;++i)origin.step(branch(i));auto snap=origin.snapshot();
 for(const auto&s:origin.protection.additional_sites())if(s.structure=="staged_control"||s.structure=="staged_control_check"){
  RoundAdapter test(Scheme::ED,RoundPolicy::STAGED,64);test.restore(snap);test.protection.corrupt({s.id});for(unsigned i=50;i<500;++i)test.step(branch(i));
  if(!test.protection.stats.detected)throw std::runtime_error("stage metadata single error missed");
  if(test.protection.stage_active())throw std::runtime_error("stage metadata single error prevented progress");
  for(unsigned w=0;w<21;++w)if(test.core.phi(w)!=test.core.read_history_word(w))throw std::runtime_error("metadata repair phi");++cases;
 }
 ReadyCredits credits(32);credits.increment(3);credits.increment(3);for(unsigned i=0;i<credits.bits();++i){auto test=credits;test.flip(i);if(test.get(3)!=2)throw std::runtime_error("credit SBU");for(unsigned j=0;j<32;++j)if(j!=3&&test.get(j))throw std::runtime_error("other credit SBU");++cases;}
 // Same-bit correlated two-copy TMR faults can outvote the healthy primary.
 RoundAdapter tmr(Scheme::TMR);auto words=tmr.protection.specs();auto bit=words[0].sites[0];std::vector<size_t>replicas;for(auto&s:tmr.protection.additional_sites())if(s.structure=="replica"&&s.word==0&&s.bit==0)replicas.push_back(s.id);
 auto old=tmr.protection.logical_bit(bit);tmr.protection.corrupt(replicas);tmr.protection.check(true);if(tmr.protection.logical_bit(bit)==old)throw std::runtime_error("correlated TMR counterexample missing");++cases;
 std::cout<<"PASS "<<cases<<" staged added-state/credit sweeps; EXPECTED_COVERAGE_FAILURE two-correlated-TMR-copies\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
