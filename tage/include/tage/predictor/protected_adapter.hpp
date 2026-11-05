#pragma once
#include "tage/predictor/tage_adapter.hpp"
#include "tage/protection/history_controller.hpp"

namespace bp {
class ProtectedAdapter {
  public:
    TageAdapter predictor;
    HistoryController protection;
    explicit ProtectedAdapter(Scheme scheme, unsigned seed = 548)
        : predictor(seed), protection(predictor.core, scheme) {}
    struct Snapshot {
        TageAdapter::Snapshot predictor;
        HistoryController::Snapshot protection;
    };
    Snapshot snapshot() const { return {predictor.snapshot(), protection.snapshot()}; }
    void restore(const Snapshot &s) {
        predictor.restore(s.predictor);
        protection.restore(s.protection);
    }
    void load_clean_warmup(const TageAdapter::Snapshot &s) {
        predictor.restore(s);
        protection.refill = 0;
        protection.epoch = 0;
        protection.stats = {};
        protection.synchronize();
        predictor.core.tagged_enabled(true);
    }
    bool step(const Branch &b) {
        protection.check();
        protection.prediction();
        auto *bi = predictor.core.makeBranchInfo(b.pc, b.conditional);
        bool p = predictor.core.tagePredict(0, b.pc, b.conditional, bi);
        int nrand = int(predictor.predictor_rng() % std::numeric_limits<int>::max()) & 3;
        if (b.conditional) {
            if (protection.fallback())
                predictor.core.fallback_update(b.pc, b.taken, bi, nrand);
            else
                predictor.core.condBranchUpdate(0, b.pc, b.taken, bi, nrand, b.target, p);
        }
        // Immediate non-spec replay: no injector callback inside the operation.
        // Check precedes the read-modify-write; re-encode only AFTER real writes.
        protection.check();
        predictor.core.updateHistories(0, b.pc, false, b.taken, b.target, {}, bi);
        protection.after_history_write();
        delete bi;
        return p;
    }
};
} // namespace bp
