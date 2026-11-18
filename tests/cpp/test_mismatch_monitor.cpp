#include "tage/history/mismatch_monitor.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <iostream>

using namespace bp;

namespace {

constexpr unsigned bank_count = 7;
constexpr unsigned raw_word = 21;

struct DetectionCounts {
    unsigned trials = 0;
    unsigned first_probe = 0;
    unsigned within_sweep = 0;
    unsigned max_delay_probes = 0;
};

void observe_trial(TageState &core, const std::vector<TageAccess::HistoryWord> &geometry,
                   BankMismatchMonitor monitor, unsigned start, unsigned expected_mask,
                   DetectionCounts &counts) {
    unsigned first = 0;
    for (unsigned probe = 1; probe <= bank_count; ++probe) {
        const auto observed = monitor.probe(core, geometry);
        const unsigned bank = (start + probe - 1) % bank_count;
        if (observed.bank != bank || observed.mismatch != bool(expected_mask & (1u << bank)))
            throw std::runtime_error("bank scheduling or visibility differs from the fault footprint");
        if (observed.mismatch && first == 0)
            first = probe;
    }
    ++counts.trials;
    counts.first_probe += first == 1;
    counts.within_sweep += first != 0;
    counts.max_delay_probes = std::max(counts.max_delay_probes, first);
}

void detection_sweep() {
    TageState core;
    const auto geometry = core.history_words();
    const auto original_raw = core.read_history_word(raw_word);
    DetectionCounts isolated_raw, isolated_fold, coherent_raw;
    std::array<BankMismatchMonitor, bank_count> phases;
    for (unsigned start = 1; start < bank_count; ++start) {
        phases[start] = phases[start - 1];
        phases[start].probe(core, geometry);
    }

    for (unsigned age = 0; age < geometry[raw_word].width; ++age) {
        auto raw = original_raw;
        raw.flip(age);
        core.write_history_word(raw_word, raw);
        unsigned footprint = 0;
        for (unsigned bank = 0; bank < bank_count; ++bank) {
            if (age < core.fold_history_length(3 * bank))
                footprint |= 1u << bank;
        }
        for (unsigned start = 0; start < bank_count; ++start)
            observe_trial(core, geometry, phases[start], start, footprint, isolated_raw);
        publish_own_folds(core, geometry);
        for (unsigned start = 0; start < bank_count; ++start)
            observe_trial(core, geometry, phases[start], start, 0, coherent_raw);
        core.write_history_word(raw_word, original_raw);
        publish_own_folds(core, geometry);
    }

    for (unsigned word = 0; word < raw_word; ++word) {
        const auto original = core.read_history_word(word);
        for (unsigned bit = 0; bit < geometry[word].width; ++bit) {
            auto damaged = original;
            damaged.flip(bit);
            core.write_history_word(word, damaged);
            for (unsigned start = 0; start < bank_count; ++start)
                observe_trial(core, geometry, phases[start], start, 1u << (word / 3), isolated_fold);
        }
        core.write_history_word(word, original);
    }

    if (isolated_raw.within_sweep != isolated_raw.trials ||
        isolated_fold.within_sweep != isolated_fold.trials ||
        coherent_raw.within_sweep != 0 ||
        isolated_fold.first_probe * bank_count != isolated_fold.trials ||
        isolated_fold.max_delay_probes != bank_count)
        throw std::runtime_error("unexpected mismatch detection coverage");

    const auto report = [](const char *condition, const DetectionCounts &counts) {
        std::cout << "mismatch_sweep " << condition << " trials=" << counts.trials
                  << " first_probe=" << counts.first_probe
                  << " within_sweep=" << counts.within_sweep
                  << " max_delay_probes=" << counts.max_delay_probes << '\n';
    };
    report("raw_only", isolated_raw);
    report("fold_only", isolated_fold);
    report("coherent_raw", coherent_raw);
}

} // namespace

int main() {
    try {
        TageState core;
        BankMismatchMonitor monitor;
        const auto geometry=core.history_words();
        auto scan=[&](unsigned expected) {
            for(unsigned bank=0;bank<7;++bank) {
                auto observation=monitor.probe(core,geometry);
                if(observation.bank!=bank ||
                   observation.mismatch!=(bank==0 && expected!=0) ||
                   (bank!=0 && observation.score!=0))
                    throw std::runtime_error("unexpected bank or mismatch");
            }
        };
        scan(0);
        auto fold=core.read_history_word(0);
        fold.flip(0);
        core.write_history_word(0,fold);
        for(unsigned pass=0;pass<4;++pass) {
            const auto fingerprint=core.bits();
            const auto first=monitor.probe(core,geometry);
            if(!first.mismatch || first.score!=std::min(pass+1,3u))
                throw std::runtime_error("mismatch score did not saturate");
            for(unsigned bank=1;bank<7;++bank)
                if(monitor.probe(core,geometry).mismatch)
                    throw std::runtime_error("unrelated bank flagged");
            if(core.bits()!=fingerprint)
                throw std::runtime_error("probe modified predictor state");
        }
        auto raw=core.read_history_word(21);
        raw.flip(0);
        core.write_history_word(21,raw);
        BankMismatchMonitor raw_probe;
        for(unsigned bank=0;bank<7;++bank)
            if(!raw_probe.probe(core,geometry).mismatch)
                throw std::runtime_error("isolated raw flip missed by a bank containing age zero");
        publish_own_folds(core,geometry);
        // Corrupted raw and its canonical folds now agree.
        for(int score=2;score>=0;--score) {
            const auto first=monitor.probe(core,geometry);
            if(first.mismatch || first.score!=unsigned(score))
                throw std::runtime_error("consistent but corrupted raw was treated as detected");
            for(unsigned bank=1;bank<7;++bank)
                if(monitor.probe(core,geometry).mismatch)
                    throw std::runtime_error("consistent bank flagged");
        }
        detection_sweep();
        std::cout<<"PASS round-robin mismatch detection, saturation, decay and consistent corruption limit\n";
    } catch(const std::exception &e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
