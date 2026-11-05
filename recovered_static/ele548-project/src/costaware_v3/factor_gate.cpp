#include "costaware_v3/role_adapter.hpp"
#include "continuation/role_adapter.hpp"
#include <iostream>
using namespace bp;
int main(){try{
 unsigned cases=0;
 for(unsigned k:{1u,64u})for(unsigned role:{0u,1u,2u}){
  RoleAdapter old(Scheme::ED,RolePolicy::N1,k);
  CostAdapter inc(Scheme::ED,CostPolicy::N1,k),full(Scheme::ED,CostPolicy::N1,k,true);
  auto words=inc.protection.specs();
  for(unsigned i=0;i<5000;++i){Branch b;b.pc=0x1000+(i%37)*4;b.target=b.pc+16;b.conditional=true;b.taken=(i*11%19)<11;
   if(i==700&&role){auto id=words[role==1?0:21].sites.at(2);old.protection.corrupt({id});inc.protection.corrupt({id});full.protection.corrupt({id});}
   auto a=old.step(b),c=inc.step(b),d=full.step(b);
   if(a!=c||c!=d)throw std::runtime_error("matched maintenance predictions differ");++cases;
  }
  if(old.core.bits()!=inc.core.bits()||inc.core.bits()!=full.core.bits())throw std::runtime_error("matched maintenance state differs");
  auto snapshot=full.snapshot();full.step(Branch{});full.restore(snapshot);
  if(full.core.bits()!=inc.core.bits())throw std::runtime_error("full backend deep restore");
  if(!full.protection.full_reduction_bits||full.protection.fold_delta_xor_inputs)throw std::runtime_error("full reduction instrumentation");
 }
 for(bool reset:{false,true}){
  CostAdapter h(Scheme::ED,CostPolicy::H1,32,false,reset);
  for(unsigned i=0;i<1024;++i){Branch b;b.pc=0x2000+i%7;b.target=b.pc+4;b.conditional=true;b.taken=i%3;if(i==200)h.protection.corrupt({h.protection.specs()[0].sites[0]});h.step(b);}
  if(!h.protection.stats.detected)throw std::runtime_error("H1 detector inactive");
  if(reset?(!h.protection.stats.reset_refill||h.protection.rebuild_requests):(h.protection.stats.reset_refill||!h.protection.rebuild_requests))throw std::runtime_error("controlled recovery selector");
  for(unsigned w=0;w<21;++w)if(h.core.phi(w)!=h.core.read_history_word(w))throw std::runtime_error("post recovery phi mismatch");++cases;
 }
 std::cout<<"PASS "<<cases<<" fixed-stream matched backend/recovery/deep-copy cases\n";
 return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
