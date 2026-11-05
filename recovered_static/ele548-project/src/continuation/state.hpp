#pragma once
#include "history_access.hpp"
#include "../predictor/tage_adapter.hpp"
namespace bp {
class ContinuationState : public ContinuationAccess {
 public:
 explicit ContinuationState(const gem5::TAGEBaseParams& p={}) : ContinuationAccess(p) {init();}
 ContinuationState(const ContinuationState&)=delete; ContinuationState& operator=(const ContinuationState&)=delete;
 ~ContinuationState() override {
  for(unsigned i=1;i<=nHistoryTables;++i)delete[] gtable[i];
  delete[] gtable;
  for(auto& h:threadHistory){delete[] h.computeIndices;delete[] h.computeTags[0];delete[] h.computeTags[1];}
  delete[] histLengths;delete[] tableIndices;delete[] tableTags;
 }
 using Snapshot=TageState::Snapshot;
 Snapshot save() const {
  Snapshot s;s.pred=btablePrediction;s.hyst=btableHysteresis;s.tables.resize(nHistoryTables+1);
  for(unsigned b=1;b<=nHistoryTables;++b)s.tables[b].assign(gtable[b],gtable[b]+(1<<logTagTableSizes[b]));
  const auto& h=threadHistory[0];s.global=h.globalHist;s.pointer=h.ptGhist;s.path=h.pathHist;s.non_spec=h.nonSpecPathHist;s.aging=tCounter;s.alt=useAltPredForNewlyAllocated;
  for(unsigned b=1;b<=nHistoryTables;++b){s.folded.push_back(h.computeIndices[b].comp);s.folded.push_back(h.computeTags[0][b].comp);s.folded.push_back(h.computeTags[1][b].comp);}return s;
 }
 void load(const Snapshot& s){
  if(s.pred.size()!=btablePrediction.size()||s.global.size()!=histBufferSize||s.tables.size()!=nHistoryTables+1||s.folded.size()!=nHistoryTables*3)throw std::invalid_argument("snapshot geometry");
  btablePrediction=s.pred;btableHysteresis=s.hyst;
  for(unsigned b=1;b<=nHistoryTables;++b){if(s.tables[b].size()!=size_t(1<<logTagTableSizes[b]))throw std::invalid_argument("snapshot table");std::copy(s.tables[b].begin(),s.tables[b].end(),gtable[b]);}
  auto& h=threadHistory[0];h.globalHist=s.global;h.ptGhist=s.pointer;h.pathHist=s.path;h.nonSpecPathHist=s.non_spec;tCounter=s.aging;useAltPredForNewlyAllocated=s.alt;
  for(unsigned b=1;b<=nHistoryTables;++b){h.computeIndices[b].comp=s.folded[(b-1)*3];h.computeTags[0][b].comp=s.folded[(b-1)*3+1];h.computeTags[1][b].comp=s.folded[(b-1)*3+2];}
 }
 bool equal(const ContinuationState& other) const {
  auto a=save(),b=other.save();if(a.pred!=b.pred||a.hyst!=b.hyst||a.global!=b.global||a.pointer!=b.pointer||a.path!=b.path||a.non_spec!=b.non_spec||a.aging!=b.aging||a.alt!=b.alt||a.folded!=b.folded)return false;
  for(unsigned bank=1;bank<=nHistoryTables;++bank)for(size_t r=0;r<a.tables[bank].size();++r){auto x=a.tables[bank][r],y=b.tables[bank][r];if(x.ctr!=y.ctr||x.tag!=y.tag||x.u!=y.u)return false;}
  return true;
 }
};
}
