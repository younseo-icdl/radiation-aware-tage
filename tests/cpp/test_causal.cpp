#include "tage/history/causal.hpp"
#include <iostream>
using namespace bp;
using namespace bp::diagnostic;
void require(bool condition, const char *reason) {
    if (!condition)
        throw std::runtime_error(reason);
}
Branch branch(unsigned n) {
    return {0x4000 + 4 * (n % 37), 0x8000 + 4 * ((n * 17) % 31),
            bool((n / 37 + n % 7) & 1), bool(n % 13)};
}
int main() {
    try {
        TageAdapter clean;
        for (unsigned i = 0; i < 2048; ++i)
            clean.step(branch(i));
        auto faulty = clone(clean.snapshot());
        Layout layout(clean.core);
        auto raw = faulty->core.read_history_word(layout.raw);
        raw.flip(0);
        faulty->core.write_history_word(layout.raw, raw);
        auto initial = distance(*faulty, clean, layout);
        require(initial.raw == 1 && initial.fold_reference == 0 && initial.fold_invariant > 0,
                "raw XOR must not rebuild folds");
        require(initial.learning_fields() == 0, "raw corruption is not learning drift");
        auto untouched = clone(faulty->snapshot());
        auto q0 = query(*faulty, clean, layout, branch(2049), QueryArm::Current);
        auto qf = query(*faulty, clean, layout, branch(2049), QueryArm::OwnInvariant);
        auto qh = query(*faulty, clean, layout, branch(2049), QueryArm::ShadowSource);
        auto ql = query(*faulty, clean, layout, branch(2049), QueryArm::ShadowLearning);
        require(q0.indices != qf.indices, "own invariant query must use its own H");
        require(q0.indices == qh.indices, "shadow source query must recover clean address");
        require(q0.indices == ql.indices, "learning query must hold H/F fixed");
        require(faulty->core.equal(untouched->core) && faulty->predictor_rng == untouched->predictor_rng,
                "queries must not change the live model or RNG");
        unsigned steps = 0;
        while (distance(*faulty, clean, layout, false).raw && steps < 1024) {
            auto b = branch(2048 + steps++);
            clean.step(b);
            faulty->step(b);
        }
        require(steps && steps < 1024, "source disappearance must be observed");
        require(distance(*faulty, clean, layout, false).fold_reference > 0,
                "source disappearance is distinct from fold recovery");
        auto both = clone(suffix_arm(faulty->snapshot(), clean.snapshot(), true, true));
        auto sanity = clone(clean.snapshot());
        for (unsigned i = 0; i < 1024; ++i) {
            auto b = branch(2048 + steps + i);
            bool reference = clean.step(b);
            require(both->step(b) == reference, "F/L restoration must match aligned suffix");
            require(sanity->step(b) == reference, "full-state sanity prediction");
        }
        auto final = distance(*both, clean, layout);
        require(!final.raw && !final.path && !final.fold_reference && !final.learning_fields(),
                "aligned Y11 active state and learning must match");
        require(sanity->core.equal(clean.core) && sanity->predictor_rng == clean.predictor_rng,
                "full-state sanity must match all stored state and RNG");
        auto folded = clone(clean.snapshot());
        auto value = folded->core.read_history_word(0);
        value.flip(0);
        folded->core.write_history_word(0, value);
        auto f = distance(*folded, clean, layout);
        require(!f.raw && !f.path && f.fold_reference == 1 && f.fold_invariant == 1,
                "fold-only mismatch must not be source corruption");
        auto learning = clone(clean.snapshot());
        auto sites = learning->core.sites();
        auto counter = std::find_if(sites.begin(), sites.end(),
                                    [](const Site &site) { return site.kind == 1; });
        require(counter != sites.end(), "counter site exists");
        learning->core.corrupt({counter->id});
        learning->predictor_rng();
        auto l = distance(*learning, clean, layout);
        require(!l.raw && !l.path && !l.fold_reference && l.counter == 1 && l.rng,
                "table/RNG drift must be separate from H/F");
        auto gold = query(clean, clean, layout, branch(8192), QueryArm::Current);
        auto repaired = query(*learning, clean, layout, branch(8192), QueryArm::ShadowLearning);
        require(gold.prediction == repaired.prediction && gold.indices == repaired.indices &&
                    gold.tags == repaired.tags && gold.provider == repaired.provider,
                "detached shadow-learning query");
        learning->core.tagged_enabled(false);
        bool rejected = false;
        try {
            query(*learning, clean, layout, branch(8192), QueryArm::Current);
        } catch (const std::invalid_argument &) {
            rejected = true;
        }
        require(rejected, "unsupported admission state must not silently change a query");
        std::cout << "PASS detached causal queries, observed source disappearance, oracle suffix "
                     "sanity; COMMITTED_ONLY_REPLAY_NOT_CPU\n";
        return 0;
    } catch (const std::exception &error) {
        std::cerr << "FAIL " << error.what() << '\n';
        return 1;
    }
}
