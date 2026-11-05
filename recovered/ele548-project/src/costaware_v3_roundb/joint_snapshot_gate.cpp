#include "costaware_v3_roundb/role_adapter.hpp"
#include "costaware_v3/finite_fifo.hpp"
#include <iostream>
using namespace bp;
int main(){try{unsigned cases=0;
 for(unsigned horizon:{0u,8u,16u,44u,129u,130u}){
  RoundAdapter a(Scheme::ED,RoundPolicy::STAGED,64);a.protection.force_refill();
  for(unsigned n=0;n<horizon;++n){Branch b;b.pc=0x4000+n%17;b.target=b.pc+8;b.conditional=true;b.taken=n%3;a.step(b);}
  auto snap=a.snapshot();auto expected=a.core.bits();RoundAdapter b(Scheme::ED,RoundPolicy::STAGED,64);b.restore(snap);
  if(a.core.bits()!=b.core.bits()||a.predictor_rng!=b.predictor_rng)throw std::runtime_error("joint core/RNG restore");
  for(size_t id=0;id<a.protection.exposed_bits();++id){if(a.protection.logical_bit(id)!=b.protection.logical_bit(id))throw std::runtime_error("joint logical restore");++cases;}
  a.protection.force_refill();a.protection.corrupt({65170});
  if(b.core.bits()!=expected)throw std::runtime_error("mutation leaked into independent core");
  RoundAdapter c(Scheme::ED,RoundPolicy::STAGED,64);c.restore(snap);
  for(unsigned n=0;n<64;++n){Branch x;x.pc=0x8000+n%11;x.target=x.pc+8;x.conditional=true;x.taken=n%5<2;
   if(b.step(x)!=c.step(x)||b.core.bits()!=c.core.bits())throw std::runtime_error("independent continuation diverged");++cases;}
  a.restore(snap);c.restore(snap);
  if(a.core.bits()!=expected||a.predictor_rng!=snap.rng)throw std::runtime_error("mutated owner core/RNG restore");
  for(size_t id=0;id<a.protection.exposed_bits();++id){if(a.protection.logical_bit(id)!=c.protection.logical_bit(id))throw std::runtime_error("mutated owner restore mismatch");}
 }
 std::cout<<"PASS "<<cases<<" joint staged snapshot/deep-copy/continuation logical-bit cases\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
