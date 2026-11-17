#pragma once
#include "tage/history/lease.hpp"

namespace bp {

// A diagnostic for a caller-provided, coherent quiescent snapshot.
// A mismatch is evidence of inconsistency between the two representations.
class BankMismatchMonitor {
    std::array<uint8_t,7> scores_{};
    unsigned next_ = 0;
  public:
    struct Observation {
        unsigned bank; // Zero-based.
        bool mismatch;
        unsigned score;
    };

    Observation probe(TageAccess &core,
                      const std::vector<TageAccess::HistoryWord> &geometry) {
        const unsigned bank=next_;
        const auto folded=canonical_own_folds(core,geometry,1u<<bank);
        bool mismatch=false;
        for(unsigned w=3*bank;w<3*bank+3;++w)
            mismatch |= core.read_history_word(w)!=folded[w];
        auto &score=scores_[bank];
        if(mismatch && score<3) ++score;
        if(!mismatch && score>0) --score;
        next_=(bank+1)%scores_.size();
        return {bank,mismatch,score};
    }
};

} // namespace bp
