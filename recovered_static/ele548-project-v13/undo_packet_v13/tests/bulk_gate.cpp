#define main inherited_service_gate_main
#include "service_gate.cpp"
#undef main
int main(){try{
 auto g=geometry();unsigned checked=0,stage_flips=0;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  Service base(mode,g,L,L);std::mt19937_64 rng(0x13b011);
  for(unsigned i=0;i<500;++i)run(base,Kind::Append,2,rng()&3,rng()&1);
  for(unsigned trial=0;trial<20;++trial){
   const unsigned ns[]={0,1,2,3,7,31,130,511,999,1000};unsigned n=trial<10?ns[trial]:rng()%1001,path=rng()&65535;
   Service jump=base;
   std::vector<size_t> faults{size_t(rng()%1130),size_t(1130+rng()%16)};
   if(mode!=Mode::Direct){size_t fold;logical_width(jump,"fold",&fold);faults.push_back(fold+rng()%200);}
   jump.corrupt(faults);Service seq=jump;run(jump,Kind::Undo,n,0,path);
   for(unsigned i=0;i<n;++i)run(seq,Kind::Undo,1,0,path);
   if(!n)run(seq,Kind::Undo,0,0,path);
   auto a=run(jump,Kind::Read),b=run(seq,Kind::Read);
   need(a.folds==b.folds&&a.path==b.path,"coalesced dirty inverse differs from sequential");
   for(unsigned age=0;age<130;++age)need(jump.source_bit(age)==seq.source_bit(age),"coalesced source window mismatch");
   need(jump.source_depth()==1000-n&&seq.source_depth()==1000-n&&jump.conserved(),"bulk credit mismatch");++checked;
  }
  // A packet counts as one accepted transaction, not n phantom queue entries.
  Service s=base;s.tick();auto t=s.accept(Kind::Undo,1000,0,17);need(bool(t),"1000-bit packet admission");
  auto read=s.accept(Kind::Read);need(bool(read),"dependent read queued");s.cancel_reads();unsigned acks=0;
  for(unsigned i=0;i<30;++i){tick(s);if(auto r=s.take()){need(r->token==*t&&r->kind==Kind::Undo,"cancel changed accepted undo packet");++acks;}}
  need(acks==1&&s.stats.bulk_undos==1&&s.stats.bulk_bits==1000&&s.stats.cancelled==1&&s.source_depth()==0&&s.conserved(),"packet loss/cancel/depth");
 }
 // Operand sampling occurs at dispatch, never at response completion.
 for(unsigned L:{1u,2u}){
  Service s(Mode::Recurrent,g,L,L);for(unsigned i=0;i<20;++i)run(s,Kind::Append,1,i&1,0);
  auto t=s.accept(Kind::Undo,10,0,0);need(bool(t),"sample setup");tick(s); // actual pre/post windows and fold operands now latched
  Service control=s;s.corrupt({s.active_raw_site(0)});
  for(unsigned i=0;i<6;++i){tick(s);tick(control);}
  auto r=s.take(t),c=control.take(t);need(r&&c,"sample completion");
  need(run(s,Kind::Read).folds==run(control,Kind::Read).folds,"completion resampled damaged source");
  need(s.source_bit(0)!=control.source_bit(0),"source SEU was healed by jump");
 }
 // Every actual before/post/fold and stage-partial latch SBU can affect output.
 for(unsigned stage:{0u,1u}){
  Service initial(Mode::Recurrent,g,2,2);for(unsigned i=0;i<20;++i)run(initial,Kind::Append,1,i&1,0);
  auto t=initial.accept(Kind::Undo,10,0,0);tick(initial);if(stage)tick(initial);
  size_t at;auto width=logical_width(initial,"update_payload_"+std::to_string(stage),&at);
  std::vector<unsigned> offsets;
  if(!stage){for(unsigned i=0;i<200;++i)offsets.push_back(i);for(unsigned i=216;i<476;++i)offsets.push_back(i);}
  else {for(unsigned i=476;i<876;++i)offsets.push_back(i);}
  Service reference=initial;for(unsigned i=0;i<6;++i)tick(reference);need(bool(reference.take(t)),"stage reference");auto correct=run(reference,Kind::Read).folds;
  for(auto bit:offsets){need(bit<width,"manifest stage width");Service s=initial;s.corrupt({at+bit});for(unsigned i=0;i<6;++i)tick(s);need(bool(s.take(t)),"stage damaged completion");need(run(s,Kind::Read).folds!=correct,"live stage SBU secretly repaired or excluded");++stage_flips;}
 }
 // Expanded count bits are physical and protected, including both copies.
 {Service s(Mode::Recurrent,g,2,2);for(unsigned i=0;i<40;++i)run(s,Kind::Append,1,i&1,0);tick(s);auto t=s.accept(Kind::Undo,31,0,0);need(bool(t),"count setup");
  size_t at;logical_width(s,"command_metadata_0",&at);
  // Locate the populated entry by the actual valid data bit, not host expected count.
  for(unsigned i=0;i<4;++i){size_t p;logical_width(s,"command_metadata_"+std::to_string(i),&p);if(s.logical_bit(p)){at=p;break;}}
  for(unsigned bit=36;bit<46;++bit){Service d=s;d.corrupt({at+bit});tick(d);for(unsigned i=0;i<8;++i)tick(d);need(bool(d.take(t))&&d.source_depth()==9&&d.stats.metadata_repairs==s.stats.metadata_repairs+1,"10-bit count correction");}
 }
 std::cout<<"{\"status\":\"PASS_STAGED_BULK_UNDO_COMPONENT_NOT_CPU\",\"dirty_coalesced_sequential_pairs\":"<<checked<<",\"live_stage_SBU\":"<<stage_flips<<",\"max_undo\":1000,\"event_seed\":\"none; explicit fixture sites\",\"fixture_seed\":\"0x13b011\"}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
