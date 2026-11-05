#include "tage_harness.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/replay/e1_trace.hpp"
#include <iostream>
using namespace bp::v13;using namespace bp::v13::test;
static void need(bool v,const char*w){if(!v)throw std::runtime_error(w);}
static gem5::TAGEBaseParams params(bool spec){gem5::TAGEBaseParams p;p.speculativeHistUpdate=spec;p.histBufferSize=4096;return p;}
int main(int argc,char**argv){try{
 need(argc==3,"usage tage_gate TRACE1 TRACE2");uint64_t normal=0,spec=0,undos=0,real_controls=0;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  Core dut(mode,L);bp::RoundState ref(params(false));std::mt19937_64 input(0x12ca11),r1(548),r2(548);
  auto step=[&](const bp::Branch&b){
   auto*a=ref.makeBranchInfo(b.pc,b.conditional);auto*d=dut.makeBranchInfo(b.pc,b.conditional);
   need(ref.tagePredict(0,b.pc,b.conditional,a)==dut.tagePredict(0,b.pc,b.conditional,d),"normal prediction differs");compare_prediction(*a,*d,b.conditional);
   int x=int(r1()%std::numeric_limits<int>::max())&3,y=int(r2()%std::numeric_limits<int>::max())&3;need(x==y,"predictor RNG");
   if(b.conditional){ref.condBranchUpdate(0,b.pc,b.taken,a,x,b.target,a->tagePred);dut.condBranchUpdate(0,b.pc,b.taken,d,y,b.target,d->tagePred);}
   ref.updateHistories(0,b.pc,false,b.taken,b.target,{},a);dut.updateHistories(0,b.pc,false,b.taken,b.target,{},d);dut.commit_record(d);delete a;delete d;
  };
  for(unsigned i=0;i<10000;++i){bp::Branch b{0x4000+input()%4096,0x8000+input()%1024,bool(input()&1),bool(i%9)};step(b);if(i%997==0)compare(dut,ref);++normal;}
  compare(dut,ref);need(r1==r2,"normal RNG state");
  auto snap=dut.snapshot();auto sites=dut.sites();auto signed_site=std::find_if(sites.begin(),sites.end(),[](auto&s){return s.kind==1&&s.bank==1&&s.row==0&&s.bit==2;});
  auto before=dut.payload(*signed_site);dut.inject({signed_site->id});need(dut.payload(*signed_site)==(before^4),"signed bit injection");dut.restore(snap);compare(dut,ref);
  auto raw=std::find_if(sites.begin(),sites.end(),[](auto&s){return s.kind==4&&!s.bank&&s.row==64;});dut.inject({raw->id});need(dut.service.observe_source().raw[64]!=(snap.source.observe_source().raw[64]),"raw source snapshot alias");dut.restore(snap);compare(dut,ref);
  // Previously exposed real design windows: deterministic no-fault gate only.
  for(unsigned wi=0;wi<2;++wi){auto trace=bp::read_e1_trace(argv[wi+1]);need(trace.controls.size()>=3000,"short supplied trace");
   for(unsigned i=0;i<3000;++i){step(trace.controls[i].branch);++real_controls;}compare(dut,ref);}
 }
 // The same native speculative update/correction/commit schedule, unchanged.
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  Core dut(mode,L,true);bp::RoundState ref(params(true));std::mt19937_64 rng(548);
  for(unsigned round=0;round<250;++round){
   std::vector<bp::Base::BranchInfo*> aa,dd;
   for(unsigned i=0;i<32;++i){auto pc=0x1001+((round*17+i*3)%4096);bool cond=(i+round)%7;
    auto*a=ref.makeBranchInfo(pc,cond);auto*d=dut.makeBranchInfo(pc,cond);need(ref.tagePredict(0,pc,cond,a)==dut.tagePredict(0,pc,cond,d),"speculative prediction");compare_prediction(*a,*d,cond);
    ref.updateHistories(0,pc,true,i&1,0,{},a);dut.updateHistories(0,pc,true,i&1,0,{},d);aa.push_back(a);dd.push_back(d);++spec;
   }
   dut.service.cancel_reads();
   for(int i=31;i>0;--i){ref.restoreHistState(0,aa[i]);dut.restoreHistState(0,dd[i]);delete aa[i];delete dd[i];++undos;}
   ref.updateHistories(0,aa[0]->branchPC,true,true,0,{},aa[0]);dut.updateHistories(0,dd[0]->branchPC,true,true,0,{},dd[0]);
   int nr=int(rng()%std::numeric_limits<int>::max())&3;
   if(aa[0]->condBranch){ref.condBranchUpdate(0,aa[0]->branchPC,true,aa[0],nr,0,aa[0]->tagePred);dut.condBranchUpdate(0,dd[0]->branchPC,true,dd[0],nr,0,dd[0]->tagePred);}
   ref.updateHistories(0,aa[0]->branchPC,false,true,0,{},aa[0]);dut.updateHistories(0,dd[0]->branchPC,false,true,0,{},dd[0]);dut.commit_record(dd[0]);
   compare(dut,ref);delete aa[0];delete dd[0];need(dut.service.source_depth()==0,"spec retention leak");
  }
 }
 std::cout<<"{\"status\":\"PASS_PINNED_TAGE_FINITE_SOURCE_FUNCTIONAL_HARNESS_NOT_GEM5_TIMING\",\"normal_synthetic_controls\":"<<normal
 <<",\"normal_real_trace_controls\":"<<real_controls<<",\"speculative_controls\":"<<spec<<",\"explicit_undos\":"<<undos
 <<",\"normal_RNG_equal\":true,\"signed_snapshot\":true,\"protection_controllers_staged\":false,\"gem5_trials\":0}\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
