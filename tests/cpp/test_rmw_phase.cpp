#include "tage/pipeline/source_protection.hpp"
#include "tage/history/state.hpp"
#include <iostream>
using namespace bp::pipeline;
static void need(bool x, const char *s) {
    if (!x)
        throw IntegrityError(s);
}
static auto geometry() {
    bp::RoundState r;
    auto w = r.history_words();
    std::vector<Geometry> g;
    for (unsigned i = 0; i < 21; ++i)
        g.push_back({r.fold_length(i), w[i].width});
    return g;
}
static Service make(Protect p) {
    Service s(Mode::Recurrent, geometry());
    s.attach_guard(std::make_unique<FiniteProtection>(s.selected_widths(), p));
    return s;
}
static FiniteProtection &guard(Service &s) { return *dynamic_cast<FiniteProtection *>(s.guard()); }
static void drain(Service &s) {
    for (unsigned n = 0; n < 100; ++n) {
        if (s.drained())
            return;
        s.tick();
        s.take();
        s.take();
    }
    throw IntegrityError("RMW gate drain");
}
static void read(Service &s) {
    auto t = s.accept(Kind::Read);
    need(bool(t), "RMW gate read");
    for (unsigned n = 0; n < 100; ++n) {
        s.tick();
        if (s.take(*t)) {
            drain(s);
            return;
        }
    }
    throw IntegrityError("RMW gate read timeout");
}
int main() {
    try {
        unsigned cases = 0, ecc_tmr = 0, parity = 0, periodic = 0, masked = 0;
        for (unsigned p = 0; p < 5; ++p) {
            auto policy = Protect(p);
            auto seed = make(policy);
            for (unsigned i = 0; i < 20; ++i) {
                need(bool(seed.accept(Kind::Append, 1, i % 3 == 0, i & 1)), "seed append");
                drain(seed);
            }
            auto widths = seed.selected_widths();
            for (unsigned w = 0; w < 23; ++w)
                for (unsigned bit = 0; bit < widths[w]; ++bit)
                    for (unsigned phase = 0; phase < 5; ++phase) {
                        auto a = seed, b = seed;
                        need(bool(a.accept(Kind::Append, 1, 1, 1)) &&
                                 bool(b.accept(Kind::Append, 1, 1, 1)),
                             "phase append");
                        for (unsigned tick = 0; tick < phase; ++tick) {
                            a.tick();
                            a.take();
                            a.take();
                            b.tick();
                            b.take();
                            b.take();
                        }
                        a.corrupt({a.selected_site(w, bit)});
                        drain(a);
                        drain(b);
                        read(a);
                        read(b);
                        bool equal = a.selected_words() == b.selected_words();
                        if (policy == Protect::Ecc || policy == Protect::Tmr) {
                            if (!equal)
                                std::cerr << "uncorrected p=" << p << " w=" << w << " b=" << bit
                                          << " phase=" << phase << '\n';
                            need(equal, "SSTAR SBU not restored after actual RMW/encode");
                            ++ecc_tmr;
                        } else if (policy == Protect::Parity) {
                            need(equal || guard(a).fallback(), "parity SSTAR silently laundered");
                            ++parity;
                        } else if (policy == Protect::Periodic) {
                            if (!equal) {
                                for (unsigned i = 0; i < 65 && !guard(a).fallback(); ++i) {
                                    need(bool(a.accept(Kind::Append, 1, i & 1, i & 1)),
                                         "periodic maintenance append");
                                    drain(a);
                                    read(a);
                                }
                                need(guard(a).fallback(), "periodic residual laundered during RMW");
                            }
                            ++periodic;
                        } else
                            masked += equal;
                        need(a.conserved() && b.conserved(), "RMW event conservation");
                        ++cases;
                    }
        }
        std::cout << "{\"status\":\"PASS_ALL_SSTAR_SOURCE_PHASES_NOT_ALL_ADDED_LATCH_BITS\","
                     "\"source_SBU_phase_cases\":"
                  << cases << ",\"ECC_TMR_restored_or_naturally_overwritten\":" << ecc_tmr
                  << ",\"parity_excluded_or_overwritten\":" << parity
                  << ",\"periodic_due_or_overwritten\":" << periodic
                  << ",\"P0_naturally_overwritten\":" << masked << ",\"CPU_trials\":0}\n";
    } catch (const std::exception &e) {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
