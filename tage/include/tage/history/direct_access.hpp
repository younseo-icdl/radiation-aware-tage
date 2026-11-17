#pragma once
#include "tage/predictor/tage_access.hpp"

namespace bp {
// Query-local direct folding: no writes, gold copy, or learned-table repair.
// Parent may retain dead rolling-fold fields for upstream software bookkeeping;
// these fields never supply a direct-mode index/tag and are not hardware storage.
template <class Parent> class DirectAccess : public Parent {
  public:
    using Parent::Parent;
    bool direct_queries = false;
    unsigned direct_word(unsigned word) const {
        if (word >= this->nHistoryTables*3)
            throw std::out_of_range("direct fold word");
        unsigned bank = word/3+1, kind = word%3;
        unsigned width = kind ? this->tagTableTagWidths[bank]-(kind-1)
                              : this->logTagTableSizes[bank];
        unsigned fold = 0;
        const auto &h = this->threadHistory[0];
        for (unsigned age = 0; age < this->histLengths[bank]; ++age)
            if (h.globalHist.at(h.ptGhist+age) & 1)
                fold ^= 1u << (age % width);
        return fold;
    }

  protected:
    int gindex(gem5::ThreadID tid, gem5::Addr pc, int bank) const override {
        if (!direct_queries) return Parent::gindex(tid, pc, bank);
        if (tid) throw std::invalid_argument("direct query single thread");
        unsigned shifted = pc >> this->instShiftAmt;
        unsigned hlen = std::min(unsigned(this->histLengths[bank]), this->pathHistBits);
        return (shifted ^ (shifted >> (std::abs(this->logTagTableSizes[bank]-bank)+1))
                ^ direct_word((bank-1)*3)
                ^ this->F(this->threadHistory[tid].pathHist, hlen, bank))
               & ((1u << this->logTagTableSizes[bank])-1);
    }
    uint16_t gtag(gem5::ThreadID tid, gem5::Addr pc, int bank) const override {
        if (!direct_queries) return Parent::gtag(tid, pc, bank);
        if (tid) throw std::invalid_argument("direct query single thread");
        return ((pc >> this->instShiftAmt) ^ direct_word((bank-1)*3+1)
                ^ (direct_word((bank-1)*3+2) << 1))
               & ((1u << this->tagTableTagWidths[bank])-1);
    }
};
} // namespace bp
