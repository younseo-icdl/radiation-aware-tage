#include "tage_harness.hpp"
#include <iostream>
using namespace bp::v13;using namespace bp::v13::test;
static void need(bool v,const char*why){if(!v)throw std::runtime_error(why);}
int main(){try{
 unsigned controls=0,undos=0,packets=0,corrected=0;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  Core dut(mode,L,true);gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.histBufferSize=4096;bp::RoundState ref(p);std::mt19937_64 rng(548);
  for(unsigned round=0;round<80;++round){
   const unsigned spans[]={1,2,3,31,130,511,999,1000};unsigned n=spans[round%8];
   std::vector<bp::Base::BranchInfo*> dd,aa;
   for(unsigned i=0;i<n;++i){bool cond=(rng()%9)!=0;uint64_t pc=0x4000+rng()%4096;auto*d=dut.makeBranchInfo(pc,cond);auto*a=ref.makeBranchInfo(pc,cond);
    auto pd=dut.tagePredict(0,pc,cond,d),pa=ref.tagePredict(0,pc,cond,a);need(pd==pa,"prediction mismatch before batch");compare_prediction(*d,*a,cond);
    dut.updateHistories(0,pc,true,pd,pc+64,{},d);ref.updateHistories(0,pc,true,pa,pc+64,{},a);dd.push_back(d);aa.push_back(a);++controls;
   }
   // Actual BPU outer corrected squash invokes its simple overload nested.
   // No fold read/check/train occurs while the undo packet is accumulated.
   dut.squash_begin();dut.squash_begin();
   for(unsigned i=n;i>1;--i){dut.restoreHistState(0,dd[i-1]);ref.restoreHistState(0,aa[i-1]);++undos;}
   dut.squash_end();
   dut.restoreHistState(0,dd[0]);ref.restoreHistState(0,aa[0]);++undos;
   if(round%2){ // Correction append forces flush BEFORE its new path operand.
    const bool actual=!bool(aa[0]->tagePred);const auto pc=aa[0]->branchPC;
    dut.updateHistories(0,pc,true,actual,pc+128,{},dd[0]);ref.updateHistories(0,pc,true,actual,pc+128,{},aa[0]);++corrected;
   }
   dut.squash_end();++packets;compare(dut,ref);
   if(round%2){dut.restoreHistState(0,dd[0]);ref.restoreHistState(0,aa[0]);++undos;compare(dut,ref);}
   for(auto*x:dd)delete x;for(auto*x:aa)delete x;
   need(dut.service.source_depth()==0&&dut.service.conserved(),"batch lost retention work");
  }
 }
 std::cout<<"{\"status\":\"PASS_NATIVE_TAGE_COALESCED_BPU_CALLBACK_FUNCTIONAL_NOT_GEM5_TIMING\",\"normal_controls\":"<<controls<<",\"primitive_undos\":"<<undos<<",\"outer_squash_packets\":"<<packets<<",\"corrected_appends\":"<<corrected<<",\"max_squash_bits\":1000,\"predictor_input_seed\":548}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
