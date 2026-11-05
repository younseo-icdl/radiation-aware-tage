#pragma once
#include <cassert>
#include <cstdint>
#include <stdexcept>
#include <utility>

namespace bp::v11 {
// Functional implementation only. No injector, golden source, dirty hint or
// BranchInfo saved fold is consulted. The timing/ports for this full reduction
// are NOT modelled by synchronous C++ callbacks.
template<class Parent> class OverwriteAccess : public Parent {
 public:
  struct Activity {
    uint64_t forward_calls=0, undo_calls=0, source_bits_sampled=0;
    uint64_t fold_tap_terms=0, fold_bit_writes=0, fold_word_writes=0;
    uint64_t lookup_calls=0, lookup_fold_word_reads=0, rollovers=0;
  };
  Activity activity{}; // software observation, not implemented hardware storage

  template<class... Args>
  explicit OverwriteAccess(Args&&... args):Parent(std::forward<Args>(args)...) {}

  unsigned source_fold(gem5::ThreadID tid,unsigned bank,unsigned width) const {
    const auto& h=this->threadHistory.at(tid);
    unsigned value=0;
    for(unsigned age=0;age<unsigned(this->histLengths[bank]);++age)
      if(h.globalHist.at(h.ptGhist+age)&1) value^=1u<<(age%width);
    return value;
  }

  // Externally issued history transition samples only actual current source.
  // One source snapshot fans out to the21 reductions; unique sampled bits and
  // XOR terms are separate counters. These counters are not PPA measurements.
  void publish_from_actual_source(gem5::ThreadID tid) {
    auto& h=this->threadHistory.at(tid);
    activity.source_bits_sampled+=this->maxHist;
    for(unsigned bank=1;bank<=this->nHistoryTables;++bank) {
      const unsigned widths[3]={unsigned(this->logTagTableSizes[bank]),
        this->tagTableTagWidths[bank],this->tagTableTagWidths[bank]-1};
      h.computeIndices[bank].comp=source_fold(tid,bank,widths[0]);
      h.computeTags[0][bank].comp=source_fold(tid,bank,widths[1]);
      h.computeTags[1][bank].comp=source_fold(tid,bank,widths[2]);
      activity.fold_tap_terms+=3*this->histLengths[bank];
      activity.fold_bit_writes+=widths[0]+widths[1]+widths[2];
      activity.fold_word_writes+=3;
    }
  }

  void observe_lookup(bool conditional) {
    ++activity.lookup_calls;
    if(conditional) activity.lookup_fold_word_reads+=3*this->nHistoryTables;
  }

  // Pinned TAGEBase raw-history rollover/append, with only its recurrent fold
  // updates replaced. Calling Parent::updateGHist and then overwriting would
  // accidentally execute both structures; this implementation does not.
  void updateGHist(gem5::ThreadID tid,uint64_t bits,uint8_t n) override {
    if(n==0) return;
    auto& h=this->threadHistory.at(tid);
    if(h.ptGhist<n) {
      constexpr int rollbackBuffer=1000;
      for(int i=0;i<int(this->maxHist)+rollbackBuffer;++i)
        h.globalHist[this->histBufferSize-this->maxHist-rollbackBuffer+i]=
          h.globalHist[h.ptGhist+i];
      h.ptGhist=this->histBufferSize-this->maxHist-rollbackBuffer;
      ++activity.rollovers;
    }
    for(unsigned i=0;i<n;++i) {
      --h.ptGhist;
      h.globalHist.at(h.ptGhist)=bits&1u;
      bits>>=1;
    }
    ++activity.forward_calls;
    publish_from_actual_source(tid);
  }

  // Same path restoration and source pointer rewind as pinned inverse undo.
  // The old/possibly upset fold and bi->ci/ct0/ct1 are never recovery operands.
  void restoreHistState(gem5::ThreadID tid,bp::Base::BranchInfo* bi) override {
    if(!this->speculativeHistUpdate||!bi->modified) return;
    auto& h=this->threadHistory.at(tid);
    h.pathHist=bi->pathHist;
    if(bi->nGhist==0) return;
    for(unsigned n=0;n<bi->nGhist;++n) {
      ++h.ptGhist;
      assert((h.ptGhist+this->maxHist)<h.globalHist.size());
    }
    bi->nGhist=0;
    bi->modified=false;
    ++activity.undo_calls;
    publish_from_actual_source(tid);
  }
};
} // namespace bp::v11
