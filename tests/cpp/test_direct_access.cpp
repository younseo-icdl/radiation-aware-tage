#include "tage/history/direct_access.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <iostream>

using namespace bp;
void check(bool value, const char *reason) {
    if (!value) throw std::runtime_error(reason);
}
int main() {
    try {
        gem5::TAGEBaseParams params;
        params.histBufferSize = 4096;
        DirectAccess<TageState> direct(params);
        direct.direct_queries = true;
        TageState rolling(params);
        std::mt19937_64 input(548);
        for (unsigned i = 0; i < 30000; ++i) {
            uint64_t pc = 0x4000+(input()%256)*4, target = pc+(input()%64)*4;
            bool conditional = i%11, taken = input()&1;
            auto *a = direct.makeBranchInfo(pc, conditional);
            auto *b = rolling.makeBranchInfo(pc, conditional);
            bool ap = direct.tagePredict(0, pc, conditional, a);
            bool bp = rolling.tagePredict(0, pc, conditional, b);
            check(ap == bp, "clean direct prediction");
            if (conditional) {
                for (unsigned bank = 1; bank <= 7; ++bank)
                    check(a->tableIndices[bank] == b->tableIndices[bank] &&
                          a->tableTags[bank] == b->tableTags[bank], "clean direct hashes");
                int draw = input()&3;
                direct.condBranchUpdate(0, pc, taken, a, draw, target, ap);
                rolling.condBranchUpdate(0, pc, taken, b, draw, target, bp);
            }
            direct.updateHistories(0, pc, false, taken, target, {}, a);
            rolling.updateHistories(0, pc, false, taken, target, {}, b);
            delete a; delete b;
        }
        check(direct.equal(rolling), "clean full learning/history state after rollovers");
        auto before = direct.save();
        DirectAccess<TageState> all_direct(params);all_direct.direct_queries=true;
        for(unsigned mask:{0u,3u,5u,64u,96u,127u}) {
            direct.load(before);direct.direct_queries=false;direct.direct_bank_mask=mask;
            for(unsigned w=0;w<21;++w) {
                Word corrupt;corrupt.limb[0]=input();direct.write_history_word(w,corrupt);
            }
            auto state=direct.save();rolling.load(state);all_direct.load(state);
            auto *h=direct.makeBranchInfo(0x4320,true);
            auto *r=rolling.makeBranchInfo(0x4320,true);
            auto *d=all_direct.makeBranchInfo(0x4320,true);
            direct.tagePredict(0,0x4320,true,h);rolling.tagePredict(0,0x4320,true,r);
            all_direct.tagePredict(0,0x4320,true,d);
            for(unsigned bank=1;bank<=7;++bank) {
                auto *expected=(mask>>(bank-1))&1 ? d:r;
                check(h->tableIndices[bank]==expected->tableIndices[bank] &&
                      h->tableTags[bank]==expected->tableTags[bank],"hybrid bank mask endpoint");
            }
            check(direct.save().folded==state.folded,"hybrid query must not repair storage");
            delete h;delete r;delete d;
        }
        direct.load(before);rolling.load(before);
        direct.direct_queries=true;direct.direct_bank_mask=0;
        auto word = direct.read_history_word(0); word.flip(0);
        direct.write_history_word(0, word);
        auto corrupt = direct.save();
        auto *a = direct.makeBranchInfo(0x4320, true);
        auto *b = rolling.makeBranchInfo(0x4320, true);
        check(direct.tagePredict(0, 0x4320, true, a) == rolling.tagePredict(0, 0x4320, true, b),
              "dead fold upset cannot change direct query");
        for (unsigned bank = 1; bank <= 7; ++bank)
            check(a->tableIndices[bank] == b->tableIndices[bank] &&
                  a->tableTags[bank] == b->tableTags[bank], "direct query ignores dead folds");
        check(direct.save().folded == corrupt.folded, "direct query must not repair stored folds");
        delete a; delete b;
        direct.load(before);
        auto raw = direct.read_history_word(21); raw.flip(0); direct.write_history_word(21, raw);
        check(direct.save().folded == before.folded, "raw event must not silently refold storage");
        bool changed = false;
        for (unsigned w = 0; w < 21; ++w)
            changed |= direct.direct_word(w) != before.folded[w];
        check(changed, "direct query must consume current faulty raw history");
        std::cout << "PASS direct query hashes/learning over 30k branches and rollovers; dead-fold isolation, no repair, raw sensitivity\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL " << e.what() << '\n'; return 1;
    }
}
