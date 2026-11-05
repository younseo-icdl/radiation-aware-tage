#include "source_access.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
#include <random>
using namespace bp::v15;
static void need(bool x,const char*s){if(!x)throw std::runtime_error(s);}
static std::vector<Geometry> geometry(){bp::RoundState s;auto w=s.history_words();std::vector<Geometry> g;for(unsigned i=0;i<21;++i)g.push_back({s.fold_length(i),w[i].width});return g;}
static bp::v9::Payload dummy(uint64_t,bool cond,const std::array<unsigned,21>&,unsigned){bp::v9::Payload p;if(!cond)p.put(25,true);return p;}
struct Model:SourceAccess<bp::RoundState>{
 unsigned peak=0;
 Model(const gem5::TAGEBaseParams&p,Mode m,unsigned U,unsigned Q,bool e,unsigned id=16,unsigned epoch=16):SourceAccess(p){configure(m,U,Q,id,epoch);if(e)enable_early();}
 void advance(){SourceAccess::advance();peak=std::max(peak,unsigned(engine->port.pending()));}
 std::optional<Token> request(uint64_t pc,bool cond){auto t=SourceAccess::request(pc,cond);peak=std::max(peak,unsigned(engine->port.pending()));return t;}
};
static bp::Base::BranchInfo* predict(Model&m,uint64_t pc,bool cond){
 std::optional<Token> token;for(unsigned i=0;i<500&&!token;++i){token=m.request(pc,cond);if(!token)m.advance();}need(bool(token),"prediction admission timeout");
 if(!cond&&m.early){need(m.early_ready(*token,pc),"early claim not actually ready");return m.consume_early(pc);}
 for(unsigned i=0;i<500;++i){if(m.engine->peek(*token))return m.consume(*token);m.advance();}throw std::runtime_error("conditional response timeout");
}
static void drain(Model&m){for(unsigned i=0;i<500;++i){if(m.drained())return;m.advance();}throw std::runtime_error("model drain timeout");}
static void compare(Model&m,bp::RoundState&r){
 auto*probe=predict(m,0x4010,true);delete probe;auto a=m.save(),b=r.save();
 need(a.pred==b.pred&&a.hyst==b.hyst&&a.aging==b.aging&&a.alt==b.alt&&a.non_spec==b.non_spec&&a.folded==b.folded,"early final predictor state mismatch");
 for(unsigned bank=1;bank<a.tables.size();++bank)for(unsigned row=0;row<a.tables[bank].size();++row){auto x=a.tables[bank][row],y=b.tables[bank][row];need(x.ctr==y.ctr&&x.tag==y.tag&&x.u==y.u,"early training changed");}
 auto src=m.engine->port.source.observe_source();for(unsigned i=0;i<130;++i)need(src.raw[i]==r.raw_bit(i),"early source bit mismatch");
 need(src.path==r.read_history_word(22).limb[0]&&m.conserved(),"early path/conservation mismatch");
}
int main(){try{
 unsigned normal=0,frames=0,metadata=0,due=0,wraps=0,max_live=0;auto g=geometry();
 // All fields and training remain pinned; final predictedTaken includes a
 // synthetic target-miss/fallthrough case, not a future actual branch outcome.
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned U:{1u,2u})for(unsigned Q:{1u,2u})for(unsigned shift:{0u,2u}){
  gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.instShiftAmt=shift;p.histBufferSize=4096;
  Model m(p,mode,U,Q,true,4,3);bp::RoundState ref(p);std::mt19937_64 rng(15548);
  for(unsigned round=0;round<30;++round){std::vector<bp::Base::BranchInfo*> a,b;unsigned span=1+rng()%32;
   for(unsigned i=0;i<span;++i){uint64_t pc=0x4000+rng()%256;bool cond=bool(rng()%3);auto*x=predict(m,pc,cond);auto*y=ref.makeBranchInfo(pc,cond);bool prediction=ref.tagePredict(0,pc,cond,y);
    if(cond){bp::v9::Payload aa,bb;aa.capture_response(*x);aa.put(25,x->tagePred);bb.capture_response(*y);bb.put(25,prediction);need(aa.data==bb.data,"conditional algorithm changed after early history");}
    bool final_prediction=cond?prediction:bool(rng()%4);m.updateHistories(0,pc,true,final_prediction,pc+16,{},x);ref.updateHistories(0,pc,true,final_prediction,pc+16,{},y);
    a.push_back(x);b.push_back(y);max_live=std::max(max_live,unsigned(m.engine->port.pending()));++normal;
   }
   for(unsigned i=0;i<500&&!m.prepare_recovery();++i)m.advance();need(m.early->pending()==0,"squash accepted before actual checkpoints");
   for(unsigned i=0;i<span;++i)need(a[i]->pathHist==b[i]->pathHist,"late checkpoint wrong source epoch");
   m.engine->begin();m.engine->begin();for(unsigned i=span;i>1;--i){m.restoreHistState(0,a[i-1]);ref.restoreHistState(0,b[i-1]);}m.engine->end();
   bool taken=rng()&1;m.updateHistories(0,a[0]->branchPC,true,taken,0x4010,{},a[0]);ref.updateHistories(0,b[0]->branchPC,true,taken,0x4010,{},b[0]);m.engine->end();++frames;
   for(unsigned i=1;i<span;++i){delete a[i];delete b[i];}
   bool retired=false;for(unsigned i=0;i<500&&!retired;++i){retired=m.retire(a[0]->nGhist);if(!retired)m.advance();}need(retired,"early actual retirement timeout");
   int draw=rng()&3;if(a[0]->condBranch){m.condBranchUpdate(0,a[0]->branchPC,taken,a[0],draw,0x4010,a[0]->tagePred);ref.condBranchUpdate(0,b[0]->branchPC,taken,b[0],draw,0x4010,b[0]->tagePred);}
   m.updateHistories(0,a[0]->branchPC,false,taken,0x4010,{},a[0]);ref.updateHistories(0,b[0]->branchPC,false,taken,0x4010,{},b[0]);delete a[0];delete b[0];drain(m);compare(m,ref);
  }
  wraps+=m.engine->port.source.stats.wrap_completions;
 }
 // Metadata snapshot explicitly rebinds the copied receiver to its copied
 // controller; no dangling reference to the golden/original instance.
 {Controller seed(Mode::Recurrent,g,2,2);EarlyReceiver original(seed);auto t=seed.request(0x4000,false);need(bool(t),"metadata setup request");need(bool(original.claim(0x4000)),"metadata setup claim");seed.append(1,1,0);
  for(size_t bit=0;bit<original.bits();++bit){Controller c=seed;EarlyReceiver r(original,c);bool before=r.logical_bit(bit);r.corrupt({bit});need(!r.ready()&&r.logical_bit(bit)==before&&r.metadata_repairs==1,"early metadata SBU not actual held correction");unsigned delivered=0;
   for(unsigned i=0;i<100&&!r.quiescent();++i){c.advance(dummy);r.advance([&](unsigned slot,unsigned path){need(slot==0&&path==0,"repaired checkpoint wrong owner/path");++delivered;});}
   need(r.quiescent()&&delivered==1&&r.conserved(),"metadata repair lost/dropped late checkpoint");++metadata;
  }
  Controller c=seed;EarlyReceiver bad(original,c);auto word=original.manifest()[0].bits/2;bad.corrupt({0,1,word,word+1});bool failed=false;try{bad.ready();}catch(const IntegrityError&){failed=true;}need(failed,"ambiguous owner DUE escaped");++due;
 }
 // A second SEU during repair and a cancel must retain the claimed checkpoint.
 {Controller c(Mode::Direct,g,1,2);EarlyReceiver r(c);auto t=c.request(0x4000,false);need(bool(t)&&bool(r.claim(0x4000)),"midrepair setup");c.append(1,1,0);r.corrupt({0});need(!r.ready(),"first repair hold");r.corrupt({2});r.cancel();unsigned delivered=0;
  for(unsigned i=0;i<100&&!r.quiescent();++i){c.advance(dummy);r.advance([&](unsigned,unsigned path){need(path==0,"midrepair path");++delivered;});}
  need(delivered==1&&r.metadata_repairs==2&&r.conserved()&&!c.take(*t),"cancel/midrepair stale owner");
 }
 // Completing a checkpoint releases an existing owner, and requires NO new
 // append credit. Otherwise full source credit + retire fence would deadlock.
 {Controller c(Mode::Recurrent,g,2,2);for(unsigned n=0;n<999;++n){while(!c.normal_ready())c.advance(dummy);c.append(1,n&1,1);c.advance(dummy);}for(unsigned i=0;i<50&&!c.drained();++i)c.advance(dummy);need(c.port.source.source_depth()==999,"credit setup depth");unsigned path=c.port.source.source_path();EarlyReceiver r(c);auto t=c.request(0x4000,false);need(bool(t)&&bool(r.claim(0x4000)),"full credit claim");c.append(1,1,0);unsigned delivered=0;
  for(unsigned i=0;i<100&&!r.quiescent();++i){c.advance(dummy);r.advance([&](unsigned,unsigned actual){need(actual==path,"full credit source path");++delivered;});}
  need(delivered==1&&r.quiescent()&&c.port.source.source_depth()==1000&&!c.normal_ready()&&r.conserved(),"full credit checkpoint deadlock");
 }
 // Four real contexts fill and reject a fifth; claimed contexts survive a
 // cancel, whereas an unclaimed stale result is discarded and conserved.
 {Controller c(Mode::Direct,g,1,2);EarlyReceiver r(c);
  for(unsigned i=0;i<4;++i){auto t=c.request(0x4000+4*i,false);need(bool(t)&&bool(r.claim(0x4000+4*i)),"finite context fill");c.advance(dummy);}
  need(!c.request(0x5000,false)&&c.port.full_stalls>0&&r.pending()==4,"queue full did not backpressure");r.cancel();unsigned delivered=0;
  for(unsigned i=0;i<100&&!r.quiescent();++i){c.advance(dummy);r.advance([&](unsigned,unsigned path){need(path==0,"cancelled live owner path");++delivered;});}
  need(delivered==4&&r.conserved(),"cancel discarded claimed owners");c.advance(dummy);auto stale=c.request(0x6000,true);need(bool(stale),"stale setup");for(unsigned i=0;i<4;++i)c.advance(dummy);r.cancel();r.advance([](unsigned,unsigned){throw std::runtime_error("stale unclaimed response published");});for(unsigned i=0;i<6;++i){c.advance(dummy);r.advance([](unsigned,unsigned){throw std::runtime_error("late stale response published");});}
  need(!c.take(*stale)&&c.port.cancelled==1&&r.conserved(),"stale cancellation not conserved");
 }
 // An actual unprotected path-latch SEU reaches the CPU checkpoint. No oracle
 // repairs it; it may subsequently damage rollback just as its manifest says.
 {Controller c(Mode::Direct,g,1,1);EarlyReceiver r(c);auto token=c.request(0x4000,false);need(bool(token)&&bool(r.claim(0x4000)),"stage fault setup");c.advance(dummy);size_t site=0;for(const auto&region:c.manifest())if(region.name=="provider_fold_path_latch_0")site=region.start+200;need(site!=0,"stage path site missing");c.corrupt({site});unsigned delivered=0;
  for(unsigned i=0;i<20&&!r.quiescent();++i){c.advance(dummy);r.advance([&](unsigned,unsigned path){need(path==1,"mid-stage path fault silently repaired");++delivered;});}
  need(delivered==1&&c.port.source.source_path()==0&&r.conserved(),"stage fault source was overwritten");
 }
 // Real dependent stream: only the current unconditional predicted direction
 // and an already available synthetic target choose the next PC. Conditional
 // requests wait for their own prediction. No future actual outcomes are used.
 std::cout<<"{\"status\":\"PASS_EARLY_UNCOND_ACTUAL_CHECKPOINT_PROTOCOL_NOT_CPU\",\"normal_controls\":"<<normal<<",\"nested_squash_frames\":"<<frames<<",\"metadata_SBU\":"<<metadata<<",\"expected_DUE\":"<<due<<",\"tiny_wrap_completions\":"<<wraps<<",\"max_lookup_pending_native_stream\":"<<max_live<<",\"CPU_trials\":0,\"timing_cases\":[";bool first=true;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned Q:{1u,2u})for(bool cond:{false,true}){
  uint64_t last_plain=0;for(bool early:{false,true}){gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;Model m(p,mode,1,Q,early);std::vector<bp::Base::BranchInfo*> live;uint64_t pc=0x4000;unsigned maximum=0;
   for(unsigned i=0;i<128;++i){auto*b=predict(m,pc,cond);bool direction=cond?b->tagePred:true;m.updateHistories(0,pc,true,direction,pc+16,{},b);live.push_back(b);pc=direction?pc+16:pc+4;maximum=std::max(maximum,unsigned(m.engine->port.pending()));}
   auto predicted=m.engine->port.source.cycle();maximum=m.peak;drain(m);auto checkpoint=m.engine->port.source.cycle();for(auto*b:live){while(!m.retire(b->nGhist))m.advance();delete b;}drain(m);
   if(!early)last_plain=predicted;else if(cond)need(predicted==last_plain&&maximum<=1,"conditional dependency was magically bypassed");else need(maximum>=2,"early stream did not genuinely overlap lookup requests");
   if(!first)std::cout<<',';first=false;std::cout<<"{\"mode\":"<<unsigned(mode)<<",\"query_L\":"<<Q<<",\"update_L\":1,\"conditional\":"<<(cond?"true":"false")<<",\"early\":"<<(early?"true":"false")<<",\"prediction_done_cycle\":"<<predicted<<",\"checkpoint_done_cycle\":"<<checkpoint<<",\"retirement_done_cycle\":"<<m.engine->port.source.cycle()<<",\"max_lookup_pending\":"<<maximum<<'}';
  }
 }
 std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
