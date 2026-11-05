#pragma once
#ifdef BP_V5_CPU_CONTEXT
#include "../predictor/tage_access.hpp"
#else
#include "../predictor/tage_adapter.hpp"
#endif
#include <cmath>
#include <numeric>
#include <functional>

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
 std::vector<uint8_t> raw_ring;unsigned raw_head=0;
 unsigned direct_path=0,direct_pcbit=0;
 bool defer_journal=false;
 std::function<void(bool,unsigned,uint64_t,unsigned)> journal_enqueue;
 template<class Params> RepresentationAccess(const Params&p,const std::string&mode,unsigned budget):Parent(p),rep(representation(mode)),tap_budget(budget){}
 bool direct()const{return rep!=Representation::Recurrent;}
 void prepare_taps(){selected.resize(this->nHistoryTables+1);for(unsigned b=1;b<=this->nHistoryTables;++b)selected[b]=taps(this->histLengths[b],tap_budget,rep);raw_ring.assign(this->maxHist+1000,0);}
 void valid_head()const {if(raw_head>=raw_ring.size())throw std::runtime_error("FAIL_PROTOCOL invalid bounded history pointer");}
 bool ring_bit(unsigned age)const{valid_head();return raw_ring.at((raw_head+age)%raw_ring.size())&1;}
 bool source_bit(unsigned age)const{return direct()?ring_bit(age):bool(this->threadHistory[0].globalHist.at(this->threadHistory[0].ptGhist+age)&1);}
 void flip_ring(unsigned age){valid_head();raw_ring.at((raw_head+age)%raw_ring.size())^=1;}
 void apply_journal(bool undo,unsigned n,uint64_t bits,unsigned path){
  valid_head();
  if(undo){raw_head=(raw_head+n)%raw_ring.size();direct_path=path&65535;}
  else {for(unsigned j=0;j<n;++j){raw_head=(raw_head+raw_ring.size()-1)%raw_ring.size();raw_ring[raw_head]=(bits>>j)&1;}direct_path=((direct_path<<1)|(path&1))&65535;}
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
  const auto& positions=selected.at(bank);
  for(unsigned age:positions){
   // Direct is bit-exact pinned folding; sparse index and tags have
   // distinct fixed non-linear-in-age bit placement to avoid identical hashes.
   unsigned lane=age%width;
   if(rep!=Representation::Direct&&domain)lane=(age*(domain==1?3:5)+(age/width)*(domain==1?1:3)+domain)%width;
   if((direct()?ring_bit(age):(h.globalHist.at(h.ptGhist+age)&1)))out^=1u<<lane;
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
