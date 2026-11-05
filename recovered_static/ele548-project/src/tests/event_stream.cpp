#include "fault/event_stream.hpp"
#include "predictor/tage_adapter.hpp"
#include <iostream>

void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    try {
        using namespace bp;
        require(poisson_times(0, 100, 548).empty(), "zero rate");
        require(poisson_times(.2, 100, 548) == poisson_times(.2, 100, 548), "determinism");
        for (auto x : std::vector<std::pair<double, double>>{
                 {-1, 1}, {1, 0}, {INFINITY, 1}, {1, NAN}, {10001, 1}}) {
            bool rejected = false;
            try { poisson_times(x.first, x.second, 1); }
            catch (const std::invalid_argument&) { rejected = true; }
            require(rejected, "invalid rate/duration accepted");
        }
        // Check the stochastic law itself, without expensive predictor campaigns.
        double sum = 0, sum2 = 0, one_time = 0;
        unsigned n_one = 0;
        const unsigned samples = 20000;
        for (unsigned seed = 0; seed < samples; ++seed) {
            auto t = poisson_times(.5, 10, seed);
            sum += t.size(); sum2 += t.size() * t.size();
            require(std::is_sorted(t.begin(), t.end()), "non-monotonic stream");
            for (auto x : t) require(x >= 0 && x < 10, "out-of-window arrival");
            if (t.size() == 1) { one_time += t[0] / 10; ++n_one; }
        }
        double mean = sum / samples, variance = sum2 / samples - mean * mean;
        require(std::abs(mean - 5) < .1 && std::abs(variance - 5) < .2, "Poisson count moments");
        require(n_one > 500 && std::abs(one_time / n_one - .5) < .05, "conditional single-event time");
        TageAdapter adapter;
        std::array<std::vector<size_t>, 6> fields;
        for (auto s : adapter.core.sites()) fields[s.kind].push_back(s.id);
        auto times = poisson_times(.01, 10000, 6548);
        auto sbu = mark_events(times, fields, MultiplicityProfile(1, 0), 11, 12);
        auto mcu = mark_events(times, fields, MultiplicityProfile(0, 1), 11, 12);
        require(sbu.size() == mcu.size(), "marks changed arrival count");
        for (size_t i = 0; i < sbu.size(); ++i) {
            require(sbu[i].time == mcu[i].time, "marks changed timing");
            require(sbu[i].field == mcu[i].field, "K changed field schedule");
            require(mcu[i].sites.size() == 2 && mcu[i].sites[1] == mcu[i].sites[0] + 1,
                    "invalid MCU marking");
        }
        // Validate bit-weighted exposure, rather than accidentally equalizing fields.
        std::vector<double> mark_times;
        for (unsigned i = 0; i < 50000; ++i) mark_times.push_back(i + .5);
        auto population = mark_events(mark_times, fields, MultiplicityProfile(205, 9), 581, 582);
        std::array<unsigned, 6> counts{};
        unsigned k2 = 0;
        size_t total_bits = 0;
        for (auto& f : fields) total_bits += f.size();
        for (auto& e : population) { ++counts[e.field]; k2 += e.sites.size() == 2; }
        for (unsigned field = 0; field < 6; ++field) {
            double p = double(fields[field].size()) / total_bits;
            require(std::abs(double(counts[field]) / population.size() - p) <
                    5 * std::sqrt(p * (1 - p) / population.size()) + .0001,
                    "incorrect bit-weighted field exposure");
        }
        require(std::abs(double(k2) / population.size() - 9.0 / 214) < .004,
                "CHARM marking probability");
        // Two independent hits to the same bit can cancel. They are not deduplicated.
        auto initial = adapter.snapshot();
        auto original = adapter.core.bits();
        std::vector<TimedFault> schedule{{0.1, {0}, 0}, {0.2, {0}, 0}, {1.1, {0, 1}, 0}};
        size_t cursor = 0;
        require(apply_before_branch(schedule, cursor, 0, [&](auto& e) { adapter.core.corrupt(e.sites); }) == 2,
                "dropped multiple arrivals in a branch bin");
        require(adapter.core.bits() == original, "separate same-bit hits did not XOR twice");
        adapter.step({0x100, 0x200, true, true});
        auto before_second_boundary = adapter.core.bits();
        require(apply_before_branch(schedule, cursor, 1, [&](auto& e) { adapter.core.corrupt(e.sites); }) == 1,
                "next-boundary event lost");
        auto after = adapter.core.bits();
        for (size_t id = 0; id < after.size(); ++id)
            require(after[id] == (before_second_boundary[id] ^ unsigned(id < 2)), "continuity or atomic MCU error");
        require(adapter.predictor_rng != initial.rng, "event reset predictor RNG");
        require(cursor == 3, "incorrect consumed count");
        std::cout << "PASS Poisson_count_mean=" << mean << " variance=" << variance
                  << " conditional_one_event_mean=" << one_time / n_one
                  << " RNG_separation,continuous_state,atomic_MCU,same_branch_multiple_events\n";
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << e.what() << '\n'; return 1;
    }
}
