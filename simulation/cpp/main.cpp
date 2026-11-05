#include "tage/predictor/protected_adapter.hpp"
#include <fstream>
#include <iostream>
#include <map>

namespace {
struct Event {
    uint64_t at;
    std::vector<std::pair<unsigned, unsigned>> sites;
};
uint64_t number(const std::string &s) {
    if (s.empty() || s[0] == '-')
        throw std::invalid_argument("invalid unsigned integer");
    size_t n = 0;
    auto v = std::stoull(s, &n, 0);
    if (n != s.size())
        throw std::invalid_argument("invalid integer: " + s);
    return v;
}
std::vector<Event> read_events(const std::string &path, const bp::TageAccess &core) {
    std::vector<Event> result;
    if (path.empty())
        return result;
    std::ifstream in(path);
    if (!in)
        throw std::runtime_error("cannot open schedule");
    std::string line;
    uint64_t previous = 0;
    auto words = core.history_words();
    while (std::getline(in, line)) {
        if (line.empty() || line[0] == '#') {
            auto unit_position = line.find("time_unit=");
            if (unit_position != std::string::npos) {
                std::istringstream header(line.substr(unit_position));
                std::string unit;
                header >> unit;
                if (unit != "time_unit=branches")
                    throw std::invalid_argument("C++ replay requires branch exposure units");
            }
            continue;
        }
        std::istringstream row(line);
        std::string time, ids, extra;
        if (!(row >> time >> ids) || (row >> extra))
            throw std::invalid_argument("schedule requires: branch_ordinal sites");
        Event e{number(time), {}};
        if (!e.at || e.at < previous)
            throw std::invalid_argument("schedule must be ordered and start at branch 1");
        previous = e.at;
        std::istringstream tokens(ids);
        std::string token;
        std::set<std::pair<unsigned, unsigned>> unique;
        while (std::getline(tokens, token, ';')) {
            uint64_t w = 0, b = 0;
            if (token.size() > 1 && token[0] == 'R') {
                w = 21;
                b = number(token.substr(1));
            } else if (token.size() > 1 && token[0] == 'W') {
                auto split = token.find(':');
                if (split == std::string::npos)
                    throw std::invalid_argument("invalid word alias");
                w = number(token.substr(1, split - 1));
                b = number(token.substr(split + 1));
            } else
                throw std::invalid_argument("expected R<age> or W<word>:<bit>");
            if (w >= words.size() || b >= words[w].width)
                throw std::invalid_argument("site outside selected logical history");
            std::pair<unsigned, unsigned> site{unsigned(w), unsigned(b)};
            if (!unique.insert(site).second)
                throw std::invalid_argument("duplicate bit within an atomic event");
            e.sites.push_back(site);
        }
        if (e.sites.empty() || ids.back() == ';')
            throw std::invalid_argument("empty atomic event");
        result.push_back(e);
    }
    return result;
}
void inject(bp::TageAccess &core, const Event &e) {
    // Validate all events before replay; coalesce writes without touching the
    // protection sidecars. No detector is called inside an atomic event.
    std::map<unsigned, bp::Word> writes;
    for (auto site : e.sites) {
        if (!writes.count(site.first))
            writes.emplace(site.first, core.read_history_word(site.first));
        writes.at(site.first).flip(site.second);
    }
    for (auto &w : writes)
        core.write_history_word(w.first, w.second);
}
} // namespace
int main(int argc, char **argv) {
    try {
        std::string trace, schedule, scheme = "P0";
        uint64_t demo = 0;
        unsigned seed = 548;
        bool list_state = false;
        for (int i = 1; i < argc; ++i) {
            std::string arg = argv[i];
            if (arg == "--list-state") {
                list_state = true;
                continue;
            }
            if (arg == "--help") {
                std::cout
                    << "tage-sim (--trace FILE | --demo N) [--scheme P0|P_ED|P_ECC|P_TMR] "
                       "[--schedule FILE] [--seed N] [--list-state]\nTrace rows: pc taken target "
                       "conditional (integers; hex addresses accepted).\n";
                return 0;
            }
            if (i + 1 == argc)
                throw std::invalid_argument("missing argument value");
            std::string value = argv[++i];
            if (arg == "--trace")
                trace = value;
            else if (arg == "--schedule")
                schedule = value;
            else if (arg == "--scheme")
                scheme = value;
            else if (arg == "--demo")
                demo = number(value);
            else if (arg == "--seed") {
                auto n = number(value);
                if (n > UINT32_MAX)
                    throw std::invalid_argument("seed too large");
                seed = n;
            } else
                throw std::invalid_argument("unknown option: " + arg);
        }
        bp::ProtectedAdapter model(bp::scheme_from(scheme), seed);
        if (list_state) {
            std::cout << "{\"selected_history_words\":[";
            auto words = model.predictor.core.history_words();
            for (unsigned w = 0; w < words.size(); ++w) {
                if (w)
                    std::cout << ',';
                std::cout << "{\"word\":" << w << ",\"name\":\"" << words[w].id
                          << "\",\"width\":" << words[w].width << '}';
            }
            std::cout << "],\"base_exposed_bits\":" << model.predictor.core.sites().size()
                      << ",\"protection_added_bits\":" << model.protection.additional_sites().size()
                      << "}\n";
            return 0;
        }
        if (trace.empty() == (demo == 0))
            throw std::invalid_argument("choose --trace FILE or --demo N");
        auto events = read_events(schedule, model.predictor.core);
        size_t event = 0;
        uint64_t branches = 0, conditional = 0, misses = 0, flips = 0;
        auto step = [&](const bp::Branch &branch) {
            ++branches;
            while (event < events.size() && events[event].at == branches) {
                inject(model.predictor.core, events[event]);
                flips += events[event].sites.size();
                ++event;
            }
            bool predicted = model.step(branch);
            if (branch.conditional) {
                ++conditional;
                misses += (predicted != branch.taken);
            }
        };
        if (demo) {
            for (uint64_t n = 0; n < demo; ++n)
                step({0x1000 + 4 * (n % 17), 0x1000 + 4 * ((n + 1) % 17),
                      bool(((n / 17) ^ (n % 7)) & 1), true});
        } else {
            std::ifstream in(trace);
            if (!in)
                throw std::runtime_error("cannot open trace");
            std::string line;
            while (std::getline(in, line)) {
                if (line.empty() || line[0] == '#')
                    continue;
                std::replace(line.begin(), line.end(), ',', ' ');
                std::istringstream row(line);
                std::string pc, taken, target, cond, extra;
                if (!(row >> pc >> taken >> target >> cond) || (row >> extra))
                    throw std::invalid_argument("trace requires four fields");
                auto t = number(taken), c = number(cond);
                if (t > 1 || c > 1)
                    throw std::invalid_argument("trace Boolean outside 0..1");
                step({number(pc), number(target), bool(t), bool(c)});
            }
        }
        if (!branches)
            throw std::invalid_argument("empty trace");
        const auto &s = model.protection.stats;
        std::cout << "{\"mode\":\"functional_replay\",\"workload\":\""
                  << (demo ? "synthetic" : "external_trace") << "\",\"scheme\":\"" << scheme
                  << "\",\"branches\":" << branches << ",\"conditional_branches\":" << conditional
                  << ",\"mispredictions\":" << misses
                  << ",\"misprediction_rate\":" << (conditional ? double(misses) / conditional : 0)
                  << ",\"applied_events\":" << event << ",\"applied_flips\":" << flips
                  << ",\"future_events_censored\":" << events.size() - event
                  << ",\"detected\":" << s.detected << ",\"corrected\":" << s.corrected
                  << ",\"due\":" << s.due << ",\"resets\":" << s.reset_refill << "}\n";
        return 0;
    } catch (const std::exception &e) {
        std::cerr << "ERROR: " << e.what() << '\n';
        return 1;
    }
}
