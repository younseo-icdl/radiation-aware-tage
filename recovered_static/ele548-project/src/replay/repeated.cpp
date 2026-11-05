#include "predictor/tage_adapter.hpp"
#include "fault/event_stream.hpp"
#include <chrono>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sys/resource.h>

using namespace bp;

int main(int argc, char** argv) {
    try {
        if (argc != 11)
            throw std::invalid_argument("usage: repeated TRACE RATE TIME_SEED K_SEED LOCATION_SEED K1 K2 MODEL SUMMARY_CSV EVENTS_CSV");
        double rate = std::stod(argv[2]);
        uint64_t time_seed = std::stoull(argv[3]), k_seed = std::stoull(argv[4]),
                 location_seed = std::stoull(argv[5]);
        MultiplicityProfile profile(std::stoull(argv[6]), std::stoull(argv[7]));
        auto times = poisson_times(rate, 10000, time_seed);
        std::ifstream in(argv[1]);
        if (!in) throw std::runtime_error("missing trace");
        std::vector<Branch> trace;
        Branch branch;
        while (in >> branch.pc >> branch.target >> branch.taken >> branch.conditional)
            trace.push_back(branch);
        if (!in.eof()) throw std::runtime_error("malformed trace");
        TageAdapter clean;
        unsigned ordinal = 0;
        size_t boundary = 0;
        for (size_t i = 0; i < trace.size(); ++i) {
            clean.step(trace[i]);
            ordinal += trace[i].conditional;
            if (ordinal == 20000) { boundary = i + 1; break; }
        }
        if (!boundary) throw std::runtime_error("short warmup");
        auto warm = clean.snapshot();
        std::vector<bool> gold;
        unsigned clean_misses = 0, observed = 0;
        for (size_t i = boundary; i < trace.size(); ++i) {
            bool p = clean.step(trace[i]);
            gold.push_back(p);
            clean_misses += trace[i].conditional && p != trace[i].taken;
            observed += trace[i].conditional;
        }
        if (observed != 10000) throw std::runtime_error("wrong observation horizon");
        std::array<std::vector<size_t>, 6> fields;
        for (const auto& site : clean.core.sites()) fields[site.kind].push_back(site.id);
        auto events = mark_events(times, fields, profile, k_seed, location_seed);
        std::ofstream event_out(argv[10]), out(argv[9]);
        if (!event_out || !out) throw std::runtime_error("unavailable output");
        event_out << std::setprecision(17)
                  << "event_id,arrival_branch_coordinate,applied_before_conditional_ordinal,field,multiplicity,event_site_ids,status\n";
        auto start = std::chrono::steady_clock::now();
        TageAdapter faulty;
        faulty.restore(warm); // ONCE per run; never between events.
        size_t cursor = 0;
        unsigned harm = 0, help = 0, flip_count = 0, multi_event_bins = 0;
        unsigned faulty_misses = 0, injected_count = 0;
        int first = -1, last = -1;
        ordinal = 0;
        for (size_t i = boundary; i < trace.size(); ++i) {
            const auto& b = trace[i];
            if (b.conditional) {
                size_t count = apply_before_branch(events, cursor, ordinal, [&](const TimedFault& e) {
                    // XOR is atomic within an event; no gold or event-driven repair.
                    faulty.core.corrupt(e.sites);
                    event_out << injected_count++ << ',' << e.time << ',' << ordinal << ','
                              << field_name(e.field) << ',' << e.sites.size() << ',';
                    for (size_t j = 0; j < e.sites.size(); ++j) {
                        if (j) event_out << ';';
                        event_out << e.sites[j];
                    }
                    event_out << ",PASS\n";
                    flip_count += e.sites.size();
                });
                multi_event_bins += count > 1;
            }
            bool p = faulty.step(b), g = gold[i - boundary];
            if (b.conditional) {
                bool fm = p != b.taken, gm = g != b.taken;
                faulty_misses += fm;
                harm += fm && !gm;
                help += !fm && gm;
                if (p != g) { if (first < 0) first = ordinal; last = ordinal; }
                ++ordinal;
            }
        }
        if (cursor != events.size() || injected_count != events.size())
            throw std::runtime_error("lost scheduled events");
        if (faulty.predictor_rng != clean.predictor_rng)
            throw std::runtime_error("predictor RNG schedule changed");
        if (events.empty() && !faulty.core.equal(clean.core))
            throw std::runtime_error("zero-event full-state mismatch");
        auto a = faulty.core.bits(), z = clean.core.bits();
        unsigned residual = 0;
        for (size_t i = 0; i < a.size(); ++i) residual += a[i] != z[i];
        double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        struct rusage usage;
        getrusage(RUSAGE_SELF, &usage);
        double mean_k = double(profile.k1 + 2 * profile.k2) / (profile.k1 + profile.k2);
        out << "model,event_rate_per_conditional_branch,expected_flip_rate_per_conditional_branch,time_seed,k_seed,location_seed,event_count,flip_count,multi_event_branch_bins,clean_misses,faulty_misses,harm,help,net,first_divergence,last_divergence,end_differing_logical_bits,observation_branches,trial_wall_seconds,peak_rss_kib,status\n"
            << std::setprecision(17) << argv[8] << ',' << rate << ',' << rate * mean_k << ','
            << time_seed << ',' << k_seed << ',' << location_seed << ',' << events.size() << ','
            << flip_count << ',' << multi_event_bins << ',' << clean_misses << ',' << faulty_misses << ','
            << harm << ',' << help << ',' << int(harm) - int(help) << ',' << first << ',' << last << ','
            << residual << ',' << ordinal << ',' << seconds << ',' << usage.ru_maxrss << ",PASS\n";
        if (!event_out || !out) throw std::runtime_error("output write failure");
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL_EXECUTION " << error.what() << '\n';
        return 1;
    }
}
