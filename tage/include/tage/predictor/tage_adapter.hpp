#pragma once
#include "tage/predictor/tage_access.hpp"
#include <random>
#include <stdexcept>
#include <algorithm>
#include <string>
#include <sstream>
#include <set>
#include <limits>
namespace bp {
class TageState : public TageAccess {
  public:
    explicit TageState(const gem5::TAGEBaseParams &p = {}) : TageAccess(p) { init(); }
    TageState(const TageState &) = delete;
    TageState &operator=(const TageState &) = delete;
    ~TageState() override {
        for (unsigned i = 1; i <= nHistoryTables; ++i)
            delete[] gtable[i];
        delete[] gtable;
        for (auto &h : threadHistory) {
            delete[] h.computeIndices;
            delete[] h.computeTags[0];
            delete[] h.computeTags[1];
        }
        delete[] histLengths;
        delete[] tableIndices;
        delete[] tableTags;
    }
    struct Snapshot {
        std::vector<bool> pred, hyst;
        std::vector<std::vector<TageEntry>> tables;
        std::vector<uint8_t> global;
        int pointer, path, non_spec;
        int64_t aging;
        std::vector<int8_t> alt;
        std::vector<unsigned> folded;
    };
    Snapshot save() const {
        Snapshot s;
        s.pred = btablePrediction;
        s.hyst = btableHysteresis;
        s.tables.resize(nHistoryTables + 1);
        for (unsigned b = 1; b <= nHistoryTables; ++b)
            s.tables[b].assign(gtable[b], gtable[b] + (1 << logTagTableSizes[b]));
        const auto &h = threadHistory[0];
        s.global = h.globalHist;
        s.pointer = h.ptGhist;
        s.path = h.pathHist;
        s.non_spec = h.nonSpecPathHist;
        s.aging = tCounter;
        s.alt = useAltPredForNewlyAllocated;
        for (unsigned b = 1; b <= nHistoryTables; ++b) {
            s.folded.push_back(h.computeIndices[b].comp);
            s.folded.push_back(h.computeTags[0][b].comp);
            s.folded.push_back(h.computeTags[1][b].comp);
        }
        return s;
    }
    void load(const Snapshot &s) {
        if (s.pred.size() != btablePrediction.size() || s.global.size() != histBufferSize ||
            s.tables.size() != nHistoryTables + 1 || s.folded.size() != nHistoryTables * 3)
            throw std::invalid_argument("snapshot geometry");
        btablePrediction = s.pred;
        btableHysteresis = s.hyst;
        for (unsigned b = 1; b <= nHistoryTables; ++b) {
            if (s.tables[b].size() != size_t(1 << logTagTableSizes[b]))
                throw std::invalid_argument("snapshot table");
            std::copy(s.tables[b].begin(), s.tables[b].end(), gtable[b]);
        }
        auto &h = threadHistory[0];
        h.globalHist = s.global;
        h.ptGhist = s.pointer;
        h.pathHist = s.path;
        h.nonSpecPathHist = s.non_spec;
        tCounter = s.aging;
        useAltPredForNewlyAllocated = s.alt;
        for (unsigned b = 1; b <= nHistoryTables; ++b) {
            h.computeIndices[b].comp = s.folded[(b - 1) * 3];
            h.computeTags[0][b].comp = s.folded[(b - 1) * 3 + 1];
            h.computeTags[1][b].comp = s.folded[(b - 1) * 3 + 2];
        }
    }
    bool equal(const TageState &other) const {
        auto a = save(), b = other.save();
        if (a.pred != b.pred || a.hyst != b.hyst || a.global != b.global ||
            a.pointer != b.pointer || a.path != b.path || a.non_spec != b.non_spec ||
            a.aging != b.aging || a.alt != b.alt || a.folded != b.folded)
            return false;
        for (unsigned bank = 1; bank <= nHistoryTables; ++bank)
            for (size_t r = 0; r < a.tables[bank].size(); ++r) {
                auto x = a.tables[bank][r], y = b.tables[bank][r];
                if (x.ctr != y.ctr || x.tag != y.tag || x.u != y.u)
                    return false;
            }
        return true;
    }
};
struct Branch {
    uint64_t pc, target;
    bool taken, conditional;
};
class TageAdapter {
  public:
    TageState core;
    std::mt19937_64 predictor_rng;
    explicit TageAdapter(unsigned seed = 548) : predictor_rng(seed) {}
    struct Snapshot {
        TageState::Snapshot state;
        std::mt19937_64 rng;
    };
    Snapshot snapshot() const { return {core.save(), predictor_rng}; }
    void restore(const Snapshot &s) {
        core.load(s.state);
        predictor_rng = s.rng;
    }
    bool step(const Branch &b) {
        return step_observed(b, [](const Base::BranchInfo &) {});
    }
    // Read-only metadata observer; used to diagnose queried addresses in E1.
    // It executes after prediction, before the unchanged RNG/update schedule.
    template <class Observer> bool step_observed(const Branch &b, Observer observe) {
        auto *bi = core.makeBranchInfo(b.pc, b.conditional);
        bool prediction = core.tagePredict(0, b.pc, b.conditional, bi);
        observe(*bi);
        // Exactly TAGE::update non-spec replay order: RNG every control branch,
        // table update for conditional branches, then actual history update.
        int nrand = int(predictor_rng() % std::numeric_limits<int>::max()) & 3;
        if (b.conditional)
            core.condBranchUpdate(0, b.pc, b.taken, bi, nrand, b.target, prediction);
        core.updateHistories(0, b.pc, false, b.taken, b.target, {}, bi);
        delete bi;
        return prediction;
    }
};
} // namespace bp
