#include "role_adapter.hpp"
#include "role_spec_history.hpp"
#include <iostream>
using namespace bp;
void require(bool b,const char*m){if(!b)throw std::runtime_error(m);}
int main(){try{
 unsigned cases=0;
 // New legacy adapter must preserve the old faultful decoder/action behavior.
 for(auto scheme:{Scheme::P0,Scheme::ED,Scheme::ECC,Scheme::TMR}){
  RoleAdapter a(scheme);ProtectedAdapter b(scheme);std::mt19937_64 r(1126);for(unsigned i=0;i<20000;++i){
   if(i%907==0){std::vector<size_t> ids{size_t(r()%a.protection.exposed_bits())};a.protection.corrupt(ids);b.protection.corrupt(ids);}
   Branch x{r()%4096,r()%8192,bool(r()&1),bool(r()%4)};require(a.step(x)==b.step(x),"faultful baseline prediction");
   if(i%500==0)require(a.core.bits()==b.predictor.core.bits(),"faultful baseline state");
  }require(a.predictor_rng==b.predictor.predictor_rng,"faultful baseline rng");++cases;
 }
 gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;params.histBufferSize=4096;
 ContinuationState c(params);RoleHistoryController p(c,Scheme::ED,true,RolePolicy::H1,1);RoleSpecHistoryProtocol protocol(c,p);
 for(unsigned i=0;i<400;++i){auto*bi=c.makeBranchInfo(i,true);auto record=protocol.capture();c.tagePredict(0,i,true,bi);bool taken=(i%7)<3;protocol.speculative(0,i,taken,0,{},bi,record);protocol.commit(0,i,taken,0,{},bi,record,0);delete bi;}
 auto state=c.save();auto saved=p.snapshot();
 for(const auto&s:p.additional_sites()){
  if(s.structure!="committed_source"&&s.structure!="committed_source_check"&&s.structure!="rebuild_accumulator"&&s.structure!="rebuild_accumulator_parity"&&s.structure!="rebuild_scan"&&s.structure!="rebuild_publish"&&s.structure!="rebuild_phase"&&s.structure!="rebuild_retries")continue;
  c.load(state);p.restore(saved);p.corrupt({65170});p.progress=1;p.check(true);require(p.phase==1,"rebuild waits for drain");require(protocol.frontend_blocked(false),"in-flight drain blocked");p.complete_cpu_drain();p.advance_rebuild_step();p.advance_rebuild_step();p.corrupt({s.id});
  unsigned steps=0;while(p.phase&&steps<400){p.advance_rebuild_step();++steps;}require(steps<400,"finite control-FI repair liveness");
  if(s.structure=="committed_source"||s.structure=="committed_source_check"||s.structure=="rebuild_accumulator"||s.structure=="rebuild_accumulator_parity"){
   require(!p.refill,"single protected shadow/scratch fault does not DUE");for(unsigned w=0;w<21;++w)require(c.phi(w)==c.read_history_word(w),"protected scratch/source restart rebuild");
  }++cases;
 }
 // A valid SECDED miscorrection on3payload errors is kept as an expected coverage failure.
 Word zero,wrong;wrong.flip(0);wrong.flip(1);wrong.flip(2);WordSecded codec(130);auto decoded=codec.decode(wrong,codec.encode(zero));
 require(decoded.corrected&&!decoded.due&&decoded.payload!=zero&&codec.encode(decoded.payload)==decoded.check,"SECDED3+ self-consistent wrong source example");++cases;
 std::cout<<"PASS "<<cases<<" additional cases: faultful baseline equality, mid-rebuild protected source/scratch/control stress; EXPECTED_COVERAGE_FAILURE SECDED3plus\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
