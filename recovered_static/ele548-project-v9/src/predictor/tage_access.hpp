#pragma once
#include "cpu/pred/tage_base.hh"
#include "../protection/word.hpp"
#include <random>
#include <stdexcept>
#include <algorithm>
#include <string>
#include <set>
#include <limits>
namespace bp {
using Base=gem5::branch_prediction::TAGEBase;
struct Site { unsigned kind,bank,row,bit,width; size_t id; };
inline const char* field_name(unsigned k) { static const char* n[]={"bimodal","ctr","tag","u","raw_path","folded"};return n[k]; }
inline int decode_signed(unsigned v,unsigned w){return (v&(1u<<(w-1)))?int(v)-int(1u<<w):int(v);}
class TageAccess : public Base {
 public:
 explicit TageAccess(const gem5::TAGEBaseParams& p):Base(p){}
 std::vector<Site> sites() const {
  std::vector<Site> v;auto add=[&](unsigned k,unsigned bank,unsigned rows,unsigned width){for(unsigned row=0;row<rows;++row)for(unsigned bit=0;bit<width;++bit)v.push_back({k,bank,row,bit,width,v.size()});};
  add(0,0,btablePrediction.size(),1);add(0,1,btableHysteresis.size(),1);
  for(unsigned b=1;b<=nHistoryTables;++b)add(1,b,1<<logTagTableSizes[b],tagTableCounterBits);
  for(unsigned b=1;b<=nHistoryTables;++b)add(2,b,1<<logTagTableSizes[b],tagTableTagWidths[b]);
  for(unsigned b=1;b<=nHistoryTables;++b)add(3,b,1<<logTagTableSizes[b],tagTableUBits);
  add(4,0,maxHist,1);add(4,1,1,pathHistBits);
  for(unsigned b=1;b<=nHistoryTables;++b){add(5,b,1,logTagTableSizes[b]);
   for(unsigned t=0;t<2;++t)for(unsigned bit=0;bit<tagTableTagWidths[b]-t;++bit)v.push_back({5,b,t+1,bit,tagTableTagWidths[b]-t,v.size()});}
  return v;
 }
 unsigned payload(const Site& s) const {
  const auto& h=threadHistory[0];
  switch(s.kind){
   case 0:return s.bank?btableHysteresis.at(s.row):btablePrediction.at(s.row);
   case 1:return unsigned(gtable[s.bank][s.row].ctr)&((1u<<s.width)-1);
   case 2:return gtable[s.bank][s.row].tag;
   case 3:return gtable[s.bank][s.row].u;
   case 4:return s.bank?unsigned(h.pathHist):h.globalHist.at(h.ptGhist+s.row);
   case 5:return s.row?h.computeTags[s.row-1][s.bank].comp:h.computeIndices[s.bank].comp;
  }throw std::invalid_argument("site kind");
 }
 void write_payload(const Site& s,unsigned val){
  val&=(1u<<s.width)-1;auto& h=threadHistory[0];
  switch(s.kind){
   case 0:if(s.bank)btableHysteresis.at(s.row)=val;else btablePrediction.at(s.row)=val;break;
   case 1:gtable[s.bank][s.row].ctr=decode_signed(val,s.width);break;
   case 2:gtable[s.bank][s.row].tag=val;break;
   case 3:gtable[s.bank][s.row].u=val;break;
   case 4:if(s.bank)h.pathHist=val;else h.globalHist.at(h.ptGhist+s.row)=val;break;
   case 5:if(s.row)h.computeTags[s.row-1][s.bank].comp=val;else h.computeIndices[s.bank].comp=val;break;
   default:throw std::invalid_argument("site kind");
  }
 }
 std::vector<unsigned> bits() const {std::vector<unsigned> v;for(const auto& s:sites())v.push_back((payload(s)>>s.bit)&1u);return v;}
 void corrupt(const std::vector<size_t>& ids){
  auto v=sites();std::set<size_t> unique;
  for(auto id:ids)if(id>=v.size()||!unique.insert(id).second)throw std::invalid_argument("invalid/duplicate site");
  // Validate whole event before mutation. Each unique logical bit XORs once.
  for(auto id:ids){const auto& s=v[id];write_payload(s,payload(s)^(1u<<s.bit));}
 }
 struct HistoryWord {std::string id;unsigned kind,bank,row,width;std::vector<size_t> sites;};
 std::vector<HistoryWord> history_words()const {
  std::vector<HistoryWord> out;
  auto all=sites();
  for(unsigned b=1;b<=nHistoryTables;++b)for(unsigned row=0;row<3;++row){
   HistoryWord w{"folded:"+std::to_string(b)+":"+std::to_string(row),5,b,row,row?tagTableTagWidths[b]-(row-1):unsigned(logTagTableSizes[b]),{}};
   for(auto& s:all)if(s.kind==5&&s.bank==b&&s.row==row)w.sites.push_back(s.id);
   out.push_back(w);
  }
  for(unsigned b=0;b<2;++b){HistoryWord w{"raw_path:"+std::to_string(b),4,b,0,b?pathHistBits:maxHist,{}};
   for(auto& s:all)if(s.kind==4&&s.bank==b)w.sites.push_back(s.id);
   out.push_back(w);}
  return out;
 }
 Word read_history_word(unsigned index)const {
  const auto& h=threadHistory[0];Word value;
  if(index<nHistoryTables*3){unsigned bank=index/3+1,row=index%3;value.limb[0]=row?h.computeTags[row-1][bank].comp:h.computeIndices[bank].comp;}
  else if(index==nHistoryTables*3){for(unsigned i=0;i<maxHist;++i)value.set(i,h.globalHist.at(h.ptGhist+i)&1);}
  else if(index==nHistoryTables*3+1)value.limb[0]=h.pathHist;
  else throw std::out_of_range("history word");
  return value;
 }
 void write_history_word(unsigned index,const Word& value){
  auto& h=threadHistory[0];
  if(index<nHistoryTables*3){unsigned bank=index/3+1,row=index%3,width=row?tagTableTagWidths[bank]-(row-1):logTagTableSizes[bank];unsigned v=value.limb[0]&((1u<<width)-1);
   if(row)h.computeTags[row-1][bank].comp=v;else h.computeIndices[bank].comp=v;}
  else if(index==nHistoryTables*3){for(unsigned i=0;i<maxHist;++i)h.globalHist.at(h.ptGhist+i)=value.bit(i);}
  else if(index==nHistoryTables*3+1)h.pathHist=value.limb[0]&((1u<<pathHistBits)-1);
  else throw std::out_of_range("history word");
 }
 void reset_selected_history(){for(unsigned i=0;i<nHistoryTables*3+2;++i)write_history_word(i,Word{});threadHistory[0].nonSpecPathHist=0;}
 void tagged_enabled(bool enabled){for(unsigned i=1;i<=nHistoryTables;++i)noSkip[i]=enabled;}
 void fallback_update(uint64_t pc,bool actual,Base::BranchInfo* bi,int nrand){baseUpdate(pc,actual,bi);handleAllocAndUReset(false,actual,bi,nrand);}
 unsigned history_depth()const{return maxHist;}
};
}
