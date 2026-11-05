#include "rate_state_v5/representation.hpp"
#include "../rate_state_v5_support/role_adapter.hpp"
#include "../rate_state_v5_support/role_spec_history.hpp"
#include <iostream>
using namespace bp;using namespace bp::v5;
struct SpecState:RepresentationAccess<RoundState>{
 static gem5::TAGEBaseParams params(){gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.histBufferSize=4096;return p;}
 SpecState(const char*m):RepresentationAccess<RoundState>(params(),m,8){prepare_taps();}
};
void require(bool v,const char*s){if(!v)throw std::runtime_error(s);}
int main(){try{
 SpecState a("recurrent"),b("direct");RoundHistory ap(a,Scheme::P0,true),bp(b,Scheme::P0,true);RoundProtocol pa(a,ap),pb(b,bp);
 for(unsigned round=0;round<5000;++round){
  std::vector<Base::BranchInfo*> av,bv;std::vector<EpochRecord> ar,br;
  for(unsigned i=0;i<32;++i){uint64_t pc=0x4000+((round*17+i*3)%1024);bool cond=(i+round)%7;
   ar.push_back(pa.capture());br.push_back(pb.capture());auto*ai=a.makeBranchInfo(pc,cond);auto*bi=b.makeBranchInfo(pc,cond);
   require(a.tagePredict(0,pc,cond,ai)==b.tagePredict(0,pc,cond,bi),"protocol clean prediction");
   if(cond)for(unsigned bank=1;bank<=7;++bank)require(ai->tableIndices[bank]==bi->tableIndices[bank]&&ai->tableTags[bank]==bi->tableTags[bank],"protocol same hash");
   pa.speculative(0,pc,i&1,0,{},ai,ar.back());pb.speculative(0,pc,i&1,0,{},bi,br.back());av.push_back(ai);bv.push_back(bi);
  }
  for(unsigned i=31;i>0;--i){pa.discard(0,av[i],ar[i]);pb.discard(0,bv[i],br[i]);require(a.hashes()==b.hashes(),"adapter discard did not rewind raw journal");delete av[i];delete bv[i];}
  pa.corrected(0,true,0,{},av[0],ar[0]);pb.corrected(0,true,0,{},bv[0],br[0]);require(a.hashes()==b.hashes(),"adapter corrected hash");
  pa.commit(0,av[0]->branchPC,true,0,{},av[0],ar[0],0);pb.commit(0,bv[0]->branchPC,true,0,{},bv[0],br[0],0);
  if(!(round%17))require(a.bits()==b.bits(),"adapter learned state mismatch");delete av[0];delete bv[0];
 }
 std::cout<<"PASS actual RoundProtocol capture/speculate/discard/correct/commit, odd PC, 32 in-flight,5000 rounds with upstream buffer rollovers\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
