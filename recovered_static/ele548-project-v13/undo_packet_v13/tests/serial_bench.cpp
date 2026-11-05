#include "lookup_port.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <deque>
#include <iostream>
using namespace bp::v13;
class ActualProvider:public bp::RoundState {
 public:
 bp::v9::Payload operator()(uint64_t pc,bool cond,const std::array<unsigned,21>&f,unsigned path){
  for(unsigned w=0;w<21;++w){bp::Word v;v.limb[0]=f[w];write_history_word(w,v);}bp::Word v;v.limb[0]=path;write_history_word(22,v);
  auto*b=makeBranchInfo(pc,cond);auto direction=tagePredict(0,pc,cond,b);bp::v9::Payload result;result.capture_response(*b);result.put(25,direction);delete b;return result;
 }
};
int main(){try{
 bp::RoundState ref;auto words=ref.history_words();std::vector<Geometry> g;for(unsigned w=0;w<21;++w)g.push_back({ref.fold_length(w),words[w].width});
 std::cout<<"{\"status\":\"PASS_MATCHED_SOURCE_PROVIDER_LATENCY_AND_SINGLE_PENDING_COMPONENT_NOT_CPU\",\"requests_per_case\":128,\"RNG\":\"NONE_FIXED_INDEPENDENT_PC_LIST\",\"cases\":[";bool first=true;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u})for(bool single:{false,true}){
  LookupPort p(mode,g,L,L);ActualProvider a,b;unsigned issued=0,done=0;uint64_t last=0;std::deque<std::pair<Token,uint64_t>> live;unsigned max_live=0;
  for(unsigned cycle=0;cycle<1000&&done<128;++cycle){
   if(!live.empty()){if(auto r=p.take(live.front().first)){auto expected=b(live.front().second,true,{},0);if(r->pc!=live.front().second||r->payload.data!=expected.data)throw std::runtime_error("matched provider output mismatch");live.pop_front();++done;last=p.source.cycle();}}
   if(issued<128&&(!single||live.empty())){auto pc=0x4000+issued*4;auto t=p.request(pc,true);if(t){live.emplace_back(*t,pc);++issued;max_live=std::max(max_live,unsigned(live.size()));}}
   p.advance([&](auto pc,auto cond,const auto&f,auto path){return a(pc,cond,f,path);});
  }
  if(done!=128||!p.conserved()||last!=(single?128*(L+1):128+L))throw std::runtime_error("matched source/provider timing");
  if(!first)std::cout<<',';first=false;std::cout<<"{\"mode\":"<<unsigned(mode)<<",\"source_L\":"<<L<<",\"provider_extra_L\":1,\"total_ready_L\":"<<L+1<<",\"II\":1,\"single_pending\":"<<(single?"true":"false")<<",\"component_cycles\":"<<last<<",\"maximum_outstanding\":"<<max_live<<",\"physical_bits\":"<<p.bits()<<'}';
 }std::cout<<"],\"CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
