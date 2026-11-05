#pragma once
#ifdef BP_V5_CPU_CONTEXT
#include "../predictor/tage_access.hpp"
#else
#include "../predictor/tage_adapter.hpp"
#endif
#include <cmath>
#include <numeric>
#include <functional>
#include <limits>
#include "../rate_pipeline_v9/mirror_secded.hpp"

namespace bp::v5 {
// Shared executable specification. No oracle, event schedule, or gold state.
enum class Representation { Recurrent, Direct, Geometric, Stratum };
inline Representation representation(const std::string& n) {
 if(n=="recurrent"||n=="short32")return Representation::Recurrent;
 if(n=="direct")return Representation::Direct;
 if(n=="geometric")return Representation::Geometric;
 if(n=="stratum")return Representation::Stratum;
 throw std::invalid_argument("unknown history representation");
}
inline std::vector<unsigned> taps(unsigned length,unsigned budget,Representation kind){
 unsigned count=std::min(length,budget);std::set<unsigned> positions;
 if(kind==Representation::Direct||kind==Representation::Recurrent){for(unsigned a=0;a<length;++a)positions.insert(a);}
 else {
  for(unsigned i=0;i<count;++i){
   unsigned a=kind==Representation::Geometric?unsigned(std::llround(std::expm1(std::log(double(length))*i/std::max(1u,count-1)))):
       unsigned((uint64_t(2*i+1)*length)/(2*count));
   positions.insert(std::min(length-1,a));
  }
  // Deterministic fill for rounded duplicate taps; no workload/fault tuning.
  for(unsigned a=0;positions.size()<count;++a)positions.insert(a);
 }
 return {positions.begin(),positions.end()};
}
template<class Parent> class RepresentationAccess:public Parent {
 public:
 Representation rep;unsigned tap_budget;
 std::vector<std::vector<unsigned>> selected;
 // Bounded hardware-like raw journal: max-history plus 1000 rollback entries,
 // matching the pinned implementation's declared rollback retention window.
 // The large upstream vector remains a simulator helper, never a gold copy.
 std::vector<uint8_t> raw_ring;mutable unsigned raw_head=0;
 // Primary raw_head11 keeps its old logical IDs. Only the two real stored
 // copies/checks below can repair it. Absolute service/hold clocks are trusted
 // scheduler tags, explicitly excluded as in the transport timing model.
 mutable uint16_t raw_head_check=0;
 mutable bp::v9::MirrorCell raw_head_mirror{};
 mutable bp::v9::MirrorSecded raw_head_code{11};
 mutable uint64_t source_cycle=0,source_hold_until=0;
 mutable uint64_t head_corrected=0,head_due_recovered=0,head_uncorrectable=0;
 mutable uint64_t head_redundancy_repairs=0,head_error_holds=0;
 struct SourceSnapshot {
  std::vector<uint8_t> ring;unsigned head,path,pcbit;uint16_t check;
  bp::v9::MirrorCell mirror;uint64_t cycle,hold_until,corrected,due_recovered,uncorrectable,repairs,holds;
 };
 SourceSnapshot source_save()const{return {raw_ring,raw_head,direct_path,direct_pcbit,raw_head_check,
  raw_head_mirror,source_cycle,source_hold_until,head_corrected,head_due_recovered,
  head_uncorrectable,head_redundancy_repairs,head_error_holds};}
 void source_restore(const SourceSnapshot&s){
  if(s.ring.size()!=raw_ring.size())throw std::invalid_argument("source snapshot geometry");
  raw_ring=s.ring;raw_head=s.head;direct_path=s.path;direct_pcbit=s.pcbit;raw_head_check=s.check;
  raw_head_mirror=s.mirror;source_cycle=s.cycle;source_hold_until=s.hold_until;
  head_corrected=s.corrected;head_due_recovered=s.due_recovered;head_uncorrectable=s.uncorrectable;
  head_redundancy_repairs=s.repairs;head_error_holds=s.holds;
 }
 unsigned direct_path=0,direct_pcbit=0;
 bool defer_journal=false;
 std::function<void(bool,unsigned,uint64_t,unsigned)> journal_enqueue;
 template<class Params> RepresentationAccess(const Params&p,const std::string&mode,unsigned budget):Parent(p),rep(representation(mode)),tap_budget(budget){}
 bool direct()const{return rep!=Representation::Recurrent;}
 void prepare_taps(){selected.resize(this->nHistoryTables+1);for(unsigned b=1;b<=this->nHistoryTables;++b)selected[b]=taps(this->histLengths[b],tap_budget,rep);raw_ring.assign(this->maxHist+1000,0);store_head(0);}
 void source_set_cycle(uint64_t cycle)const {source_cycle=cycle;}
 bool source_blocked()const{return source_cycle<source_hold_until;}
 bool source_poll(uint64_t cycle)const {
  source_set_cycle(cycle);if(!direct())return true;
  bp::v9::MirrorCell primary;primary.data.limb[0]=raw_head;primary.check=raw_head_check;
  try{
   const auto r=raw_head_code.decode(primary,raw_head_mirror);
   raw_head=unsigned(r.data.limb[0]);raw_head_check=primary.check;
   if(r.repaired){++head_corrected;++head_redundancy_repairs;head_due_recovered+=r.due_copies;
    if(cycle==std::numeric_limits<uint64_t>::max())throw std::overflow_error("source repair deadline overflow");
    source_hold_until=std::max(source_hold_until,cycle+1);++head_error_holds;
   }
  }catch(const bp::v9::MirrorUncorrectable&){++head_uncorrectable;throw;}
  if(raw_head>=raw_ring.size()){++head_uncorrectable;throw bp::v9::MirrorUncorrectable("valid source copies encode out-of-range head");}
  return !source_blocked();
 }
 bool source_ready(uint64_t cycle)const{return source_poll(cycle);}
 void valid_head()const {(void)source_poll(source_cycle);}
 void store_head(unsigned value)const {
  if(value>=raw_ring.size()||value>=2048)throw std::invalid_argument("source head store range");
  bp::Word word;word.limb[0]=value;bp::v9::MirrorCell primary;
  raw_head_code.store(primary,raw_head_mirror,word);raw_head=value;raw_head_check=primary.check;
 }
 bool head_bit(unsigned bit)const {if(bit>=11)throw std::out_of_range("source head bit");return (raw_head>>bit)&1;}
 void flip_head(unsigned bit){if(bit>=11)throw std::out_of_range("source head bit");raw_head^=1u<<bit;}
 size_t head_extra_bits()const{return 21;}
 bool head_extra_bit(size_t bit)const {
  if(bit>=head_extra_bits())throw std::out_of_range("source head extra bit");
  if(bit<5)return (raw_head_check>>bit)&1;
  if(bit<16)return raw_head_mirror.data.bit(bit-5);
  return (raw_head_mirror.check>>(bit-16))&1;
 }
 void flip_head_extra(size_t bit){
  if(bit>=head_extra_bits())throw std::out_of_range("source head extra bit");
  if(bit<5)raw_head_check^=uint16_t(1u<<bit);
  else if(bit<16)raw_head_mirror.data.flip(bit-5);
  else raw_head_mirror.check^=uint16_t(1u<<(bit-16));
 }
 // Diagnostics read actual storage without invoking any correcting accessor.
 // A corrupt head is mapped modulo physical storage only for observation;
 // this mapping is not a production eligibility or recovery decision.
 bool diagnostic_ring_bit(unsigned age)const{return raw_ring.at((uint64_t(raw_head)+age)%raw_ring.size())&1;}
 unsigned diagnostic_history_fold(unsigned bank,unsigned width,unsigned domain=0)const{
  unsigned out=0;for(unsigned age:selected.at(bank)){
   unsigned lane=age%width;
   if(rep!=Representation::Direct&&domain)lane=(age*(domain==1?3:5)+(age/width)*(domain==1?1:3)+domain)%width;
   if(diagnostic_ring_bit(age))out^=1u<<lane;
  }return out;
 }
 bool ring_bit(unsigned age)const{valid_head();return raw_ring.at((raw_head+age)%raw_ring.size())&1;}
 bool source_bit(unsigned age)const{return direct()?ring_bit(age):bool(this->threadHistory[0].globalHist.at(this->threadHistory[0].ptGhist+age)&1);}
 void flip_ring(unsigned age){valid_head();raw_ring.at((raw_head+age)%raw_ring.size())^=1;}
 void apply_journal(bool undo,unsigned n,uint64_t bits,unsigned path){
  valid_head();
  if(undo){store_head((raw_head+n)%raw_ring.size());direct_path=path&65535;}
  else {for(unsigned j=0;j<n;++j){store_head((raw_head+raw_ring.size()-1)%raw_ring.size());raw_ring[raw_head]=(bits>>j)&1;}direct_path=((direct_path<<1)|(path&1))&65535;}
 }
 void updateGHist(gem5::ThreadID tid,uint64_t bits,uint8_t n)override{
  Parent::updateGHist(tid,bits,n);
  if(!direct())return;valid_head();
  if(defer_journal)journal_enqueue(false,n,bits,direct_pcbit);else apply_journal(false,n,bits,direct_pcbit);
 }
 void restoreHistState(gem5::ThreadID tid,Base::BranchInfo*bi)override{
  if(direct()&&bi->modified){if(defer_journal)journal_enqueue(true,bi->nGhist,0,bi->pathHist);else apply_journal(true,bi->nGhist,0,bi->pathHist);}
  Parent::restoreHistState(tid,bi);
 }
 void recordHistState(gem5::ThreadID tid,Base::BranchInfo*bi)override{
  Parent::recordHistState(tid,bi);if(direct())bi->pathHist=direct_path;
 }
 void updatePathAndGlobalHistory(gem5::ThreadID tid,int brtype,bool taken,gem5::Addr pc,gem5::Addr target,Base::BranchInfo*bi)override{
  direct_pcbit=(pc>>this->instShiftAmt)&1;
  Parent::updatePathAndGlobalHistory(tid,brtype,taken,pc,target,bi);
 }
 unsigned history_fold(unsigned tid,unsigned bank,unsigned width,unsigned domain=0)const{
  const auto&h=this->threadHistory[tid];unsigned out=0;
  // One real head check precedes this non-yielding combinational fold read.
  // There is no event/dirty hint and no fault can interleave its individual taps.
  if(direct())valid_head();
  const auto& positions=selected.at(bank);
  for(unsigned age:positions){
   // Direct is bit-exact pinned folding; sparse index and tags have
   // distinct fixed non-linear-in-age bit placement to avoid identical hashes.
   unsigned lane=age%width;
   if(rep!=Representation::Direct&&domain)lane=(age*(domain==1?3:5)+(age/width)*(domain==1?1:3)+domain)%width;
   if((direct()?(raw_ring.at((raw_head+age)%raw_ring.size())&1):(h.globalHist.at(h.ptGhist+age)&1)))out^=1u<<lane;
  }return out;
 }
 int gindex(gem5::ThreadID tid,gem5::Addr pc,int bank)const override{
  if(!direct())return Parent::gindex(tid,pc,bank);
  unsigned p=pc>>this->instShiftAmt;
  unsigned hlen=std::min(this->histLengths[bank],int(this->pathHistBits));
  return (p^(p>>(std::abs(this->logTagTableSizes[bank]-bank)+1))^
      history_fold(tid,bank,this->logTagTableSizes[bank])^
      this->F(direct_path,hlen,bank))&((1u<<this->logTagTableSizes[bank])-1);
 }
 uint16_t gtag(gem5::ThreadID tid,gem5::Addr pc,int bank)const override{
  if(!direct())return Parent::gtag(tid,pc,bank);
  return ((pc>>this->instShiftAmt)^history_fold(tid,bank,this->tagTableTagWidths[bank],1)^
       (history_fold(tid,bank,this->tagTableTagWidths[bank]-1,2)<<1))&((1u<<this->tagTableTagWidths[bank])-1);
 }
 unsigned hash_mismatch()const{
  unsigned n=0;auto&h=this->threadHistory[0];
  for(unsigned b=1;b<=this->nHistoryTables;++b){
   n+=h.computeIndices[b].comp!=history_fold(0,b,this->logTagTableSizes[b]);
   n+=h.computeTags[0][b].comp!=history_fold(0,b,this->tagTableTagWidths[b],1);
   n+=h.computeTags[1][b].comp!=history_fold(0,b,this->tagTableTagWidths[b]-1,2);
  }return n;
 }
 auto hashes()const{
  std::vector<unsigned> v;auto&h=this->threadHistory[0];
  for(unsigned b=1;b<=this->nHistoryTables;++b){
   v.push_back(direct()?history_fold(0,b,this->logTagTableSizes[b]):h.computeIndices[b].comp);
   v.push_back(direct()?history_fold(0,b,this->tagTableTagWidths[b],1):h.computeTags[0][b].comp);
   v.push_back(direct()?history_fold(0,b,this->tagTableTagWidths[b]-1,2):h.computeTags[1][b].comp);
  }return v;
 }
 unsigned read_demands()const {unsigned n=0;for(unsigned b=1;b<selected.size();++b)n+=selected[b].size();return n;}
};
#ifndef BP_V5_CPU_CONTEXT
class State:public RepresentationAccess<TageState>{
 public:
 explicit State(const std::string&mode="recurrent",unsigned budget=8,bool spec=false):RepresentationAccess<TageState>(params(mode,spec),mode,budget){prepare_taps();}
 static gem5::TAGEBaseParams params(const std::string&mode,bool spec){gem5::TAGEBaseParams p;p.speculativeHistUpdate=spec;if(mode=="short32"){p.minHist=2;p.maxHist=32;}return p;}
 void corrupt(const std::vector<size_t>&ids){
  if(!direct()){TageState::corrupt(ids);return;}auto ss=this->sites();
  for(auto id:ids){const auto&s=ss.at(id);if(s.kind==5)throw std::invalid_argument("removed fold site is not exposed");}
  for(auto id:ids){const auto&s=ss.at(id);if(s.kind==4&&s.bank==0)flip_ring(s.row);else if(s.kind==4&&s.bank==1){direct_path^=1u<<s.bit;TageState::corrupt({id});}else TageState::corrupt({id});}
 }
};
class Adapter {
 public:
 State core;std::mt19937_64 rng{548};
 explicit Adapter(const std::string&mode="recurrent",unsigned taps=8):core(mode,taps){}
 template<class Observer> bool step(const Branch&b,Observer observe){
  auto*bi=core.makeBranchInfo(b.pc,b.conditional);bool pred=core.tagePredict(0,b.pc,b.conditional,bi);observe(*bi);
  int nrand=int(rng()%std::numeric_limits<int>::max())&3;
  if(b.conditional)core.condBranchUpdate(0,b.pc,b.taken,bi,nrand,b.target,pred);
  core.updateHistories(0,b.pc,false,b.taken,b.target,{},bi);delete bi;return pred;
 }
 bool step(const Branch&b){return step(b,[](const Base::BranchInfo&){});}
};
#endif
}
