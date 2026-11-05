#include "service.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <deque>
#include <fstream>
#include <iostream>
#include <random>

using namespace bp::v12;
static void need(bool v,const char* why){if(!v)throw std::runtime_error(why);}
static std::vector<Geometry> geometry(){bp::RoundState s;auto words=s.history_words();std::vector<Geometry> out;for(unsigned w=0;w<21;++w)out.push_back({s.fold_length(w),words[w].width});return out;}
static void tick(Service&s){s.tick();need(s.conserved(),"transaction conservation");}
static Reply run(Service&s,Kind kind,unsigned n=0,unsigned bits=0,unsigned arg=0){
 std::optional<Token> token;
 for(unsigned t=0;t<10000&&!token;++t){token=s.accept(kind,n,bits,arg);if(!token){if(s.drained()&&s.wrap_waiting())s.acknowledge_receiver_drained();tick(s);}}
 need(bool(token),"command admission stuck");
 for(unsigned t=0;t<10000;++t){if(auto r=s.take(*token))return *r;tick(s);}
 throw std::runtime_error("completion timeout");
}
static unsigned logical_width(const Service&s,const std::string& name,size_t*start=nullptr){for(auto&r:s.manifest())if(r.name==name){if(start)*start=r.start;return r.bits;}throw std::runtime_error("missing manifest region");}
static void compare_source(Service&s,bp::RoundState&ref){
 auto reply=run(s,Kind::Read);for(unsigned a=0;a<130;++a)need(s.source_bit(a)==ref.raw_bit(a),"source differs from pinned raw history");
 for(unsigned w=0;w<21;++w)need(reply.folds[w]==ref.read_history_word(w).limb[0],"fold differs from pinned recurrence");
 need(reply.path==ref.read_history_word(22).limb[0],"path differs");
}
static void setpath(bp::RoundState&r,unsigned path){bp::Word w;w.limb[0]=path;r.write_history_word(22,w);}
int main(int argc,char**argv){try{
 need(argc==2,"usage service_gate MANIFEST_JSON");auto g=geometry();uint64_t source_checks=0,metadata_bits=0,wraps=0;
 std::ofstream manifest(argv[1]);manifest<<"{\"scope\":\"FINITE_SOURCE_COMPONENT_NOT_CPU_OR_FULL_PROTECTION\",\"models\":[";bool first=true;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  Service s(mode,g,L,L);gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.histBufferSize=4096;bp::RoundState ref(p);
  std::mt19937_64 input(0x120001);std::deque<bp::Base::BranchInfo*> live;
  for(unsigned i=0;i<3000;++i){
   auto choice=input()%5;
   if(live.empty()||(choice<3&&live.size()<64)){
    auto* bi=ref.makeBranchInfo(0x1001+i,true);ref.recordHistState(0,bi);bi->modified=true;bi->nGhist=1+unsigned(input()%2);
    unsigned value=input()&3,pathbit=input()&1;run(s,Kind::Append,bi->nGhist,value,pathbit);
    ref.updateGHist(0,value,bi->nGhist);setpath(ref,((ref.read_history_word(22).limb[0]<<1)|pathbit)&65535);live.push_back(bi);
   }else if(choice==3){auto* bi=live.back();live.pop_back();run(s,Kind::Undo,bi->nGhist,0,bi->pathHist);ref.restoreHistState(0,bi);delete bi;
   }else{auto*bi=live.front();live.pop_front();run(s,Kind::Commit,bi->nGhist);delete bi;}
   compare_source(s,ref);++source_checks;
  }
  while(!live.empty()){auto*bi=live.back();live.pop_back();run(s,Kind::Undo,bi->nGhist,0,bi->pathHist);ref.restoreHistState(0,bi);delete bi;compare_source(s,ref);}
  need(s.source_depth()==0&&s.conserved(),"terminal retention depth");
  if(!first)manifest<<',';first=false;
  manifest<<"{\"mode\":"<<unsigned(mode)<<",\"update_L\":"<<L<<",\"lookup_L\":"<<L<<",\"total_bits\":"<<s.bits()<<",\"regions\":[";
  bool a=true;for(auto&r:s.manifest()){if(!a)manifest<<',';a=false;manifest<<"{\"name\":\""<<r.name<<"\",\"start\":"<<r.start<<",\"bits\":"<<r.bits<<'}';}manifest<<"]}";
 }
 manifest<<"],\"excluded\":[\"software counters\",\"absolute cycle/hold timing helper\",\"elaboration mode, geometry and L/II\",\"host temporary combinational arithmetic/padding\"]}\n";
 manifest.close();need(bool(manifest),"manifest output");

 // Independent lookup pipeline reaches one result/cycle after fill, at L1/2.
 for(unsigned L:{1u,2u})for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite}){
  Service s(mode,g,L,L);unsigned issued=0,completed=0;uint64_t previous=0;bool contiguous=true;
  for(unsigned t=0;t<1000&&completed<200;++t){
   if(auto r=s.take()){if(completed&&s.cycle()!=previous+1)contiguous=false;previous=s.cycle();++completed;}
   if(issued<200&&s.accept(Kind::Read))++issued;tick(s);
  }
  need(issued==200&&completed==200&&contiguous,"independent II1 throughput");
  need(s.conserved(),"independent conservation");
 }
 // Actual response backpressure fills finite stages/FIFO and rejects input.
 {Service s(Mode::Direct,g,2,2);unsigned accepted=0;
  for(unsigned t=0;t<50;++t){accepted+=bool(s.accept(Kind::Read));tick(s);}
  need(accepted==10&&s.stats.input_full_stalls>0&&s.stats.response_stalls>0,"finite storage backpressure");
  unsigned done=0;for(unsigned t=0;t<100&&done<accepted;++t){if(s.take())++done;tick(s);}need(done==accepted&&s.conserved(),"backpressure lost work");}
 // Ready input samples at accept; no result exists until the next real stage.
 {Service s(Mode::Direct,g,1,1);auto t=s.accept(Kind::Read);need(bool(t)&&!s.take(t),"ready sample request/early result");
  s.corrupt({s.active_raw_site(0)});tick(s);auto r=s.take(t);need(bool(r),"L1 read response");for(auto x:r->folds)need(x==0,"ready operand resampled at completion");need(s.source_bit(0),"source flip lost");}
 // A waiting query samples only after actual source RMW and write-first bypass.
 {Service s(Mode::Direct,g,1,1);auto update=s.accept(Kind::Append,1,1,1);auto read=s.accept(Kind::Read);need(bool(update)&&bool(read),"queued query setup");
  tick(s);need(!s.take(read),"queued response calculated before operand stage");s.corrupt({s.active_raw_site(0)});tick(s);
  auto r=s.take(read);need(bool(r),"write-first read response");for(auto x:r->folds)need(x==1,"query used completion-time source instead of actual bypass latch");}
 // Mid-stage payload error is visible; no golden reconstruction is consulted.
 {Service s(Mode::Direct,g,2,2);s.corrupt({s.active_raw_site(0)});auto t=s.accept(Kind::Read);
  size_t id;logical_width(s,"lookup_payload_0",&id);s.corrupt({id});tick(s);need(!s.take(t),"L2 response early");tick(s);
  auto r=s.take(t);need(bool(r),"mid-stage response");for(auto x:r->folds)need(x==0,"mid-stage fault secretly repaired");need(s.source_bit(0),"stage flip modified source");}
 // All physical metadata bits, populated stage, exact correction and real hold.
 {Service seed(Mode::Overwrite,g,2,2);need(bool(seed.accept(Kind::Append,1,1,1)),"metadata setup");tick(seed);
  for(auto&r:seed.manifest())if(r.name.find("metadata")!=std::string::npos||r.name.find("mirrored_SECDED")!=std::string::npos)
   for(size_t id=r.start;id<r.start+r.bits;++id){Service s=seed;bool before=s.logical_bit(id);s.corrupt({id});auto old=s.stats.produced;tick(s);
    need(s.logical_bit(id)==before&&s.stats.metadata_repairs==1&&s.stats.produced==old,"metadata correction/hold");
    for(unsigned i=0;i<8;++i){tick(s);s.take();}need(s.stats.completed==1&&s.conserved(),"metadata repair lost source operand");++metadata_bits;}
  size_t start;auto width=logical_width(seed,"controller_mirrored_SECDED",&start);
  Service s=seed;s.corrupt({start+14,start+15});tick(s);need(s.stats.metadata_repairs==1,"two-bit primary recovery");tick(s);tick(s);need(s.conserved(),"DUE loss");
  Service bad=seed;bad.corrupt({start+14,start+15,start+width/2+14,start+width/2+15});bool failed=false;
  try{tick(bad);}catch(const IntegrityError&){failed=true;}need(failed,"both copies DUE falsely passed");
 }
 // Atomic bad events and copied snapshots cannot alias original storage.
 {Service a(Mode::Overwrite,g);Service b=a;auto before=a.logical_bit(0);b.corrupt({0});need(a.logical_bit(0)==before&&b.logical_bit(0)!=before,"snapshot alias");
  bool rejected=false;try{a.corrupt({0,0});}catch(const std::invalid_argument&){rejected=true;}need(rejected&&a.logical_bit(0)==before,"atomic duplicate partial mutation");}
 // A raw bit can re-enter after undo; source retention is not oracle healed.
 {Service s(Mode::Overwrite,g);auto id=s.active_raw_site(64);s.corrupt({id});
  for(unsigned i=0;i<130;++i)run(s,Kind::Append,1,0,0);for(unsigned i=0;i<130;++i)need(!s.source_bit(i),"raw did not leave active window");
  for(unsigned i=0;i<130;++i)run(s,Kind::Undo,1,0,0);need(s.source_bit(64),"rollback resurrected fault was erased");}
 // Retention credits are reserved before acceptance, not after an overflow.
 {Service s(Mode::Direct,g);for(unsigned i=0;i<500;++i)run(s,Kind::Append,2,0,0);
  tick(s);need(!s.accept(Kind::Append,1,0,0)&&s.stats.credit_stalls>0,"retention credit overflow");
  run(s,Kind::Undo,2,0,0);run(s,Kind::Append,2,3,1);need(s.source_depth()==1000,"retention release");}
 // Epoch cancellation discards only reads; accepted source operations survive.
 {Service s(Mode::Overwrite,g,2,2);auto read=s.accept(Kind::Read);tick(s);auto append=s.accept(Kind::Append,1,1,1);need(bool(append),"squash source setup");
  s.cancel_reads();for(unsigned i=0;i<16;++i){need(!s.take(read),"stale response escaped");tick(s);if(auto r=s.take())need(r->kind==Kind::Append&&r->token==*append,"accepted source dropped/changed");}
  need(s.stats.completed==1&&s.stats.cancelled==1&&s.source_bit(0)&&s.conserved(),"squash discarded source");}
 // A squash arriving during correction is latched; a second SEU extends hold.
 {Service s(Mode::Overwrite,g,2,2);auto read=s.accept(Kind::Read);tick(s);auto append=s.accept(Kind::Append,1,1,1);need(bool(append),"held squash setup");
  size_t control;logical_width(s,"controller_mirrored_SECDED",&control);s.corrupt({control+14});s.cancel_reads();need(!s.take(read),"held squash leaked response");
  size_t q;logical_width(s,"command_metadata_3",&q);s.corrupt({q+4});tick(s);need(s.stats.metadata_repairs==2&&s.stats.produced==0,"mid-repair SEU did not hold");
  for(unsigned i=0;i<12;++i){tick(s);if(auto r=s.take())need(r->kind==Kind::Append,"latched squash lost stale filter");}
  need(s.stats.completed==1&&s.stats.cancelled==1&&s.source_bit(0)&&s.conserved(),"held squash lost source work");}
 // Fold SBUs remain at HOLD/path-only undo and clear only on actual raw update.
 {Service base(Mode::Overwrite,g);run(base,Kind::Append,1,1,1);run(base,Kind::Commit,1);size_t start;need(logical_width(base,"fold",&start)==200,"fold layout");
  for(unsigned bit=0;bit<200;++bit){Service s=base;bool before=s.logical_bit(start+bit);s.corrupt({start+bit});run(s,Kind::Hold);run(s,Kind::Undo,0,0,0);
   need(s.logical_bit(start+bit)!=before,"HOLD/path-only undo repaired dirty fold");run(s,Kind::Append,1,0,1);auto r=run(s,Kind::Read);
   for(unsigned w=0;w<21;++w){unsigned phi=0;for(unsigned age=0;age<g[w].length;++age)if(s.source_bit(age))phi^=1u<<(age%g[w].width);need(r.folds[w]==phi,"next source transition retained fold error");}}
 }
 // Every manifest bit is a real independent logical XOR, with no padding.
 {Service s(Mode::Overwrite,g,2,2);const auto count=s.bits();for(size_t id=0;id<count;++id){bool before=s.logical_bit(id);s.corrupt({id});need(s.logical_bit(id)!=before,"manifest flip missing");s.corrupt({id});need(s.logical_bit(id)==before,"logical flip not reversible");}}
 // Tiny effective counters exercise real drain/receiver-ACK before reuse.
 {Service s(Mode::Overwrite,g,2,2,1,2,2);
  for(unsigned i=0;i<100;++i){run(s,Kind::Read);if(s.wrap_waiting()){
    need(!s.accept(Kind::Read),"wrapped token reused before ACK");need(s.drained(),"wrap pending work");need(s.acknowledge_receiver_drained(),"receiver ACK refused");tick(s);++wraps;}}
  need(wraps>=30&&s.stats.wrap_completions==wraps&&s.conserved(),"token/epoch wrap gate");}
 // Two real intake/sampling ports preserve read-before-write and RAW order.
 for(unsigned L:{1u,2u}){
  Service s(Mode::Direct,g,L,L);auto old=s.accept(Kind::Read);auto append=s.accept(Kind::Append,1,1,1);
  need(bool(old)&&bool(append),"split ports did not accept concurrent work");tick(s);
  auto fresh=s.accept(Kind::Read);need(bool(fresh),"fresh read issue");unsigned received=0;
  for(unsigned i=0;i<30&&received<3;++i){if(auto r=s.take()){
   if(r->token==*old){for(auto v:r->folds)need(v==0,"old read overtaken by source write");need(r->path==0,"old path lost");}
   else if(r->token==*fresh){for(auto v:r->folds)need(v==1,"RAW query sampled stale source");need(r->path==1,"new path not visible");}
   else need(r->token==*append&&r->kind==Kind::Append,"unexpected split reply");++received;}tick(s);}
  need(received==3&&s.conserved(),"split work lost");need(s.retire(1),"retire port");
  need(bool(s.accept(Kind::Read))&&bool(s.accept(Kind::Append,1,0,0)),"retire serialized source/query intake");
  Service shared(Mode::Direct,g,L,L,1,16,16,Ports::SharedOne);need(bool(shared.accept(Kind::Read))&&!shared.accept(Kind::Append,1,0,0),"shared port sensitivity is not shared");
 }
 // A stalled old read prevents source advance from destroying its operands.
 {Service s(Mode::Direct,g,2,2);for(unsigned i=0;i<10;++i){need(bool(s.accept(Kind::Read)),"fill reads");tick(s);}
  auto append=s.accept(Kind::Append,1,1,1);need(bool(append),"source queue independent of full read queue");
  for(unsigned i=0;i<5;++i)tick(s);need(!s.source_bit(0)&&s.stats.ordering_stalls>0,"backpressured read lost source version");
  unsigned done=0;for(unsigned i=0;i<100&&done<11;++i){if(auto r=s.take()){if(r->kind==Kind::Read)for(auto v:r->folds)need(v==0,"blocked old read changed");++done;}tick(s);}
  need(done==11&&s.source_bit(0)&&s.conserved(),"ordering/response backpressure deadlock");}
 // Recurrent L2 uses actual registered low-word forwarding, not full-fold wait.
 {Service s(Mode::Recurrent,g,2,2);bp::RoundState ref;unsigned sent=0,done=0;uint64_t last=0;bool contiguous=true;
  for(unsigned i=0;i<300&&done<100;++i){if(auto r=s.take()){need(r->kind==Kind::Append,"source burst reply");if(done&&s.cycle()!=last+1)contiguous=false;last=s.cycle();++done;}
   if(sent<100){unsigned value=sent&1;if(s.accept(Kind::Append,1,value,value)){ref.updateGHist(0,value,1);setpath(ref,((ref.read_history_word(22).limb[0]<<1)|value)&65535);++sent;}}tick(s);}
  need(sent==100&&done==100&&contiguous&&s.stats.recurrent_low_forwards>0,"recurrent L2 forwarding throughput");compare_source(s,ref);
 }
 // Dependency gate: next source command is built from the actual prior reply.
 uint64_t dependent_cycles=0;
 {Service s(Mode::Overwrite,g,2,2);for(unsigned i=0;i<100;++i){auto r=run(s,Kind::Read);run(s,Kind::Append,1,r.folds[0]&1,r.path&1);while(!s.retire(1))tick(s);}dependent_cycles=s.cycle();need(dependent_cycles>300,"dependent stream assumed free latency");}
 std::cout<<"{\"status\":\"PASS_FINITE_SOURCE_COMPONENT_NOT_CPU_QUALIFICATION\",\"pinned_source_checks\":"<<source_checks
 <<",\"metadata_single_bits\":"<<metadata_bits<<",\"wrap_drains\":"<<wraps<<",\"dependent_cycles_100\":"<<dependent_cycles
 <<",\"independent_II1\":true,\"queue_full\":true,\"operand_sampling\":true,\"mid_stage_SEU\":true,\"accepted_source_preserved\":true}"<<'\n';
 return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
