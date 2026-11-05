#include "tage/pipeline/source_access.hpp"
#include "tage/history/state.hpp"
#include <iostream>
using namespace bp::pipeline;

static void need(bool value, const char *message) {
    if (!value)
        throw std::runtime_error(message);
}
struct Model : SourceAccess<bp::RoundState> {
    Model(const gem5::TAGEBaseParams &p) : SourceAccess(p) {
        configure(Mode::Recurrent, 1, 1);
        enable_protection(Protect::Ecc, Mode::Recurrent);
    }
};
int main() {
    try {
        gem5::TAGEBaseParams params;
        params.speculativeHistUpdate = true;
        params.instShiftAmt = 0;
        params.histBufferSize = 4096;
        Model m(params);
        // Actual two-bit source upset starts the real decoder's DUE/refill path.
        auto &source = m.engine->port.source;
        source.corrupt({source.selected_site(21, 76), source.selected_site(21, 77)});
        auto token = m.request(0x1000, true);
        need(bool(token), "recovery lookup admission");
        bool received = false;
        for (unsigned i = 0; i < 200; ++i) {
            m.advance();
            if (m.engine->peek(*token)) {
                auto *bi = m.consume(*token);
                delete bi;
                received = true;
                break;
            }
        }
        need(received && m.fallback(), "DUE did not enter actual fallback");
        for (unsigned i = 0; i < 200 && !m.drained(); ++i)
            m.advance();
        need(m.drained(), "initial DUE path drain");
        std::vector<bp::Base::BranchInfo *> delayed;
        unsigned retired = 0, waits = 0;
        std::vector<bool> actual;
        for (unsigned cycle = 0; cycle < 600 && retired < 8; ++cycle) {
            unsigned in_cycle = 0;
            while (in_cycle < 8 && m.can_retire(0)) {
                const auto pc = 0x1000 + retired;
                const bool outcome = (retired % 3) == 0;
                need(m.retire_with_outcome(0, outcome, pc), "same-cycle retirement enqueue failed");
                delayed.push_back(m.makeBranchInfo(pc, true));
                actual.push_back(outcome);
                ++retired;
                ++in_cycle;
            }
            need(in_cycle <= 1, "more than one actual commit-history write in a cycle");
            if (!in_cycle)
                ++waits;
            m.advance();
        }
        need(retired == 8 && m.fallback_commits == 8, "retirement lost committed outcome");
        const auto before = m.engine->enqueued;
        // The same delayed BPU callback batch no longer re-enqueues history.
        for (unsigned i = 0; i < delayed.size(); ++i) {
            auto *bi = delayed[i];
            m.updateHistories(0, bi->branchPC, false, actual[i], 0x2000, {}, bi);
            delete bi;
        }
        need(m.engine->enqueued == before, "delayed training duplicated actual commits");
        for (unsigned i = 0; i < 600 && !m.drained(); ++i)
            m.advance();
        need(m.drained() && m.conserved() && m.protection()->committed_refill_publications == 8,
             "committed refill did not drain exactly once");
        auto result = source.observe_source();
        for (unsigned i = 0; i < 8; ++i)
            need(result.raw[i] == actual[7 - i], "actual retirement outcome ordering lost");
        // New one-write/cycle state is included in the mirrored metadata manifest.
        auto regions = m.engine->manifest();
        auto found = std::find_if(regions.begin(), regions.end(), [](const auto &r) {
            return r.name == "ingress_control_mirrored_SECDED";
        });
        need(found != regions.end(), "new control absent from manifest");
        unsigned repaired = 0;
        for (size_t bit = 0; bit < found->bits; ++bit) {
            auto copy = *m.engine;
            copy.corrupt({found->start + bit});
            for (unsigned i = 0; i < 4; ++i)
                copy.advance([](uint64_t, bool, const std::array<unsigned, 21> &, unsigned) {
                    return bp::transport::Payload{};
                });
            need(copy.conserved(), "new ingress-control single-SBU did not preserve state");
            ++repaired;
        }
        std::cout << "{\"status\":\"PASS_ACTUAL_RETIREMENT_COMMIT_INGRESS_II1_NO_DELAYED_"
                     "DUPLICATION\",\"committed_outcomes\":"
                  << retired << ",\"queue_wait_cycles\":" << waits
                  << ",\"new_control_SBU_cases\":" << repaired << ",\"CPU_trials\":0}\n";

    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
