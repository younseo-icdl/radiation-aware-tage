#include "tage/history/mismatch_monitor.hpp"
#include "tage/predictor/tage_adapter.hpp"
#include <iostream>

using namespace bp;

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
        std::cout<<"PASS round-robin mismatch detection, saturation, decay and consistent corruption limit\n";
    } catch(const std::exception &e) {
        std::cerr<<e.what()<<'\n';
        return 1;
    }
}
