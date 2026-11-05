#include "rate_state_v5/representation.hpp"
#include "replay/e1_trace.hpp"
#include <fstream>
#include <iostream>
#include <map>
#include <chrono>
using namespace bp;using namespace bp::v5;
uint64_t hash_values(const std::vector<unsigned>&v){uint64_t h=14695981039346656037ULL;for(auto x:v){h^=x;h*=1099511628211ULL;}return h;}
uint64_t raw_hash(const State&s){uint64_t h=14695981039346656037ULL;for(unsigned a=0;a<s.history_depth();++a){h^=s.source_bit(a);h*=1099511628211ULL;}return h;}
struct Saved{TageState::Snapshot base;std::vector<uint8_t>ring;unsigned head;std::mt19937_64 rng;};
Saved save(const Adapter&a){return {a.core.save(),a.core.raw_ring,a.core.raw_head,a.rng};}
void load(Adapter&a,const Saved&s){a.core.load(s.base);a.core.raw_ring=s.ring;a.core.raw_head=s.head;a.rng=s.rng;}
struct Plan{unsigned owner,inject;std::string field;size_t site;};
int main(int argc,char**argv){try{
 if(argc!=8)throw std::invalid_argument("TRACE MODE TAPS HORIZON PLAN OUTPUT WARMUP");
 auto tr=read_e1_trace(argv[1]);std::string mode=argv[2];unsigned taps=std::stoul(argv[3]),H=std::stoul(argv[4]),warm=std::stoul(argv[7]);
 std::ifstream planfile(argv[5]);std::vector<Plan> plans;Plan p;unsigned last=0;
 while(planfile>>p.owner>>p.inject>>p.field>>p.site){plans.push_back(p);last=std::max(last,p.inject+H);}
 last=H+10000;
 if(plans.empty()||tr.conditionals.size()<warm+last)throw std::runtime_error("incomplete real trace window");
 Adapter clean(mode,taps);size_t start=tr.conditionals[warm],end=tr.conditionals[warm+last-1]+1;
 for(size_t i=0;i<start;++i)clean.step(tr.controls[i].branch);
 auto initial=save(clean);std::vector<bool> gold;std::map<size_t,uint64_t> goldhash,goldraw;
 std::map<size_t,TageState::Snapshot> goldend;unsigned ord=0;uint64_t misses=0;
 std::set<size_t> samples,ends;
 for(auto&q:plans){ends.insert(tr.conditionals[warm+q.inject+H-1]);
  for(unsigned n=1;n<=H;++n)if(n<=512||n%128==0||n==1000||n==10000||n==100000||n==H)samples.insert(tr.conditionals[warm+q.inject+n-1]);}
 for(size_t i=start;i<end;++i){auto&b=tr.controls[i].branch;bool pred=clean.step(b);gold.push_back(pred);misses+=b.conditional&&pred!=b.taken;
  if(samples.count(i)){goldhash[i]=hash_values(clean.core.hashes());goldraw[i]=raw_hash(clean.core);}
  if(ends.count(i))goldend.emplace(i,clean.core.save());
 }
 std::ofstream out(argv[6]);out<<"mode,taps,owner,field,site,inject_conditional,horizon,instructions,clean_misses,fault_misses,harm,help,net,hash_first_equal,hash_last_divergence,hash_terminal_mismatch,raw_last_divergence,raw_terminal_mismatch,table_terminal_mismatch,prediction_last_divergence,status,wall_seconds,read_taps\n";
 for(auto&q:plans){auto time=std::chrono::steady_clock::now();Adapter fault(mode,taps);load(fault,initial);bool injected=false;unsigned n=0;uint64_t cm=0,fm=0,harm=0,help=0,firsteq=0,lasthash=0,lastraw=0,lastpred=0;bool ht=false,rt=false;size_t finish=tr.conditionals[warm+q.inject+H-1];std::string status="PASS";
  try{
   for(size_t i=start;i<=finish;++i){auto&b=tr.controls[i].branch;
    if(b.conditional&&n==q.inject&&!injected){
     if(q.field=="head"){fault.core.raw_head^=1u<<q.site;fault.core.valid_head();}
     else fault.core.corrupt({q.site});injected=true;
    }
    bool fp=fault.step(b),gp=gold[i-start];
    if(injected&&b.conditional){unsigned age=n-q.inject+1;cm+=gp!=b.taken;fm+=fp!=b.taken;harm+=gp==b.taken&&fp!=b.taken;help+=gp!=b.taken&&fp==b.taken;if(gp!=fp)lastpred=age;
     if(samples.count(i)){ht=hash_values(fault.core.hashes())!=goldhash.at(i);rt=raw_hash(fault.core)!=goldraw.at(i);if(ht)lasthash=age;else if(!firsteq)firsteq=age;if(rt)lastraw=age;}
    }n+=b.conditional;
   }
  }catch(const std::exception&e){status=std::string("FAIL:")+e.what();}
  unsigned table=0;auto final=fault.core.save();auto&gs=goldend.at(finish);
  for(unsigned bank=1;bank<final.tables.size();++bank)for(unsigned row=0;row<final.tables[bank].size();++row){auto&a=final.tables[bank][row];auto&b=gs.tables[bank][row];table+=a.ctr!=b.ctr||a.tag!=b.tag||a.u!=b.u;}
  auto ins=tr.controls[finish].instruction-tr.controls[tr.conditionals[warm+q.inject]].instruction+1;
  out<<mode<<','<<taps<<','<<q.owner<<','<<q.field<<','<<q.site<<','<<q.inject<<','<<H<<','<<ins<<','<<cm<<','<<fm<<','<<harm<<','<<help<<','<<int64_t(harm)-int64_t(help)<<','<<firsteq<<','<<lasthash<<','<<ht<<','<<lastraw<<','<<rt<<','<<table<<','<<lastpred<<','<<status<<','<<std::chrono::duration<double>(std::chrono::steady_clock::now()-time).count()<<','<<fault.core.read_demands()<<'\n';out.flush();
 }
 uint64_t ins=tr.controls[end-1].instruction-tr.controls[start].instruction+1;
 std::cout<<"{\"mode\":\""<<mode<<"\",\"clean_misses\":"<<misses<<",\"instructions\":"<<ins<<",\"clean_MPKI\":"<<1000.0*misses/ins<<",\"trials\":"<<plans.size()<<",\"horizon\":"<<H<<",\"read_taps\":"<<clean.core.read_demands()<<"}\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
