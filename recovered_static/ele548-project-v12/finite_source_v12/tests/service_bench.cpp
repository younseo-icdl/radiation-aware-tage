#include "service.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <fstream>
#include <iostream>
#include <map>
using namespace bp::v12;
static void need(bool v,const char*w){if(!v)throw std::runtime_error(w);}
static std::vector<Geometry> geometry(){bp::RoundState x;auto words=x.history_words();std::vector<Geometry> g;for(unsigned w=0;w<21;++w)g.push_back({x.fold_length(w),words[w].width});return g;}
struct Expected {Kind kind;std::array<unsigned,21> folds{};unsigned path=0;};
int main(int argc,char**argv){try{
 need(argc==2||argc==3&&std::string(argv[2])=="--cross","usage service_bench CSV [--cross]");const bool cross=argc==3;std::ofstream out(argv[1]);need(bool(out),"CSV unavailable");
 out<<"mode,update_L,lookup_L,II,ports,pattern,logical_operations,model_cycles,accepted,completed,update_finalizations,query_finalizations,recurrent_forwards,input_full_stalls,ordering_stalls,dependency_stalls,response_stalls,physical_source_component_bits\n";
 auto g=geometry();unsigned cases=0;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned UL:{1u,2u})for(unsigned QL:{1u,2u})for(auto ports:{Ports::SharedOne,Ports::SplitTwo})for(unsigned pattern=0;pattern<3;++pattern){
  if((UL!=QL)!=cross||cross&&mode==Mode::Direct)continue;
  constexpr unsigned N=128;const unsigned total=pattern==2?2*N:N;
  Service s(mode,g,UL,QL,1,16,16,ports);bp::RoundState ref;
  std::map<uint32_t,Expected> pending;unsigned issued=0,done=0,retired=0,acks=0;
  for(unsigned wall=0;wall<10000&&done<total;++wall){
   for(unsigned port=0;port<2;++port)if(auto r=s.take()){
    auto it=pending.find(r->token.packed());need(it!=pending.end(),"response id unknown");need(it->second.kind==r->kind,"response type");
    if(r->kind==Kind::Read)need(r->folds==it->second.folds&&r->path==it->second.path,"mixed version / stage result differs from pinned source");
    else ++acks;
    pending.erase(it);++done;
   }
   if(retired<acks&&s.retire(1))++retired;
   if(done==total)break;
   for(unsigned port=0;port<2&&issued<total;++port){
    const Kind kind=pattern==0||pattern==2&&issued%2==0?Kind::Read:Kind::Append;
    unsigned source_index=pattern==2?issued/2:issued,bit=(source_index*13+7)&1;
    auto token=s.accept(kind,kind==Kind::Append?1:0,kind==Kind::Append?bit:0,kind==Kind::Append?bit:0);if(!token)break;
    Expected expected{kind};
    if(kind==Kind::Read){for(unsigned w=0;w<21;++w)expected.folds[w]=ref.read_history_word(w).limb[0];expected.path=ref.read_history_word(22).limb[0];}
    else{ref.updateGHist(0,bit,1);bp::Word path;path.limb[0]=((ref.read_history_word(22).limb[0]<<1)|bit)&65535;ref.write_history_word(22,path);}
    need(pending.emplace(token->packed(),expected).second,"duplicate live token");++issued;
   }
   s.tick();need(s.conserved(),"component conservation");
  }
  need(done==total&&pending.empty()&&s.drained()&&s.conserved(),"component benchmark did not drain");
  auto image=s.observe_source();for(unsigned age=0;age<130;++age)need(image.raw[age]==ref.raw_bit(age),"final source differs");
  const char* modes[]={"RECURRENT","DIRECT","OVERWRITE"};const char* patterns[]={"READ_ONLY_INDEPENDENT","APPEND_BURST","MATCHED_VERSION_MIXED"};
  out<<modes[unsigned(mode)]<<','<<UL<<','<<QL<<",1,"<<(ports==Ports::SplitTwo?"SPLIT_2":"SHARED_1")<<','<<patterns[pattern]<<','<<total<<','<<s.cycle()<<','<<s.stats.accepted<<','<<s.stats.completed
     <<','<<s.stats.update_reductions<<','<<s.stats.lookup_reductions<<','<<s.stats.recurrent_low_forwards<<','<<s.stats.input_full_stalls<<','<<s.stats.ordering_stalls<<','<<s.stats.dependency_stalls<<','<<s.stats.response_stalls<<','<<s.bits()<<'\n';++cases;
 }
 out.close();need(bool(out),"CSV write");std::cout<<"{\"status\":\"PASS_COMPONENT_SERVICE_CASES_NOT_CPU_PERFORMANCE\",\"cases\":"<<cases<<",\"N\":128,\"source_rng\":\"NONE_FIXED_COMMAND_STREAM\",\"CPU_trials\":0}\n";return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
