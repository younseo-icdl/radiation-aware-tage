// Derived from persistent.cpp; canonical-zero reset instead of restoring a trained snapshot.
#include "rate_state_v5/representation.hpp"
#include "replay/e1_trace.hpp"
#include <fstream>
#include <iostream>
using namespace bp;using namespace bp::v5;
struct Snapshot{TageState::Snapshot base;std::vector<uint8_t>ring;unsigned head,path;std::mt19937_64 rng;};
Snapshot save(const Adapter&a){return {a.core.save(),a.core.raw_ring,a.core.raw_head,a.core.direct_path,a.rng};}
void load(Adapter&a,const Snapshot&s){a.core.load(s.base);a.core.raw_ring=s.ring;a.core.raw_head=s.head;a.core.direct_path=s.path;a.rng=s.rng;}
int main(int argc,char**argv){try{
 if(argc!=5)throw std::invalid_argument("TRACE MODE PLAN OUTPUT");auto trace=read_e1_trace(argv[1]);std::string mode=argv[2];
 Adapter warm(mode);size_t start=trace.conditionals.at(10000),end=trace.conditionals.at(20000);
 for(size_t i=0;i<start;++i)warm.step(trace.controls[i].branch);auto initial=save(warm);Adapter cold_init(mode);auto cold=save(cold_init);
 struct SitePlan{unsigned owner,offset;std::string field;size_t id;};std::ifstream in(argv[3]);std::vector<SitePlan> plans;SitePlan s;while(in>>s.owner>>s.offset>>s.field>>s.id)if(s.field=="raw")plans.push_back(s);
 std::ofstream out(argv[4]);out<<"mode,owner,reset_each_task,repetitions,task,clean_misses,fault_misses,harm,help,net,hash_terminal_mismatch,table_terminal_mismatch\n";
 for(unsigned reps:{2u,8u,32u})for(bool reset:{false,true})for(auto&p:plans){Adapter c(mode),f(mode);load(c,initial);load(f,initial);
  for(unsigned task=0;task<reps;++task){if(reset&&task){load(c,cold);load(f,cold);}uint64_t cm=0,fm=0,h=0,help=0;
   for(size_t i=start;i<end;++i){if(!task&&i==start+1000)f.core.corrupt({p.id});auto&b=trace.controls[i].branch;bool cp=c.step(b),fp=f.step(b);if(b.conditional){cm+=cp!=b.taken;fm+=fp!=b.taken;h+=cp==b.taken&&fp!=b.taken;help+=cp!=b.taken&&fp==b.taken;}}
   auto cs=c.core.save(),fs=f.core.save();unsigned residual=0;for(unsigned bank=1;bank<cs.tables.size();++bank)for(unsigned row=0;row<cs.tables[bank].size();++row){auto&a=cs.tables[bank][row];auto&b=fs.tables[bank][row];residual+=a.ctr!=b.ctr||a.tag!=b.tag||a.u!=b.u;}
   out<<mode<<','<<p.owner<<','<<reset<<','<<reps<<','<<task+1<<','<<cm<<','<<fm<<','<<h<<','<<help<<','<<int64_t(h)-int64_t(help)<<','<<(c.core.hashes()!=f.core.hashes())<<','<<residual<<'\n';
  }
 }
 std::cout<<"PASS real trace segment repetition diagnostic; canonical cold predictor reset vs retained state; same fixed branch stream, not native CPU performance\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
