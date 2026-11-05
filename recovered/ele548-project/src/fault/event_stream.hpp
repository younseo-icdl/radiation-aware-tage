#pragma once

#include "fault/multiplicity.hpp"
#include <array>
#include <cmath>
#include <limits>
#include <numeric>

namespace bp {

struct TimedFault {
    double time; // Explicit coordinate: conditional-branch exposure, NOT seconds.
    std::vector<size_t> sites;
    unsigned field;
};

inline std::vector<double>
poisson_times(double rate, double duration, uint64_t seed)
{
    if (!std::isfinite(rate) || !std::isfinite(duration) || rate < 0 ||
        duration <= 0 || rate * duration > 10000)
        throw std::invalid_argument("invalid/budget-exceeding Poisson exposure");
    std::vector<double> times;
    if (rate == 0) return times;
    std::mt19937_64 rng(seed);
    std::exponential_distribution<double> gap(rate);
    double time = 0;
    for (;;) {
        double next = time + gap(rng);
        // Floating-point resolution failure is an execution failure, not masking.
        if (!(next > time)) throw std::runtime_error("non-increasing arrival");
        time = next;
        if (time >= duration) return times;
        times.push_back(time);
        if (times.size() > 20000) throw std::runtime_error("event safety limit");
    }
}

// Six fields are sampled by B_j/B, then valid anchors within that field.
// SBU is uniform per exposed bit. MCU endpoints are less exposed than interiors;
// no physical adjacency, SRAM/FF susceptibility, or device strike rate is inferred.
inline std::vector<TimedFault>
mark_events(const std::vector<double>& times,
            const std::array<std::vector<size_t>, 6>& fields,
            const MultiplicityProfile& profile, uint64_t k_seed,
            uint64_t location_seed)
{
    size_t total = 0;
    for (const auto& field : fields) {
        if (field.size() < (profile.k2 ? 2u : 1u))
            throw std::invalid_argument("field too small for multiplicity");
        total += field.size();
    }
    std::mt19937_64 k_rng(k_seed), field_rng(location_seed),
                    anchor_rng(location_seed ^ 0x9e3779b97f4a7c15ULL);
    std::vector<TimedFault> events;
    double last = -1;
    for (double time : times) {
        if (!std::isfinite(time) || time < 0 || time <= last)
            throw std::invalid_argument("invalid arrival times");
        last = time;
        size_t ticket = std::uniform_int_distribution<size_t>(0, total - 1)(field_rng);
        unsigned field = 0;
        while (ticket >= fields[field].size()) ticket -= fields[field++].size();
        auto k = profile.draw(k_rng);
        events.push_back({time, logical_adjacent_event(fields[field], k, anchor_rng), field});
    }
    return events;
}

// All arrivals in [ordinal, ordinal+1) occur BEFORE that conditional prediction.
// Keep distinct events in order, including repeated hits to one bit. Each event
// is an atomic unique bit set. No functional operation occurs between arrivals
// projected to the same branch boundary. This is a trace timing approximation.
template<class Apply>
size_t apply_before_branch(const std::vector<TimedFault>& events,
                          size_t& cursor, unsigned ordinal, Apply apply)
{
    size_t start = cursor;
    while (cursor < events.size() && events[cursor].time < double(ordinal) + 1) {
        if (events[cursor].time < ordinal)
            throw std::logic_error("overdue/unprocessed event");
        apply(events[cursor]);
        ++cursor;
    }
    return cursor - start;
}
} // namespace bp
