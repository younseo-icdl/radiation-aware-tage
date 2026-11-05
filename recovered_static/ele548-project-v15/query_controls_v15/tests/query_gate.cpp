#include "source_access.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <fstream>
#include <iostream>
#include <random>
using namespace bp::v15;
static void need(bool v,const char*why){if(!v)throw std::runtime_error(why);}
static std::vector<Geometry> geometry(){bp::RoundState s;auto w=s.history_words();std::vector<Geometry> g;for(unsigned i=0;i<21;++i)g.push_back({s.fold_length(i),w[i].width});return g;}
static bp::v9::Payload dummy(uint64_t,bool,const std::array<unsigned,21>&,unsigned){return {};}
static void drain(Controller&c){for(unsigned i=0;i<200;++i){if(c.drained())return;c.advance(dummy);}throw std::runtime_error("controller drain timeout");}
struct Model:SourceAccess<bp::RoundState>{Model(const gem5::TAGEBaseParams&p,Mode m,unsigned L):SourceAccess(p){configure(m,1,L);}};
static void empty_frame(Controller&c,unsigned n,unsigned path){for(unsigned i=0;i<200&&!c.prepare_recovery();++i)c.advance(dummy);c.begin();c.restore(n,path);c.end();drain(c);}
static bp::Base::BranchInfo* predict(Model&m,uint64_t pc,bool cond){
 std::optional<Token> t;for(unsigned i=0;i<200&&!t;++i){t=m.engine->request(pc,cond);if(!t)m.advance();}need(bool(t),"native admission");
 for(unsigned i=0;i<200;++i){if(m.engine->peek(*t))return m.consume(*t);m.advance();}throw std::runtime_error("native provider response");
}
int main(int argc,char**argv){try{
 need(argc==2,"manifest path required");auto g=geometry();unsigned normal=0,squashes=0,metadata=0,negative=0,wraps=0;std::ofstream out(argv[1]);out<<"{\"scope\":\"CONTROLLER_AND_SOURCE_PROVIDER_NOT_CPU\",\"models\":[";bool first=true;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u})for(unsigned shift:{0u,2u}){
  gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.instShiftAmt=shift;p.histBufferSize=4096;Model model(p,mode,L);bp::RoundState ref(p);std::mt19937_64 rng(548);
  for(unsigned round=0;round<60;++round){std::vector<bp::Base::BranchInfo*> a,b;unsigned span=round==0?1000:1+unsigned(rng()%32);
   for(unsigned i=0;i<span;++i){auto pc=0x1000+(rng()%1024);bool conditional=rng()%7;auto*d=predict(model,pc,conditional);auto*r=ref.makeBranchInfo(pc,conditional);bool prediction=ref.tagePredict(0,pc,conditional,r);
    bp::v9::Payload exact,got;exact.capture_response(*r);exact.put(25,prediction);got.capture_response(*d);got.put(25,conditional?d->tagePred:true);need(exact.data==got.data,"native actual provider equality");
    model.updateHistories(0,pc,true,prediction,pc+64,{},d);ref.updateHistories(0,pc,true,prediction,pc+64,{},r);a.push_back(d);b.push_back(r);++normal;
   }
   for(unsigned wait=0;wait<200&&!model.engine->prepare_recovery();++wait)model.advance();model.engine->begin();model.engine->begin();
   for(unsigned i=span;i>1;--i){model.restoreHistState(0,a[i-1]);ref.restoreHistState(0,b[i-1]);}
   model.engine->end();const bool taken=rng()&1;model.updateHistories(0,a[0]->branchPC,true,taken,0x1234,{},a[0]);ref.updateHistories(0,b[0]->branchPC,true,taken,0x1234,{},b[0]);model.engine->end();++squashes;
   for(unsigned i=1;i<span;++i){delete a[i];delete b[i];}
   bool retired=false;for(unsigned wait=0;wait<200&&!retired;++wait){retired=model.engine->retire(a[0]->nGhist);if(!retired)model.advance();}need(retired,"native retirement credit");
   int draw=rng()&3;if(a[0]->condBranch){model.condBranchUpdate(0,a[0]->branchPC,taken,a[0],draw,0x1234,a[0]->tagePred);ref.condBranchUpdate(0,b[0]->branchPC,taken,b[0],draw,0x1234,b[0]->tagePred);}
   model.updateHistories(0,a[0]->branchPC,false,taken,0x1234,{},a[0]);ref.updateHistories(0,b[0]->branchPC,false,taken,0x1234,{},b[0]);delete a[0];delete b[0];
   for(unsigned i=0;i<200&&!model.engine->drained();++i)model.advance();need(model.engine->drained()&&model.engine->port.source.source_depth()==0,"native terminal source ownership");
   auto*probe=predict(model,0x1000,true);delete probe;auto aa=model.save(),bb=ref.save();auto source=model.engine->port.source.observe_source();
   need(aa.pred==bb.pred&&aa.hyst==bb.hyst&&aa.aging==bb.aging&&aa.alt==bb.alt&&aa.non_spec==bb.non_spec&&aa.folded==bb.folded,"native final tables/counters/folds mismatch");
   for(unsigned bank=1;bank<aa.tables.size();++bank)for(unsigned row=0;row<aa.tables[bank].size();++row){auto x=aa.tables[bank][row],y=bb.tables[bank][row];need(x.ctr==y.ctr&&x.tag==y.tag&&x.u==y.u,"native tagged training mismatch");}
   for(unsigned age=0;age<130;++age)need(source.raw[age]==ref.raw_bit(age),"native physical source mismatch");need(source.path==ref.read_history_word(22).limb[0]&&model.engine->conserved(),"native path/transactions mismatch");
  }
  if(shift==0){if(!first)out<<',';first=false;out<<"{\"mode\":"<<unsigned(mode)<<",\"update_L\":"<<L<<",\"query_L\":"<<L<<",\"bits\":"<<model.engine->bits()<<",\"regions\":[";bool a=true;for(auto&r:model.engine->manifest()){if(!a)out<<',';a=false;out<<"{\"name\":\""<<r.name<<"\",\"start\":"<<r.start<<",\"bits\":"<<r.bits<<'}';}out<<"]}";}
 }
 out<<"],\"excluded\":[\"configuration and absolute simulator cycle/hold helpers\",\"diagnostic counters\",\"CPU-owned consumed BranchInfo and original O3 time-buffer messages\",\"provider helper history arrays are combinational scratch, not second source\"]}\n";out.close();need(bool(out),"manifest output");
 // Incoming BPU message is retained by caller while admission is false. Only
 // that frame retries; source clock keeps draining four actual register slots.
 {Controller c(Mode::Direct,g);for(unsigned i=0;i<4;++i)c.append(1,i&1,0);need(!c.prepare_recovery(),"full source transaction incorrectly admitted");c.advance(dummy);need(!c.prepare_recovery(),"one free slot accepted two callbacks");c.advance(dummy);need(c.prepare_recovery(),"two credits not released");c.begin();c.begin();c.restore(3,0);c.end();c.restore(1,0);c.append(1,1,1);c.end();drain(c);need(c.enqueued==6&&c.issued==6&&c.max_count==4&&c.recovery_waits>=2&&c.port.source.source_depth()==1&&c.port.source.source_bit(0)&&c.conserved(),"backpressured actual squash lost/reordered source work");}
 // New metadata bits: actual data/check replicas, correction with real hold.
 {Controller seed(Mode::Recurrent,g,2,2);for(unsigned i=0;i<4;++i)seed.append(1,i&1,0);
  for(auto&r:seed.manifest())if(r.name.find("ingress_")==0)for(size_t bit=r.start;bit<r.start+r.bits;++bit){Controller c=seed;bool before=c.logical_bit(bit);c.corrupt({bit});need(!c.prepare_recovery()&&c.logical_bit(bit)==before&&c.metadata_repairs==1,"ingress correction not actual/held");drain(c);need(c.enqueued==4&&c.issued==4&&c.port.source.source_depth()==4&&c.conserved(),"ingress correction lost operand");++metadata;}
  auto region=seed.manifest().end();size_t start=0,width=0;for(auto&r:seed.manifest())if(r.name=="ingress_control_mirrored_SECDED"){start=r.start;width=r.bits;}
  Controller bad=seed;bad.corrupt({start,start+1,start+width/2,start+width/2+1});bool due=false;try{bad.prepare_recovery();}catch(const IntegrityError&){due=true;}need(due,"both ingress copies DUE passed");++negative;
 }
 // Repair-held cancellation is still captured; accepted writes are preserved.
 {Controller c(Mode::Overwrite,g,2,2);auto token=c.request(0x1000,true);need(bool(token),"cancel setup");c.append(1,1,0);size_t control=0;for(auto&r:c.manifest())if(r.name=="ingress_control_mirrored_SECDED")control=r.start;c.corrupt({control});c.cancel();drain(c);need(!c.peek(*token)&&c.port.cancelled==1&&c.port.source.source_bit(0)&&c.conserved(),"repair-held cancel lost");}
 // Wrap cannot deadlock queued pre-ID writes or a receiver waiting for squash.
 {Controller c(Mode::Direct,g,1,1,2,2);for(unsigned i=0;i<80;++i){std::optional<Token> t;for(unsigned n=0;n<30&&!t;++n){t=c.request(0x1000,true);if(!t)c.advance(dummy);}need(bool(t),"wrap admission");for(unsigned n=0;n<30&&!c.peek(*t);++n)c.advance(dummy);need(bool(c.take(*t)),"wrap consume");c.append(1,1,0);for(unsigned n=0;n<30&&!c.retire(1);++n)c.advance(dummy);drain(c);}wraps=c.port.source.stats.wrap_completions;need(wraps>40&&c.conserved(),"ingress wrap lost work");}
 std::cout<<"{\"status\":\"PASS_QUERY_UPDATE_SPLIT_NATIVE_EQUALITY_NOT_CPU\",\"normal_controls\":"<<normal<<",\"nested_corrected_squashes\":"<<squashes<<",\"new_metadata_SBU\":"<<metadata<<",\"expected_DUE_fixtures\":"<<negative<<",\"wraps\":"<<wraps<<",\"CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
