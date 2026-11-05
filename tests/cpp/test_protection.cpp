#include "tage/predictor/protected_adapter.hpp"
#include <iostream>
#include <numeric>
using namespace bp;
static void require(bool v, const char *why) {
    if (!v)
        throw std::runtime_error(why);
}
static void stored_flip(Word &w, uint16_t &c, unsigned bit, unsigned k) {
    if (bit < k)
        w.flip(bit);
    else
        c ^= 1u << (bit - k);
}
int main() {
    try {
        TageAdapter clean;
        std::mt19937_64 input(548882);
        std::vector<Branch> stream;
        for (unsigned i = 0; i < 120000; ++i)
            stream.push_back(
                {0x1000 + 4 * (input() % 256), 0x2000, bool(input() & 1), i % 13 != 0});
        std::vector<bool> predictions;
        for (auto b : stream)
            predictions.push_back(clean.step(b));
        auto warm = clean.snapshot();
        auto words = clean.core.history_words();
        require(words.size() == 23, "natural word count");
        unsigned payload = 0, check_bits = 0;
        uint64_t single_cases = 0, double_cases = 0;
        for (const auto &word : words) {
            payload += word.width;
            WordSecded code(word.width);
            check_bits += code.r + 1;
            for (unsigned pattern = 0; pattern < 4; ++pattern) {
                Word value;
                for (unsigned b = 0; b < code.k; ++b)
                    value.set(b, pattern == 1 || (pattern == 2 && b % 2) ||
                                     (pattern == 3 && (input() & 1)));
                auto encoded = code.encode(value);
                auto z = code.decode(value, encoded);
                require(z.payload == value && z.check == encoded && !z.corrected && !z.due,
                        "clean SECDED decode");
                for (unsigned a = 0; a < code.n; ++a) {
                    auto v = value;
                    auto c = encoded;
                    stored_flip(v, c, a, code.k);
                    auto r = code.decode(v, c);
                    ++single_cases;
                    require(r.corrected && !r.due && r.payload == value && r.check == encoded,
                            "SECDED single correction/writeback");
                    for (unsigned b = a + 1; b < code.n; ++b) {
                        auto vv = v;
                        auto cc = c;
                        stored_flip(vv, cc, b, code.k);
                        auto rr = code.decode(vv, cc);
                        ++double_cases;
                        require(rr.due && !rr.corrected, "SECDED double detection");
                    }
                }
            }
        }
        require(payload == 346 && check_bits == 121, "scope payload/check counts");
        // Hamming positions 1,2,3: odd zero-syndrome triple is miscorrected as
        // overall-parity error. A fourth flip in overall parity is undetected.
        WordSecded code(9);
        Word zero, triple = zero;
        triple.flip(0);
        uint16_t check = 3;
        auto t = code.decode(triple, check);
        require(t.corrected && !t.due && t.payload != zero, "real triple miscorrection missing");
        require(!code.decode(t.payload, t.check).due && !code.decode(t.payload, t.check).corrected,
                "miscorrection not a valid codeword");
        auto four = code.decode(triple, uint16_t(check ^ (1u << code.r)));
        require(!four.corrected && !four.due && four.payload != zero, "real four-bit miss missing");
        Word illegal;
        illegal.set(9, true);
        bool reject = false;
        try {
            code.encode(illegal);
        } catch (const std::invalid_argument &) {
            reject = true;
        }
        require(reject, "ECC nonlogical high bit accepted");
        for (auto scheme : {Scheme::P0, Scheme::ED, Scheme::ECC, Scheme::TMR}) {
            ProtectedAdapter p(scheme);
            for (unsigned i = 0; i < stream.size(); ++i)
                require(p.step(stream[i]) == predictions[i], "zero-fault prediction changed");
            require(p.predictor.core.equal(clean.core) &&
                        p.predictor.predictor_rng == clean.predictor_rng,
                    "zero-fault full-state/RNG changed");
            require(!p.protection.stats.detected && !p.protection.stats.reset_refill,
                    "spurious detection");
            auto before = p.snapshot();
            auto extra = p.protection.additional_sites();
            size_t expected = scheme == Scheme::P0    ? 0
                              : scheme == Scheme::ED  ? 63
                              : scheme == Scheme::ECC ? 161
                                                      : 692;
            require(extra.size() == expected, "added storage count");
            for (unsigned i = 0; i < extra.size(); ++i)
                require(extra[i].id == 65370 + i, "noncontiguous stored ID");
            for (const auto &word : words)
                for (auto id : word.sites) {
                    p.restore(before);
                    p.protection.corrupt({id});
                    p.protection.check();
                    if (scheme == Scheme::ECC || scheme == Scheme::TMR)
                        require(p.predictor.core.equal(clean.core) &&
                                    p.protection.stats.corrected == 1,
                                "selected payload single not repaired");
                    else if (scheme == Scheme::ED)
                        require(p.protection.refill == 130 && p.protection.epoch == 1 &&
                                    p.protection.stats.reset_refill == 1,
                                "parity single no fallback");
                    else
                        require(!p.predictor.core.equal(clean.core), "P0 unexpectedly repaired");
                }
            for (const auto &site : extra) {
                p.restore(before);
                p.protection.corrupt({site.id});
                if (site.structure == "refill_remaining") {
                    require(p.protection.refill == (1u << site.bit), "refill bit encoding");
                    continue;
                }
                if (site.structure == "history_epoch") {
                    require(p.protection.epoch == (uint32_t(1) << site.bit), "epoch bit encoding");
                    continue;
                }
                p.protection.check();
                if (scheme == Scheme::ED)
                    require(p.protection.refill == 130 && p.protection.stats.reset_refill == 1,
                            "parity-cell injection invisible");
                else
                    require(p.predictor.core.equal(clean.core) && p.protection.stats.corrected == 1,
                            "check/replica single not repaired");
            }
            p.restore(before);
            auto id = words[0].sites[0];
            p.protection.corrupt({id});
            auto corrupt = p.snapshot();
            p.protection.check();
            p.restore(corrupt);
            require(p.predictor.core.payload(p.predictor.core.sites()[id]) !=
                        clean.core.payload(clean.core.sites()[id]),
                    "snapshot aliased modified state");
            auto unchanged = p.predictor.core.bits();
            reject = false;
            try {
                p.protection.corrupt({id, p.protection.exposed_bits()});
            } catch (const std::invalid_argument &) {
                reject = true;
            }
            require(reject && p.predictor.core.bits() == unchanged,
                    "partial invalid event applied");
            reject = false;
            try {
                p.protection.corrupt({id, id});
            } catch (const std::invalid_argument &) {
                reject = true;
            }
            require(reject && p.predictor.core.bits() == unchanged, "duplicate event applied");
        }
        for (auto scheme : {Scheme::ED, Scheme::ECC}) {
            ProtectedAdapter p(scheme);
            p.load_clean_warmup(warm);
            p.protection.corrupt(scheme == Scheme::ED
                                     ? std::vector<size_t>{words[0].sites[0]}
                                     : std::vector<size_t>{words[0].sites[0], words[0].sites[1]});
            require(p.protection.check() && p.protection.fallback(), "DUE/ED did not begin refill");
            for (unsigned w = 0; w < 23; ++w)
                require(p.predictor.core.read_history_word(w) == Word{},
                        "reset left corrupt history");
            auto tables = p.predictor.core.save().tables;
            for (unsigned i = 0; i < 130; ++i) {
                auto b = stream[i];
                auto *bi = p.predictor.core.makeBranchInfo(b.pc, b.conditional);
                auto expect = p.predictor.core.tagePredict(0, b.pc, b.conditional, bi);
                if (b.conditional)
                    require(bi->hitBank == 0 && bi->altBank == 0, "fallback used tagged provider");
                delete bi;
                require(p.step(b) == expect, "fallback prediction");
                require(p.protection.refill == 129 - i, "actual-control refill progress");
            }
            require(!p.protection.fallback() && p.protection.stats.refill_updates == 130,
                    "refill completion");
            auto after = p.predictor.core.save().tables;
            for (unsigned bank = 1; bank < tables.size(); ++bank)
                for (unsigned row = 0; row < tables[bank].size(); ++row)
                    require(tables[bank][row].ctr == after[bank][row].ctr &&
                                tables[bank][row].tag == after[bank][row].tag,
                            "fallback trained tagged tables");
        }
        ProtectedAdapter parity(Scheme::ED);
        parity.load_clean_warmup(warm);
        parity.protection.corrupt({words[0].sites[0], words[0].sites[1]});
        parity.protection.check();
        require(!parity.protection.stats.detected && !parity.predictor.core.equal(clean.core),
                "even parity double wrongly repaired");
        ProtectedAdapter vote(Scheme::TMR);
        vote.load_clean_warmup(warm);
        auto extras = vote.protection.additional_sites();
        vote.protection.corrupt({words[0].sites[0], extras[0].id});
        vote.protection.check();
        require(!vote.predictor.core.equal(clean.core) &&
                    vote.protection.stored_replica(0, 0) == vote.protection.stored_replica(0, 2),
                "same-bit two-copy majority failure hidden");
        vote.load_clean_warmup(warm);
        vote.protection.corrupt({words[0].sites[0], extras[1].id});
        vote.protection.check();
        require(vote.predictor.core.equal(clean.core),
                "different-bit two-copy TMR errors not repaired");
        std::cout
            << "PASS SECDED single=" << single_cases << " double=" << double_cases
            << "; four schemes 120k-control clean full-state/RNG equivalence; 346 payload singles "
               "each; all added cells; parity double miss; SECDED triple miscorrection/four miss; "
               "TMR correlated failure; actual 130-control refill; snapshot; atomic rejection\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "FAIL " << e.what() << '\n';
        return 1;
    }
}
