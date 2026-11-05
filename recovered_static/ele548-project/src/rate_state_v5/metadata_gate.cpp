#include "rate_state_v5/representation.hpp"
#include "../rate_state_v5_support/role_adapter.hpp"
#include "../rate_state_v5_support/finite_fifo.hpp"
#include <iostream>
using namespace bp;using namespace bp::v5;
void require(bool v,const char*s){if(!v)throw std::runtime_error(s);}
int main(){try{
 std::mt19937_64 r(315548777);
 for(auto scheme:{Scheme::ED,Scheme::ECC}){
  RoundAdapter clean(scheme,RoundPolicy::N1,64);TageAdapter reference;
  for(unsigned n=0;n<10000;++n){Branch br{r()%4096,0,bool(r()&1),true};require(clean.step(br)==reference.step(br),"periodic clean equality");}
  require(clean.core.bits()==reference.core.bits(),"periodic clean training equality");require(!clean.protection.stats.detected,"clean false detection");
 }
 // ECC checks on every RMW must not silently re-encode an unchecked upset.
 for(unsigned k:{1u,8u,64u})for(auto id:{size_t(65024),size_t(65170),size_t(65369)}){
  RoundAdapter clean(Scheme::ECC,RoundPolicy::N1,k),fault(Scheme::ECC,RoundPolicy::N1,k);
  for(unsigned n=0;n<100;++n){Branch br{r()%4096,0,bool(r()&1),true};clean.step(br);fault.step(br);}
  auto before=fault.protection.stats.corrected;fault.protection.corrupt({id});Branch br{0x1234,0,true,true};clean.step(br);fault.step(br);
  require(fault.protection.stats.corrected==before+1,"ECC RMW did not correct latent SBU");
  require(clean.core.bits()==fault.core.bits(),"corrected ECC history/table mismatch");
 }
 Adapter a("direct"),b("direct");for(unsigned n=0;n<1200;++n){Branch br{0x100+4*(n%64),0,bool(n%3),true};a.step(br);b.step(br);}
 b.core.raw_head^=1;bool differed=false;
 for(unsigned n=0;n<150;++n){differed|=a.core.hashes()!=b.core.hashes();Branch br{0x200+4*(n%16),0,bool(n%3),true};a.step(br);b.step(br);}
 require(differed,"head upset unexpectedly invisible");require(a.core.hashes()==b.core.hashes(),"valid head error did not age out under same stream");
 State spec("direct",8,true);auto*bi=spec.makeBranchInfo(0x1235,true);spec.updateHistories(0,0x1235,true,true,0,{},bi);bi->pathHist^=1;spec.restoreHistState(0,bi);
 require(spec.payload(Site{4,1,0,0,16,0})==1,"stale path checkpoint corruption not reintroduced");delete bi;
 bool rejected=false;spec.raw_head=2047;try{spec.hashes();}catch(const std::runtime_error&){rejected=true;}require(rejected,"invalid journal head accepted");
 // Deferred publication really changes the state only when the finite job
 // completes; it is not an atomic functional update followed by charged debt.
 Adapter atomic("direct"),queued("direct");FiniteRmwQueue q(22,64,1,1);
 queued.core.defer_journal=true;queued.core.journal_enqueue=[&](bool undo,unsigned n,uint64_t bits,unsigned path){Word w;w.set(0,undo);for(unsigned j=0;j<2;++j){w.set(1+j,(n>>j)&1);w.set(3+j,(bits>>j)&1);}for(unsigned j=0;j<16;++j)w.set(5+j,(path>>j)&1);w.set(21,true);q.push(w);q.start();};
 for(unsigned n=0;n<1000;++n){Branch br{0x101+4*(n%64),0,bool(n&1),true};auto old_head=queued.core.raw_head;
  require(atomic.step(br)==queued.step(br),"deferred clean prediction equality");require(queued.core.raw_head==old_head,"journal published at enqueue");
  auto job=q.tick();require(bool(job),"L1 completion missing");unsigned count=0,path=0;uint64_t bits=0;for(unsigned j=0;j<2;++j){count|=unsigned(job->bit(1+j))<<j;bits|=uint64_t(job->bit(3+j))<<j;}for(unsigned j=0;j<16;++j)path|=unsigned(job->bit(5+j))<<j;queued.core.apply_journal(job->bit(0),count,bits,path);
  require(atomic.core.hashes()==queued.core.hashes()&&atomic.core.direct_path==queued.core.direct_path,"service publication mismatch");require(q.conserved(),"journal queue conservation");
 }
 std::cout<<"PASS periodic parity/ECC clean table equality; matched prediction cadence with mandatory ECC RMW decode; SBU recovery; valid head upset aging; stale checkpoint reintroduction; invalid pointer is protocol failure\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
