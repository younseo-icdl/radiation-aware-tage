#include "lookup_port.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <deque>
#include <iostream>
#include <random>
using namespace bp::v13;
static void need(bool v,const char*why){if(!v)throw std::runtime_error(why);}
static std::vector<Geometry> geometry(){bp::RoundState s;auto words=s.history_words();std::vector<Geometry> g;for(unsigned w=0;w<21;++w)g.push_back({s.fold_length(w),words[w].width});return g;}
class Provider:public bp::RoundState {
 public:
 static gem5::TAGEBaseParams params(){gem5::TAGEBaseParams p;p.speculativeHistUpdate=false;return p;}
 Provider():bp::RoundState(params()){}
 void train(uint64_t pc,bool taken,const bp::v9::Payload&payload,int draw,uint64_t target){auto*b=makeBranchInfo(pc,true);payload.restore_response(*b);condBranchUpdate(0,pc,taken,b,draw,target,b->tagePred);delete b;}
 bp::v9::Payload run(uint64_t pc,bool cond,const std::array<unsigned,21>&fold,unsigned path){
  // Combinational operands from actual fold/path latch. These helper locations
  // are not a retained recovery image or second physical predictor source.
  for(unsigned w=0;w<21;++w){bp::Word v;v.limb[0]=fold[w];write_history_word(w,v);}bp::Word p;p.limb[0]=path;write_history_word(22,p);
  auto*b=makeBranchInfo(pc,cond);auto predicted=tagePredict(0,pc,cond,b);bp::v9::Payload out;out.capture_response(*b);out.put(25,predicted);delete b;return out;
 }
};
static size_t start(const LookupPort&p,const std::string&name){for(auto&r:p.manifest())if(r.name==name)return r.start;throw std::runtime_error("region missing");}
int main(){try{
 auto g=geometry();unsigned normal=0,metadata=0,stale=0;std::vector<unsigned> cycle_totals;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  LookupPort p(mode,g,L,L);Provider actual,reference;uint64_t calls=0;auto provider=[&](auto pc,auto cond,const auto&fold,auto path){++calls;return actual.run(pc,cond,fold,path);};
  std::deque<std::pair<Token,uint64_t>> live;unsigned issued=0,done=0;uint64_t last=0;bool contiguous=true;
  for(unsigned cycle=0;cycle<500&&done<128;++cycle){
   if(!live.empty()){auto r=p.take(live.front().first);if(r){need(r->pc==live.front().second&&r->conditional,"PC/type changed");need(p.source.cycle()==done+L+1,"unexpected real lookup latency/throughput");
     auto expected=reference.run(r->pc,true,{},0);need(r->payload.data==expected.data,"actual pinned index/provider differs");if(done&&p.source.cycle()!=last+1)contiguous=false;last=p.source.cycle();live.pop_front();++done;++normal;}}
   if(issued<128){auto pc=0x4000+issued*4;auto t=p.request(pc,true);if(t){live.emplace_back(*t,pc);++issued;}}
   if(cycle==0)need(calls==0,"provider computed at admission");p.advance(provider);need(p.conserved(),"lookup conservation");
  }
  need(done==128&&calls==128&&contiguous,"actual provider II1");cycle_totals.push_back(last);
  // No consumption: all finite contexts fill; requests must backpressure.
  LookupPort full(mode,g,L,L);for(unsigned i=0;i<20;++i){full.request(0x1234+i,true);full.advance(provider);}need(full.pending()==4&&full.full_stalls>0,"unbounded contexts");
  full.cancel();for(unsigned i=0;i<8;++i)full.advance(provider);need(full.pending()==0&&full.cancelled==4&&full.conserved(),"squash lost contexts");stale+=4;
 }
 // A live latched fold bit changes real hash/provider payload, not source.
 {LookupPort p(Mode::Direct,g,2,2);Provider a;auto provider=[&](auto pc,auto cond,const auto&fold,auto path){return a.run(pc,cond,fold,path);};auto t=p.request(0x1234,true);p.advance(provider);p.advance(provider);
  LookupPort clean=p;auto raw=p.source.source_bit(0);p.corrupt({start(p,"provider_fold_path_latch_0")});p.advance(provider);clean.advance(provider);auto r=p.take(*t),c=clean.take(*t);need(r&&c&&r->payload.data!=c->payload.data,"fold latch healed or ignored");need(p.source.source_bit(0)==raw,"fold latch alias");}
 // Every added metadata bit is corrected in actual copies with one real hold.
 {LookupPort seed(Mode::Direct,g);Provider a;auto provider=[&](auto pc,auto cond,const auto&fold,auto path){return a.run(pc,cond,fold,path);};auto t=seed.request(0x1234,true);
  for(auto&r:seed.manifest())if(r.name.find("provider_")==0&&(r.name.find("metadata")!=std::string::npos||r.name.find("control")!=std::string::npos))for(size_t bit=r.start;bit<r.start+r.bits;++bit){
   LookupPort p=seed;p.corrupt({bit});need(!p.take(*t),"response before stages");need(!p.request(0x9999,true),"metadata correction no real hold");p.advance(provider);p.advance(provider);auto out=p.take(*t);need(out&&out->pc==0x1234&&p.metadata_repairs==1,"metadata correction lost actual PC/token");++metadata;}
 }
 // Reset during held decode does not expose old token or drop accepted write.
 {LookupPort p(Mode::Overwrite,g,2,2);Provider a;auto provider=[&](auto pc,auto cond,const auto&fold,auto path){return a.run(pc,cond,fold,path);};auto t=p.request(0x4444,true);auto u=p.source.accept(Kind::Append,1,1,0);need(bool(u),"source append setup");
  p.corrupt({start(p,"provider_context_metadata_0")+2});p.cancel();for(unsigned i=0;i<10;++i){p.advance(provider);need(!p.take(*t),"stale provider response escaped");}need(p.source.source_bit(0)&&p.acks==1&&p.conserved(),"cancel dropped source operation");}

#include "lookup_extra.inc"
 std::cout<<"{\"status\":\"PASS_FINITE_CONTEXT_REAL_PINNED_PROVIDER_PIPELINE_NOT_O3\",\"normal_predictions\":"<<normal<<",\"trained_dependent_predictions\":"<<dependent<<",\"tiny_wraps\":"<<wraps<<",\"expected_fail_closed_fixtures\":"<<expected_fail_closed<<",\"metadata_SBU\":"<<metadata<<",\"stale_contexts\":"<<stale<<",\"independent_II1\":true,\"actual_source_L\":[1,2],\"provider_extra_L\":1,\"requests\":128,\"total_ready_cycles\":[";
 for(unsigned i=0;i<cycle_totals.size();++i){if(i)std::cout<<',';std::cout<<cycle_totals[i];}std::cout<<"],\"dependent_synthetic_component_cycles\":[";for(unsigned i=0;i<dependent_cycles.size();++i){if(i)std::cout<<',';std::cout<<dependent_cycles[i];}std::cout<<"],\"gem5_CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
