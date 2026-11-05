#include "representation.hpp"
#include "batch_undo.hpp"
#include "../rate_state_v5_r5_support/finite_fifo.hpp"
#include <iostream>
using namespace bp;using namespace bp::v5;
void check(bool x,const char*s){if(!x)throw std::runtime_error(s);}
Word packet(bool undo,unsigned n,uint64_t bits,unsigned path){Word w;w.set(0,undo);for(unsigned j=0;j<10;++j)w.set(1+j,(n>>j)&1);for(unsigned j=0;j<2;++j)w.set(11+j,(bits>>j)&1);for(unsigned j=0;j<16;++j)w.set(13+j,(path>>j)&1);w.set(29,true);return w;}
void apply(State&s,const Word&w){unsigned n=0,path=0;uint64_t bits=0;for(unsigned j=0;j<10;++j)n|=unsigned(w.bit(1+j))<<j;for(unsigned j=0;j<2;++j)bits|=uint64_t(w.bit(11+j))<<j;for(unsigned j=0;j<16;++j)path|=unsigned(w.bit(13+j))<<j;s.apply_journal(w.bit(0),n,bits,path);}
int main(){try{
 State a("direct",8,true),b("direct",8,true);FiniteRmwQueue q(30,64,1,1);UndoBatch batch;
 b.defer_journal=true;b.journal_enqueue=[&](bool undo,unsigned n,uint64_t bits,unsigned path){if(undo&&batch.add(n,path))return;if(!undo&&batch.active())if(auto reduced=batch.take()){q.push(packet(true,reduced->count,0,reduced->path));if(q.can_start())q.start(2);}q.push(packet(undo,n,bits,path));if(q.can_start())q.start(undo?2:1);};
 auto drain=[&]{while(q.count()){if(auto w=q.tick())apply(b,*w);if(q.can_start())q.start(q.peek().bit(0)?2:1);}};
 for(unsigned round=0;round<2000;++round){std::vector<Base::BranchInfo*>aa,bb;
  for(unsigned j=0;j<32;++j){uint64_t pc=0x100+((round*11+j*3)%512);bool cond=(round+j)%7;
   auto*x=a.makeBranchInfo(pc,cond);auto*y=b.makeBranchInfo(pc,cond);check(a.tagePredict(0,pc,cond,x)==b.tagePredict(0,pc,cond,y),"batch clean prediction");
   a.updateHistories(0,pc,true,j&1,0,{},x);b.updateHistories(0,pc,true,j&1,0,{},y);drain();check(a.hashes()==b.hashes(),"append completion");aa.push_back(x);bb.push_back(y);
  }
  auto before=b.raw_head;batch.begin();for(unsigned j=31;j>0;--j){a.restoreHistState(0,aa[j]);b.restoreHistState(0,bb[j]);delete aa[j];delete bb[j];}
  check(b.raw_head==before,"undo result published before batch service");auto merged=batch.finish();check(merged&&merged->count==31&&merged->operations==31,"squash cardinality");
  q.push(packet(true,merged->count,0,merged->path));q.start(2);
  check(!q.tick()&&b.raw_head==before,"L2 undo published after only one cycle");
  // Same physical journal cell is hit while the batch is in flight. The
  // command carries head/path only, so it must not overwrite the upset.
  if(round==0){b.flip_ring(100);a.flip_ring(69);q.flip(q.bits()-q.depth*(q.width+q.payload_check_bits())+((q.accepted-1)%q.depth)*(q.width+q.payload_check_bits()));}
  auto done=q.tick();check(bool(done),"L2 undo never completed");apply(b,*done);
  check(a.hashes()==b.hashes()&&a.direct_path==b.direct_path,"coalesced undo source mismatch");check(q.conserved(),"batch conservation");
  delete aa[0];delete bb[0];
 }
 // The actual resolved-branch overload nests the younger-branch squash.
 batch.begin();batch.begin();a.apply_journal(true,7,0,55);b.journal_enqueue(true,7,0,55);
 check(!batch.finish(),"inner boundary prematurely published");a.apply_journal(true,1,0,33);b.journal_enqueue(true,1,0,33);
 a.apply_journal(false,1,1,1);b.journal_enqueue(false,1,1,1);check(!batch.finish(),"outer boundary double-published flushed packet");
 check(q.count()==2,"nested undo did not flush once before corrected append");drain();check(a.hashes()==b.hashes()&&a.direct_path==b.direct_path,"nested recovery packet order");
 check(q.corrected()==1,"queue SBU was not corrected at consumption");
 bool reject=false;try{batch.begin();batch.add(1001,0);}catch(const std::overflow_error&){reject=true;}check(reject,"unbounded undo accepted");
 std::cout<<"PASS bounded BPU undo reduction, odd-PC speculative reads, one L2 batch for31undos, completion-only publication, retained mid-service raw upset and queue SBU, finite conservation\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
