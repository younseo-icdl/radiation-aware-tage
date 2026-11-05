// Golden-assisted interventions are diagnostic only. No production policy links this executable.
#include "replay/e1_trace.hpp"
#include <iostream>
#include <map>
#include <tuple>
using namespace bp;
struct Observation {int hit=0,alt=0,index=0;unsigned provider=0;};
struct Diagnostic {
 TageAdapter a; bool learning;uint64_t draws=0,hash=14695981039346656037ULL;
 Diagnostic(bool l):learning(l){}
 bool step(const Branch& b,Observation& o){
  auto* bi=a.core.makeBranchInfo(b.pc,b.conditional);bool p=a.core.tagePredict(0,b.pc,b.conditional,bi);
  o={bi->hitBank,bi->altBank,bi->hitBankIndex,bi->provider};
  int n=int(a.predictor_rng()%std::numeric_limits<int>::max())&3;++draws;hash^=unsigned(n);hash*=1099511628211ULL;
  if(learning&&b.conditional)a.core.condBranchUpdate(0,b.pc,b.taken,bi,n,b.target,p);
  a.core.updateHistories(0,b.pc,false,b.taken,b.target,{},bi);delete bi;return p;
 }
};
void intervene(Diagnostic& bad,const Diagnostic& good,const std::string& arm){
 if(arm=="NONE")return;
 if(arm=="SHAM"){bad.a.restore(bad.a.snapshot());return;}
 if(arm=="FULL"){bad.a.restore(good.a.snapshot());bad.draws=good.draws;bad.hash=good.hash;return;}
 bool h=arm=="H_ONLY"||arm=="HF"||arm=="HFT"||arm=="HF_R"||arm=="HFTC";
 bool f=arm=="F_ONLY"||arm=="HF"||arm=="HFT"||arm=="HF_R"||arm=="HFTC";
 if(h)for(unsigned w=21;w<23;++w)bad.a.core.write_history_word(w,good.a.core.read_history_word(w));
 if(f)for(unsigned w=0;w<21;++w)bad.a.core.write_history_word(w,good.a.core.read_history_word(w));
 if(arm=="T_ONLY"||arm=="HFT"||arm=="HFTC"){
  auto s=bad.a.core.save(),g=good.a.core.save();s.pred=g.pred;s.hyst=g.hyst;s.tables=g.tables;
  if(arm=="HFTC"){s.alt=g.alt;s.aging=g.aging;}
  bad.a.core.load(s);
 }
 if(arm=="HF_R")bad.a.predictor_rng=good.a.predictor_rng;
}
struct Diff {unsigned h=0,p=0,f=0,t=0,c=0;bool r=false;};
Diff diff(const Diagnostic& x,const Diagnostic& y){
 Diff d;
 for(unsigned w=0;w<23;++w){auto a=x.a.core.read_history_word(w),b=y.a.core.read_history_word(w);unsigned n=0;for(unsigned j=0;j<3;++j)n+=__builtin_popcountll(a.limb[j]^b.limb[j]);if(w<21)d.f+=n;else if(w==21)d.h=n;else d.p=n;}
 auto a=x.a.core.save(),b=y.a.core.save();
 for(size_t i=0;i<a.pred.size();++i)d.t+=a.pred[i]!=b.pred[i];
 for(size_t i=0;i<a.hyst.size();++i)d.t+=a.hyst[i]!=b.hyst[i];
 for(size_t bank=1;bank<a.tables.size();++bank)for(size_t row=0;row<a.tables[bank].size();++row){auto u=a.tables[bank][row],v=b.tables[bank][row];d.t+=(u.ctr!=v.ctr)+(u.tag!=v.tag)+(u.u!=v.u);}
 d.c=(a.aging!=b.aging);for(size_t i=0;i<a.alt.size();++i)d.c+=a.alt[i]!=b.alt[i];d.r=x.a.predictor_rng!=y.a.predictor_rng;return d;
}
int main(int argc,char** argv){try{
 if(argc!=4)throw std::invalid_argument("causal TRACE PLAN TSV_OUTPUT");auto trace=read_e1_trace(argv[1]);std::ifstream plan(argv[2]);std::ofstream out(argv[3]);std::ofstream checkpoints(std::string(argv[3])+".checkpoints.csv");
 out<<"label,owner,stratum,site,anchor,delay,arm,learning,horizon,harm,help,net,pre_net,post_net,prediction_divergences,provider_divergences,H_diff,P_diff,F_diff,T_diff,C_diff,R_diff,draws_equal,full_gate,status\n";
 checkpoints<<"label,control_elapsed,conditional_elapsed,net,H_diff,P_diff,F_diff,T_diff,C_diff,R_diff\n";
 TageAdapter warm;size_t warmed=0;unsigned previous_anchor=0;TageAdapter::Snapshot anchor_snapshot;
 std::string label,owner,stratum,arm;size_t site;unsigned anchor,delay,learning,horizon;
 while(plan>>label>>owner>>stratum>>site>>anchor>>delay>>arm>>learning>>horizon){
  if(anchor<previous_anchor)throw std::invalid_argument("non-monotone owner anchors");size_t begin=trace.conditionals.at(anchor);
  if(anchor!=previous_anchor||!warmed){for(;warmed<begin;++warmed)warm.step(trace.controls[warmed].branch);anchor_snapshot=warm.snapshot();previous_anchor=anchor;}
  Diagnostic good(learning),bad(learning);good.a.restore(anchor_snapshot);bad.a.restore(anchor_snapshot);bad.a.core.corrupt({site});
  uint64_t harm=0,help=0,pre_harm=0,pre_help=0,pdiv=0,providerdiv=0;unsigned cond=0,elapsed=0;bool repaired=false;bool full_gate=true;
  for(size_t i=begin;i<trace.controls.size()&&cond<horizon;++i,++elapsed){
   if(!repaired&&elapsed==delay&&arm!="NONE"){
    intervene(bad,good,arm);repaired=true;pre_harm=harm;pre_help=help;
    if(arm=="FULL"&&!bad.a.core.equal(good.a.core))throw std::runtime_error("FULL structural restoration failed");
    auto d=diff(bad,good);checkpoints<<label<<','<<elapsed<<','<<cond<<','<<int64_t(harm)-int64_t(help)<<','<<d.h<<','<<d.p<<','<<d.f<<','<<d.t<<','<<d.c<<','<<d.r<<'\n';
   }
   Observation go,bo;const auto& b=trace.controls[i].branch;bool gp=good.step(b,go),bp=bad.step(b,bo);
   if(b.conditional){++cond;if(bp!=gp)++pdiv;providerdiv+=(go.hit!=bo.hit||go.alt!=bo.alt||go.index!=bo.index||go.provider!=bo.provider);harm+=(bp!=b.taken&&gp==b.taken);help+=(bp==b.taken&&gp!=b.taken);}
   if(arm=="FULL"&&repaired&&(bp!=gp||bad.a.predictor_rng!=good.a.predictor_rng))throw std::runtime_error("FULL future equality failed");
   if(b.conditional&&(cond==130||cond==1000||cond==10000||cond==100000||cond==horizon)){
    auto d=diff(bad,good);if(arm=="FULL"&&repaired&&(d.h||d.p||d.f||d.t||d.c||d.r))throw std::runtime_error("FULL checkpoint equality failed");
    checkpoints<<label<<','<<elapsed+1<<','<<cond<<','<<int64_t(harm)-int64_t(help)<<','<<d.h<<','<<d.p<<','<<d.f<<','<<d.t<<','<<d.c<<','<<d.r<<'\n';
   }
  }
  if(cond!=horizon)throw std::runtime_error("short actual trace window");auto d=diff(bad,good);auto net=int64_t(harm)-int64_t(help),pre=int64_t(pre_harm)-int64_t(pre_help);
  out<<label<<','<<owner<<','<<stratum<<','<<site<<','<<anchor<<','<<delay<<','<<arm<<','<<learning<<','<<horizon<<','<<harm<<','<<help<<','<<net<<','<<pre<<','<<net-pre<<','<<pdiv<<','<<providerdiv<<','<<d.h<<','<<d.p<<','<<d.f<<','<<d.t<<','<<d.c<<','<<d.r<<','<<(good.draws==bad.draws)<<','<<full_gate<<",PASS\n";out.flush();
 }
 std::cout<<"PASS ORACLE_DIAGNOSTIC causal replay only\n";
 }catch(const std::exception& e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
