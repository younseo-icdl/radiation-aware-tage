#include "rate_state_v5/representation.hpp"
#include <iostream>
using namespace bp;using namespace bp::v5;
void check(bool x,const char*s){if(!x)throw std::runtime_error(s);}
int main(){try{
 Adapter rec,dir("direct");std::mt19937_64 gen(315548);
 for(unsigned i=0;i<100000;++i){
  Branch b{0x4000+(gen()%1024),0x6000,bool(gen()&1),bool(i%9)};
  std::vector<int> x,y;unsigned hp=0,hq=0,pp=0,pq=0;
  auto p=rec.step(b,[&](const Base::BranchInfo&bi){if(!b.conditional)return;hp=bi.hitBank;pp=bi.provider;for(unsigned j=1;j<=7;++j){x.push_back(bi.tableIndices[j]);x.push_back(bi.tableTags[j]);}});
  auto q=dir.step(b,[&](const Base::BranchInfo&bi){if(!b.conditional)return;hq=bi.hitBank;pq=bi.provider;for(unsigned j=1;j<=7;++j){y.push_back(bi.tableIndices[j]);y.push_back(bi.tableTags[j]);}});
  check(p==q&&x==y&&hp==hq&&pp==pq,"normal read/provider equality");
  if(!(i%997)){check(rec.core.equal(dir.core)&&rec.rng==dir.rng,"table/training/RNG equality");auto s=dir.core.save();State copy("direct");copy.load(s);check(copy.equal(dir.core),"deep snapshot");copy.corrupt({copy.sites().back().id});check(!copy.equal(dir.core),"snapshot alias");}
 }
 // Speculation and inverse rollback with multiple outstanding records.
 State a("recurrent",8,true),b("direct",8,true);std::vector<Base::BranchInfo*>aa,bb;
 for(unsigned i=0;i<512;++i){
  auto*ai=a.makeBranchInfo(0x100+i,true);auto*bi=b.makeBranchInfo(0x100+i,true);
  check(a.tagePredict(0,ai->branchPC,true,ai)==b.tagePredict(0,bi->branchPC,true,bi),"spec lookup");
  a.updateHistories(0,ai->branchPC,true,i&1,0,{},ai);b.updateHistories(0,bi->branchPC,true,i&1,0,{},bi);aa.push_back(ai);bb.push_back(bi);
 }
 for(int i=511;i>=0;--i){a.restoreHistState(0,aa[i]);b.restoreHistState(0,bb[i]);check(a.equal(b)&&a.hashes()==b.hashes(),"inverse rollback equality");delete aa[i];delete bb[i];}
 // Independent derived-state upset has no input into direct lookup.
 Adapter x("direct"),y("direct");auto sites=x.core.sites();for(auto&s:sites)if(s.kind==5){y.core.corrupt({s.id});break;}
 for(unsigned i=0;i<1000;++i){Branch br{0x1234+4*(i%16),0,bool(i&1),true};check(x.step(br)==y.step(br),"helper fold influenced direct function");}
 // Source bit eviction is bounded only under the same fixed stream, no rollback.
 for(unsigned age:{0u,1u,64u,129u}){
  Adapter c("direct"),d("direct");auto ss=c.core.sites();for(auto&s:ss)if(s.kind==4&&s.bank==0&&s.row==age)d.core.corrupt({s.id});
  for(unsigned i=0;i<131;++i){Branch br{0x4000+4*(i%8),0,bool(i&1),true};c.step(br);d.step(br);}
  check(c.core.hashes()==d.core.hashes(),"raw eviction failed to restore direct hashes");
 }
 for(auto mode:{"geometric","stratum","short32"}){Adapter p(mode);for(unsigned i=0;i<1000;++i)p.step({0x5000+4*(i%16),0,bool(i&1),true});}
 std::cout<<"PASS 100000 same-hash index/tag/provider/prediction/training/RNG; deep snapshot; 512 in-flight inverse rollback; helper isolation; source-age eviction; sparse/short smoke\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;} }
