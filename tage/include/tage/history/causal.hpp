#pragma once
#include "tage/predictor/tage_adapter.hpp"
#include <memory>

namespace bp::diagnostic {
// Quiescent committed-only replay has no pending provider or live checkpoint.
// These are diagnostic interventions, never deployable repairs or CPU timing.
struct Layout {
    std::vector<TageAccess::HistoryWord> words;
    std::vector<unsigned> lengths;
    unsigned folds, raw, path;
    explicit Layout(const TageAccess &core) : words(core.history_words()) {
        if (words.size() < 2)
            throw std::invalid_argument("history layout");
        folds = unsigned(words.size()) - 2;
        raw = folds;
        path = folds + 1;
        for (unsigned w = 0; w < folds; ++w)
            lengths.push_back(core.fold_history_length(w));
    }
    Word phi(const TageAccess &core, unsigned word) const {
        if (word >= folds)
            throw std::out_of_range("fold query");
        auto source = core.read_history_word(raw);
        Word result;
        for (unsigned age = 0; age < lengths[word]; ++age)
            if (source.bit(age))
                result.flip(age % words[word].width);
        return result;
    }
};
inline unsigned difference(const Word &a, const Word &b) {
    unsigned count = 0;
    for (unsigned i = 0; i < 3; ++i)
        count += __builtin_popcountll(a.limb[i] ^ b.limb[i]);
    return count;
}
inline unsigned field_difference(const std::vector<unsigned> &a,
                                 const std::vector<unsigned> &b) {
    if (a.size() != b.size())
        throw std::invalid_argument("learning geometry mismatch");
    unsigned result = 0;
    for (size_t i = 0; i < a.size(); ++i)
        result += a[i] != b[i];
    return result;
}
struct Distance {
    unsigned raw = 0, path = 0, fold_invariant = 0, fold_reference = 0;
    unsigned nonspec_path = 0;
    bool head = false;
    std::vector<unsigned> invariant_by_word, reference_by_word;
    unsigned prediction = 0, hysteresis = 0, counter = 0, tag = 0, useful = 0, chooser = 0;
    bool allocation_clock = false, rng = false;
    unsigned learning_fields() const {
        return prediction + hysteresis + counter + tag + useful + chooser + allocation_clock + rng;
    }
};
inline Distance distance(const TageAdapter &current, const TageAdapter &shadow,
                         const Layout &layout, bool include_learning = true) {
    Distance d;
    d.raw = difference(current.core.read_history_word(layout.raw),
                       shadow.core.read_history_word(layout.raw));
    d.path = difference(current.core.read_history_word(layout.path),
                        shadow.core.read_history_word(layout.path));
    d.nonspec_path = __builtin_popcount(current.core.nonspec_path_history() ^
                                      shadow.core.nonspec_path_history());
    d.head = current.core.history_cursor() != shadow.core.history_cursor();
    for (unsigned w = 0; w < layout.folds; ++w) {
        auto value = current.core.read_history_word(w);
        unsigned invariant = difference(value, layout.phi(current.core, w));
        unsigned reference = difference(value, shadow.core.read_history_word(w));
        d.invariant_by_word.push_back(invariant);
        d.reference_by_word.push_back(reference);
        d.fold_invariant += invariant;
        d.fold_reference += reference;
    }
    if (include_learning) {
        auto a = current.core.learning_view(), b = shadow.core.learning_view();
        d.prediction = field_difference(a.prediction, b.prediction);
        d.hysteresis = field_difference(a.hysteresis, b.hysteresis);
        d.counter = field_difference(a.counter, b.counter);
        d.tag = field_difference(a.tag, b.tag);
        d.useful = field_difference(a.useful, b.useful);
        d.chooser = field_difference(a.chooser, b.chooser);
        d.allocation_clock = a.allocation_clock != b.allocation_clock;
        d.rng = current.predictor_rng != shadow.predictor_rng;
    }
    return d;
}
struct Query {
    bool prediction;
    int provider, selected_bank, hit_bank, alternate;
    std::vector<int> indices, tags;
};
inline Query metadata(const Base::BranchInfo &bi, bool prediction, unsigned folds) {
    int selected = bi.provider == Base::TAGE_LONGEST_MATCH ? bi.hitBank :
                   bi.provider == Base::TAGE_ALT_MATCH ? bi.altBank : 0;
    Query q{prediction, int(bi.provider), selected, bi.hitBank, bi.altBank, {}, {}};
    if (bi.condBranch)
        for (unsigned bank = 1; bank <= folds / 3; ++bank) {
            q.indices.push_back(bi.tableIndices[bank]);
            q.tags.push_back(bi.tableTags[bank]);
        }
    return q;
}
inline void copy_learning(TageAdapter::Snapshot &to, const TageAdapter::Snapshot &from) {
    to.state.pred = from.state.pred;
    to.state.hyst = from.state.hyst;
    to.state.tables = from.state.tables;
    to.state.aging = from.state.aging;
    to.state.alt = from.state.alt;
    to.rng = from.rng;
}
inline std::unique_ptr<TageAdapter> clone(const TageAdapter::Snapshot &snapshot) {
    auto result = std::make_unique<TageAdapter>();
    result->restore(snapshot);
    return result;
}
enum class QueryArm { Current, OwnInvariant, ShadowSource, ShadowLearning };
inline Query query(const TageAdapter &current, const TageAdapter &shadow,
                   const Layout &layout, const Branch &branch, QueryArm arm) {
    if (!current.core.all_tagged_banks_enabled() || !shadow.core.all_tagged_banks_enabled())
        throw std::invalid_argument("causal queries require the ordinary all-bank replay contract");
    auto state = current.snapshot();
    if (arm == QueryArm::ShadowSource || arm == QueryArm::ShadowLearning) {
        auto normal = shadow.snapshot();
        if (arm == QueryArm::ShadowSource) {
            state.state.global = normal.state.global;
            state.state.pointer = normal.state.pointer;
            state.state.path = normal.state.path;
            state.state.non_spec = normal.state.non_spec;
        } else
            copy_learning(state, normal);
    }
    auto detached = clone(state);
    if (arm == QueryArm::OwnInvariant || arm == QueryArm::ShadowSource)
        for (unsigned w = 0; w < layout.folds; ++w)
            detached->core.write_history_word(w, layout.phi(detached->core, w));
    auto *bi = detached->core.makeBranchInfo(branch.pc, branch.conditional);
    bool prediction = detached->core.tagePredict(0, branch.pc, branch.conditional, bi);
    auto result = metadata(*bi, prediction, layout.folds);
    delete bi;
    return result;
}
inline TageAdapter::Snapshot suffix_arm(const TageAdapter::Snapshot &faulty,
                                       const TageAdapter::Snapshot &shadow,
                                       bool restore_folds, bool restore_learning) {
    auto result = faulty;
    if (restore_folds)
        result.state.folded = shadow.state.folded;
    if (restore_learning)
        copy_learning(result, shadow);
    return result;
}
} // namespace bp::diagnostic
