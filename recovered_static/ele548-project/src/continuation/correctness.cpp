#include "role_adapter.hpp"
#include "role_spec_history.hpp"
#include "predictor/protected_adapter.hpp"
#include <iostream>
using namespace bp;
void require(bool x,const char* m){if(!x)throw std::runtime_error(m);}
Branch branch(std::mt19937_64& r){auto pc=r()%4096;return {pc,r()%8192,bool(r()&1),bool(r()%4)};}
int main(){try{
 std::mt19937_64 r(1831);unsigned cases=0;
 for(auto scheme:{Scheme::P0,Scheme::ED,Scheme::ECC,Scheme::TMR}){
  RoleAdapter c(scheme);ProtectedAdapter old(scheme);for(unsigned i=0;i<20000;++i){auto b=branch(r);require(c.step(b)==old.step(b),"legacy prediction");}require(c.core.bits()==old.predictor.core.bits(),"legacy full bits");require(c.predictor_rng==old.predictor.predictor_rng,"legacy rng");++cases;
 }
 for(auto policy:{RolePolicy::N1,RolePolicy::H1,RolePolicy::REV})for(auto k:{1u,8u,32u,64u}){
  RoleAdapter c(Scheme::ED,policy,k);TageAdapter golden;for(unsigned i=0;i<10000;++i){auto b=branch(r);require(c.step(b)==golden.step(b),"healthy prediction");if(i%997==0)for(unsigned w=0;w<21;++w)require(c.core.phi(w)==c.core.read_history_word(w),"phi recurrence");}
  require(c.core.bits()==golden.core.bits(),"healthy all logical bits");require(c.protection.stats.detected==0,"healthy false alarm");auto s=c.snapshot();auto b=branch(r);c.step(b);auto next=c.snapshot();c.restore(s);c.step(b);require(c.core.bits()==([&]{ContinuationState t;t.load(next.state);return t.bits();})(),"deep-copy replay");++cases;
 }
 // Odd folded payload and parity faults retain incremental syndromes across writes.
 RoleAdapter c(Scheme::ED,RolePolicy::N1,32);for(unsigned i=0;i<1000;++i)c.step(branch(r));auto warm=c.snapshot();
 for(size_t id=65170;id<65370;++id){c.restore(warm);c.protection.corrupt({id});for(unsigned i=0;i<40;++i)c.step(branch(r));require(c.protection.stats.reset_refill==1,"odd fold detector");++cases;}
 for(auto& s:c.protection.additional_sites())if(s.structure=="parity"){c.restore(warm);c.protection.corrupt({s.id});for(unsigned i=0;i<40;++i)c.step(branch(r));require(c.protection.stats.reset_refill==1,"odd parity detector");++cases;}
 c.restore(warm);c.protection.corrupt({65170,65171});for(unsigned i=0;i<40;++i)c.step(branch(r));require(!c.protection.stats.detected,"even parity no guarantee");++cases;
 c.restore(warm);c.protection.corrupt({65170});c.protection.corrupt({65170});for(unsigned i=0;i<40;++i)c.step(branch(r));require(!c.protection.stats.detected,"same bit cancel");++cases;
 auto before=c.core.bits();try{c.protection.corrupt({65170,c.protection.exposed_bits()});throw std::runtime_error("invalid event accepted");}catch(const std::invalid_argument&){}require(before==c.core.bits(),"invalid event atomic rejection");++cases;
 // CPU-like rollback, including a finite buffer rollover, under speculative histories.
 gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;params.histBufferSize=4096;
 for(auto policy:{RolePolicy::N1,RolePolicy::H1}){
  ContinuationState core(params);RoleHistoryController p(core,Scheme::ED,true,policy,32);RoleSpecHistoryProtocol protocol(core,p);
  for(unsigned i=0;i<10000;++i){auto b=branch(r);auto rec=protocol.capture();auto* bi=core.makeBranchInfo(b.pc,b.conditional);core.tagePredict(0,b.pc,b.conditional,bi);protocol.speculative(0,b.pc,b.taken,b.target,{},bi,rec);
   if(i%3==0){protocol.corrected(0,!b.taken,b.target,{},bi,rec);b.taken=!b.taken;}
   if(i%5==0){protocol.discard(0,bi,rec);delete bi;continue;}
   protocol.commit(0,b.pc,b.taken,b.target,{},bi,rec,int(r()&3));delete bi;
  }
  require(!p.stats.detected,"healthy speculative incremental syndrome");for(unsigned w=0;w<21;++w)require(core.phi(w)==core.read_history_word(w),"healthy rollback phi");++cases;
 }
 // Checked rebuild from a radiation-exposed actual-commit source, not a golden copy.
 RoleAdapter h(Scheme::ED,RolePolicy::H1,1);for(unsigned i=0;i<500;++i)h.step(branch(r));auto hs=h.snapshot();
 for(size_t id=65024;id<65370;++id){h.restore(hs);h.protection.corrupt({id});h.protection.progress=1;h.protection.check(true);require(h.protection.rebuild_requests==1,"source/fold SBU rebuild");for(unsigned w=0;w<21;++w)require(h.core.phi(w)==h.core.read_history_word(w),"checked rebuild phi");++cases;}
 h.restore(hs);h.protection.corrupt({65024,65025});h.protection.progress=1;h.protection.check(true);require(h.protection.stats.due==1&&h.protection.refill==130,"source DUE escalate");++cases;
 // Every added stored site XORs separately; not object padding. Preserve snapshots.
 for(auto& s:h.protection.additional_sites()){h.restore(hs);bool b=h.protection.logical_bit(s.id);h.protection.corrupt({s.id});require(h.protection.logical_bit(s.id)!=b,"added stored bit XOR");h.protection.corrupt({s.id});require(h.protection.logical_bit(s.id)==b,"added stored bit cancel");++cases;}
 std::cout<<"PASS "<<cases<<" cases baseline4,incremental,phi,rollback,source/fold/sidecar/control manifest\n";
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
