#include "tage/predictor/tage_adapter.hpp"
#include "tage/predictor/gshare_adapter.hpp"
#include <fstream>
#include <iostream>
#include <memory>
using namespace bp;
void require(bool ok, const char *msg) {
    if (!ok)
        throw std::runtime_error(msg);
}
int main() {
    try {
        std::mt19937_64 input(20261012);
        TageAdapter adapter;
        TageState reference;
        std::mt19937_64 reference_rng(548);
        for (unsigned i = 0; i < 150000; ++i) {
            Branch b{0x4000 + (input() % 128) * 4, 0x8000 + (input() % 128) * 4, bool(input() & 1),
                     bool(i % 11)};
            bool a = adapter.step(b);
            auto *bi = reference.makeBranchInfo(b.pc, b.conditional);
            bool z = reference.tagePredict(0, b.pc, b.conditional, bi);
            int nrand = int(reference_rng() % std::numeric_limits<int>::max()) & 3;
            if (b.conditional)
                reference.condBranchUpdate(0, b.pc, b.taken, bi, nrand, b.target, z);
            reference.updateHistories(0, b.pc, false, b.taken, b.target, {}, bi);
            delete bi;
            require(a == z, "TAGE no-fault direction");
            if (i % 4096 == 0)
                require(adapter.core.equal(reference), "TAGE no-fault complete state");
        }
        require(adapter.core.equal(reference), "TAGE final state");
        std::cout << "PASS TAGE 150000 direct-upstream differential branches, full state, "
                     "allocation RNG and periodic u aging\n";
        auto s = adapter.snapshot();
        TageAdapter clone;
        clone.restore(s);
        require(clone.core.equal(adapter.core), "TAGE snapshot");
        auto sites = adapter.core.sites();
        auto before = adapter.core.bits();
        clone.core.corrupt({0});
        auto after = clone.core.bits();
        size_t changed = 0;
        for (size_t i = 0; i < before.size(); ++i)
            changed += before[i] != after[i];
        require(changed == 1, "single exact bit");
        require(adapter.core.bits() == before, "copy isolation");
        clone.restore(s);
        // Every exposed bit: width-masked round trip and persistence under functional read.
        for (const auto &site : sites) {
            unsigned old = clone.core.payload(site);
            clone.core.write_payload(site, old ^ (1u << site.bit));
            require(clone.core.payload(site) == (old ^ (1u << site.bit)), "logical width XOR");
            require(clone.core.payload(site) == (old ^ (1u << site.bit)), "read cannot repair");
            clone.core.write_payload(site, old);
        }
        for (const auto &site : sites)
            if (site.kind == 1 && site.row == 0) {
                for (unsigned val = 0; val < 8; ++val) {
                    clone.core.write_payload(site, val);
                    require(clone.core.getCtr(site.bank, 0) == decode_signed(val, 3),
                            "signed decode");
                    for (unsigned bit = 0; bit < 3; ++bit) {
                        auto t = site;
                        t.bit = bit;
                        clone.core.write_payload(t, val ^ (1u << bit));
                        require(clone.core.getCtr(site.bank, 0) ==
                                    decode_signed(val ^ (1u << bit), 3),
                                "signed bit flip");
                    }
                }
            }
        clone.restore(s);
        auto raw = *std::find_if(sites.begin(), sites.end(),
                                 [](const Site &t) { return t.kind == 4 && t.bank == 0; });
        auto folded =
            *std::find_if(sites.begin(), sites.end(), [](const Site &t) { return t.kind == 5; });
        auto folds = clone.core.save().folded;
        clone.core.corrupt({raw.id});
        require(clone.core.save().folded == folds, "raw must not recompute folded");
        clone.restore(s);
        auto global = clone.core.save().global;
        clone.core.corrupt({folded.id});
        require(clone.core.save().global == global, "folded must not change raw");
        clone.restore(s);
        auto oldbits = clone.core.bits();
        bool rejected = false;
        try {
            clone.core.corrupt({raw.id, raw.id});
        } catch (const std::invalid_argument &) {
            rejected = true;
        }
        require(rejected && clone.core.bits() == oldbits, "atomic duplicate rejection");
        rejected = false;
        try {
            clone.core.corrupt({raw.id, sites.size()});
        } catch (const std::invalid_argument &) {
            rejected = true;
        }
        require(rejected && clone.core.bits() == oldbits, "atomic bounds rejection");
        clone.core.corrupt({raw.id, folded.id});
        auto bs = clone.core.bits();
        changed = 0;
        for (size_t i = 0; i < bs.size(); ++i)
            changed += bs[i] != oldbits[i];
        require(changed == 2, "atomic two-bit event");
        clone.restore(s);
        for (unsigned i = 0; i < 2000; ++i) {
            Branch b{0x5000 + (i % 30) * 4, 0x5400, bool(i & 1), true};
            require(clone.step(b) == adapter.step(b), "restored continuation");
        }
        require(clone.core.equal(adapter.core) && clone.predictor_rng == adapter.predictor_rng,
                "restored RNG continuation");
        std::cout << "PASS " << sites.size()
                  << " logical sites, signed encodings, snapshot/deep-copy/RNG, raw-folded "
                     "independence, atomic MCU rejection\n";
        // Same upstream implementation rollover path in a smaller software buffer.
        gem5::TAGEBaseParams p;
        p.histBufferSize = 4096;
        TageState small(p), large;
        for (unsigned i = 0; i < 20000; ++i) {
            uint64_t pc = 0x2000 + (i % 20) * 4;
            bool taken = i % 3;
            auto *a = small.makeBranchInfo(pc, true), *b = large.makeBranchInfo(pc, true);
            bool ap = small.tagePredict(0, pc, true, a), bp = large.tagePredict(0, pc, true, b);
            require(ap == bp, "history rollover prediction");
            small.condBranchUpdate(0, pc, taken, a, i & 3, pc + 4, ap);
            large.condBranchUpdate(0, pc, taken, b, i & 3, pc + 4, bp);
            small.updateHistories(0, pc, false, taken, pc + 4, {}, a);
            large.updateHistories(0, pc, false, taken, pc + 4, {}, b);
            delete a;
            delete b;
        }
        require(small.bits() == large.bits(), "history rollover logical state");
        std::cout << "PASS software-buffer rollover equality (4096 vs 2097152)\n";

        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL " << e.what() << '\n';
        return 1;
    }
}
