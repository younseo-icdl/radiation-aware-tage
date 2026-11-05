#include "predictor/tage_adapter.hpp"
#include "fault/multiplicity.hpp"
#include "predictor/gshare_adapter.hpp"
#include "gshare_original.h"
#include <fstream>
#include <iostream>
#include <chrono>
#include <sys/resource.h>
using namespace bp;
int main(int argc,char**argv){try{
 if(argc!=4&&argc!=7)throw std::runtime_error("usage: pilot EVENTS_PER_FIELD SEED OUTPUT_CSV [K1_WEIGHT K2_WEIGHT MODEL_LABEL]");unsigned events=std::stoul(argv[1]);uint64_t seed=std::stoull(argv[2]);if(events>20||events<1)throw std::runtime_error("bounded pilot: 1..20 events/field");
 bool summary_model=argc==7;MultiplicityProfile profile(summary_model?std::stoull(argv[4]):1,summary_model?std::stoull(argv[5]):0);std::string model=summary_model?argv[6]:"M0";
 std::ofstream out(argv[3]);if(!out)throw std::runtime_error("output file unavailable");out<<"workload,field,trial,seed,site_id,bank,row,bit,width,inject_conditional_ordinal,harm,help,net,prediction_divergences,first_divergence,last_divergence,end_differing_logical_bits,trial_wall_seconds,peak_rss_kib,status,model,multiplicity,event_site_ids,mapping\n";
 for(const auto* name:{"SHORT-INT-1","SHORT-FP-1"}){
  std::ifstream file(std::string("workloads/derived/")+name+".branches");if(!file)throw std::runtime_error("missing workload window");std::vector<Branch> trace;Branch b;
  while(file>>b.pc>>b.target>>b.taken>>b.conditional)trace.push_back(b);
  TageAdapter clean;GshareAdapter gs;PREDICTOR old;unsigned ordinal=0;size_t boundary=0;
  for(size_t i=0;i<trace.size();++i){auto& t=trace[i];if(t.conditional){bool a=gs.predict(t.pc),z=old.GetPrediction(t.pc);if(a!=z)throw std::runtime_error("real-trace Gshare mismatch");gs.update(t.pc,t.taken);old.UpdatePredictor(t.pc,t.taken,z,t.target);}clean.step(t);ordinal+=t.conditional;if(ordinal==20000){boundary=i+1;break;}}
  if(!boundary)throw std::runtime_error("short warmup");auto warm=clean.snapshot();std::vector<bool> gold;
  unsigned clean_misses=0;for(size_t i=boundary;i<trace.size();++i){bool p=clean.step(trace[i]);gold.push_back(p);clean_misses+=trace[i].conditional&&p!=trace[i].taken;}
  auto final_bits=clean.core.bits();auto sites=clean.core.sites();std::vector<std::vector<size_t>> byfield(6);for(auto s:sites)byfield[s.kind].push_back(s.id);
  std::cerr<<name<<" controls="<<trace.size()<<" boundary="<<boundary<<" clean_mispredicts="<<clean_misses<<" window_conditional=10000\n";
  for(unsigned field=0;field<6;++field)for(unsigned trial=0;trial<events;++trial){
   uint64_t event_seed=seed+(name==std::string("SHORT-INT-1")?0:1000000)+field*10000+trial;std::mt19937_64 rng(event_seed);
   unsigned k=summary_model?profile.draw(rng):1;auto event_ids=logical_adjacent_event(byfield[field],k,rng);auto id=event_ids[0];unsigned inject=std::uniform_int_distribution<unsigned>(0,9999)(rng);auto site=sites[id];
   auto start=std::chrono::steady_clock::now();TageAdapter faulty;faulty.restore(warm);unsigned o=0,harm=0,help=0,div=0;int first=-1,last=-1;bool injected=false;
   for(size_t i=boundary;i<trace.size();++i){const auto& t=trace[i];if(t.conditional&&o==inject){faulty.core.corrupt(event_ids);injected=true;}
    bool p=faulty.step(t),g=gold[i-boundary];if(t.conditional){bool fm=p!=t.taken,gm=g!=t.taken;harm+=fm&&!gm;help+=!fm&&gm;if(p!=g){++div;if(first<0)first=o;last=o;}++o;}}
   if(!injected||o!=10000)throw std::runtime_error("invalid injection/window");auto bits=faulty.core.bits();unsigned residual=0;for(size_t i=0;i<bits.size();++i)residual+=bits[i]!=final_bits[i];
   double sec=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();struct rusage use;getrusage(RUSAGE_SELF,&use);
   out<<name<<','<<field_name(field)<<','<<trial<<','<<event_seed<<','<<id<<','<<site.bank<<','<<site.row<<','<<site.bit<<','<<site.width<<','<<inject<<','<<harm<<','<<help<<','<<int(harm)-int(help)<<','<<div<<','<<first<<','<<last<<','<<residual<<','<<sec<<','<<use.ru_maxrss<<",PASS,"<<model<<','<<k<<',';for(size_t e=0;e<event_ids.size();++e){if(e)out<<';';out<<event_ids[e];}out<<",within_field_logical_flattening_assumption\n";
  }
 }
 return 0;
}catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
