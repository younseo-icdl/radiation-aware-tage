#include "tage/history/causal.hpp"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
using namespace bp;
namespace diag = bp::diagnostic;
namespace fs = std::filesystem;
namespace {
uint64_t number(const std::string &text) {
    size_t end = 0;
    if (text.empty() || text[0] == '-')
        throw std::invalid_argument("expected unsigned integer");
    auto result = std::stoull(text, &end, 0);
    if (end != text.size())
        throw std::invalid_argument("invalid integer");
    return result;
}
std::vector<Branch> read_trace(const fs::path &path, bool target_second, uint64_t limit) {
    std::ifstream stream(path);
    if (!stream)
        throw std::runtime_error("cannot open trace");
    std::vector<Branch> result;
    std::string line;
    while (result.size() < limit && std::getline(stream, line)) {
        if (line.empty() || line[0] == '#')
            continue;
        std::replace(line.begin(), line.end(), ',', ' ');
        std::istringstream row(line);
        std::string pc, a, b, conditional, extra;
        if (!(row >> pc >> a >> b >> conditional) || row >> extra)
            throw std::invalid_argument("trace requires four explicit fields");
        auto taken = number(target_second ? b : a), cond = number(conditional);
        if (taken > 1 || cond > 1)
            throw std::invalid_argument("trace Boolean outside 0..1; check --trace-format");
        result.push_back({number(pc), number(target_second ? a : b), bool(taken), bool(cond)});
    }
    return result;
}
diag::Query step(TageAdapter &model, const Branch &branch, unsigned folds) {
    diag::Query result{};
    result.prediction = model.step_observed(branch, [&](const Base::BranchInfo &bi) {
        result = diag::metadata(bi, bi.tagePred, folds);
    });
    return result;
}
struct Outcome {
    uint64_t harmful = 0, helpful = 0, differences = 0;
    void observe(bool fault, bool normal, const Branch &b) {
        if (!b.conditional)
            return;
        differences += fault != normal;
        harmful += normal == b.taken && fault != b.taken;
        helpful += normal != b.taken && fault == b.taken;
    }
    int64_t net() const { return int64_t(harmful) - int64_t(helpful); }
};
unsigned inject(TageAdapter &model, const diag::Layout &layout, const std::string &sites) {
    std::istringstream stream(sites);
    std::string token;
    std::map<unsigned, Word> writes;
    std::set<std::pair<unsigned, unsigned>> unique;
    while (std::getline(stream, token, ';')) {
        uint64_t word, bit;
        if (token.size() > 1 && token[0] == 'R') {
            word = layout.raw;
            bit = number(token.substr(1));
        } else if (token.size() > 1 && token[0] == 'W') {
            auto colon = token.find(':');
            if (colon == std::string::npos)
                throw std::invalid_argument("expected W<word>:<bit>");
            word = number(token.substr(1, colon-1));
            bit = number(token.substr(colon+1));
        } else
            throw std::invalid_argument("expected R<age> or W<word>:<bit>");
        if (word >= layout.words.size() || bit >= layout.words[word].width ||
            !unique.emplace(unsigned(word), unsigned(bit)).second)
            throw std::invalid_argument("invalid or duplicate atomic site");
        if (!writes.count(word))
            writes[word] = model.core.read_history_word(word);
        writes[word].flip(bit);
    }
    if (unique.empty() || sites.back() == ';')
        throw std::invalid_argument("empty event site");
    // Commit only after the entire one-event XOR group has been validated.
    for (const auto &entry : writes)
        model.core.write_history_word(entry.first, entry.second);
    return unsigned(unique.size());
}
} // namespace
int main(int argc, char **argv) {
    try {
        fs::path trace, output;
        std::string sites, format = "pc-taken-target-conditional";
        uint64_t event = 2049, limit = 8192, seed = 548;
        for (int i = 1; i < argc; ++i) {
            std::string name = argv[i];
            if (name == "--help") {
                std::cout << "tage-causal --trace FILE --site R<age>|W<word>:<bit> --output NEW_DIR "
                    "[--trace-format pc-taken-target-conditional|pc-target-taken-conditional] "
                    "[--event-branch N] [--limit N] [--seed N]\n"
                    "Quiescent committed-only causal replay, not CPU performance.\n";
                return 0;
            }
            if (++i == argc)
                throw std::invalid_argument("missing option value");
            std::string value = argv[i];
            if (name == "--trace") trace = value;
            else if (name == "--output") output = value;
            else if (name == "--site") sites = value;
            else if (name == "--trace-format") format = value;
            else if (name == "--event-branch") event = number(value);
            else if (name == "--limit") limit = number(value);
            else if (name == "--seed") seed = number(value);
            else throw std::invalid_argument("unknown option");
        }
        if (trace.empty() || output.empty() || sites.empty() || !event || !limit || seed > UINT32_MAX)
            throw std::invalid_argument("trace, site, fresh output and valid bounds are required");
        if (format != "pc-taken-target-conditional" && format != "pc-target-taken-conditional")
            throw std::invalid_argument("unknown trace format");
        auto branches = read_trace(trace, format == "pc-target-taken-conditional", limit);
        if (event > branches.size())
            throw std::invalid_argument("forced event lies beyond observed trace");
        if (fs::exists(output))
            throw std::invalid_argument("output exists; use a fresh directory");
        TageAdapter shadow{unsigned(seed)}, fault{unsigned(seed)};
        diag::Layout layout(shadow.core);
        for (size_t i = 0; i + 1 < event; ++i) {
            shadow.step(branches[i]);
            fault.step(branches[i]);
        }
        if (!fault.core.equal(shadow.core) || fault.predictor_rng != shadow.predictor_rng)
            throw std::logic_error("common warm prefix is not equivalent");
        auto before = diag::distance(fault, shadow, layout);
        unsigned multiplicity = inject(fault, layout, sites);
        // Validate first, then create output: invalid events never become partial trials.
        fs::create_directories(output);
        std::ofstream timeline(output/"STATE_DISTANCE_TIMESERIES.csv");
        std::ofstream queries(output/"CAUSAL_LOOKUP_QUERIES.csv");
        timeline << "callback_ordinal,branch_id,pc,conditional,history_updates_since_fault,conditional_history_transitions,"
            "phase,raw_distance,path_distance,nonspec_path_distance,head_difference,fold_invariant_distance,fold_reference_distance,"
            "learning_field_differences,bimodal_prediction_fields,bimodal_hysteresis_fields,"
            "tagged_counter_fields,stored_tag_fields,useful_fields,chooser_fields,allocator_difference,"
            "rng_difference,index_mismatch,query_tag_mismatch,"
            "provider_mismatch,prediction_difference,harmful,helpful,net_extra_misses,"
            "own_cycle,own_sim_tick,trace_kind";
        for (unsigned bank = 1; bank <= layout.folds/3; ++bank)
            timeline << ",index_mismatch_bank_" << bank << ",query_tag_mismatch_bank_" << bank;
        for (unsigned w = 0; w < layout.folds; ++w)
            timeline << ',' << layout.words[w].id << "_invariant_distance," << layout.words[w].id
                     << "_reference_distance";
        timeline << '\n';
        auto detail = [&](const diag::Distance &d, const diag::Query *a, const diag::Query *b) {
            for (unsigned bank = 0; bank < layout.folds/3; ++bank) {
                if (a && b && bank < a->indices.size() && bank < b->indices.size())
                    timeline << ',' << (a->indices[bank] != b->indices[bank]) << ','
                             << (a->tags[bank] != b->tags[bank]);
                else
                    timeline << ",NOT_APPLICABLE,NOT_APPLICABLE";
            }
            for (unsigned w = 0; w < layout.folds; ++w)
                timeline << ',' << d.invariant_by_word[w] << ',' << d.reference_by_word[w];
            timeline << '\n';
        };
        std::ofstream manifest(output/"STATE_AND_EXPOSURE_MANIFEST.csv");
        manifest << "word,name,width,history_length,active_representation,exposure_scope,physical_mapping\n";
        for (unsigned w = 0; w < layout.words.size(); ++w)
            manifest << w << ',' << layout.words[w].id << ',' << layout.words[w].width << ','
                << (w < layout.folds ? std::to_string(layout.lengths[w]) : "NOT_APPLICABLE")
                << ",recurrent,SELECTED_HISTORY_CONDITIONAL,UNKNOWN_HARDWARE_PLACEMENT\n";
        queries << "branch_id,history_updates_since_fault,arm,bank,index,query_tag,provider_type,"
            "selected_provider_bank,hit_bank,alternate_bank,prediction,is_oracle,arm_local_lookup_metadata\n";
        std::array<std::unique_ptr<TageAdapter>, 4> arms;
        std::unique_ptr<TageAdapter> sanity;
        std::array<Outcome, 4> outcomes;
        Outcome natural;
        uint64_t ordinal = 0, updates = 0, conditional_updates = 0, tau = 0;
        bool sanity_pass = true, y11_prediction_equal = true;
        std::set<uint64_t> queried;
        auto learning = [&](const diag::Distance &d) {
            timeline << d.learning_fields() << ',' << d.prediction << ',' << d.hysteresis << ','
                << d.counter << ',' << d.tag << ',' << d.useful << ',' << d.chooser << ','
                << d.allocation_clock << ',' << d.rng;
        };
        auto query_all = [&](size_t i) {
            if (!queried.insert(i).second) return;
            const diag::QueryArm options[] = {diag::QueryArm::Current, diag::QueryArm::OwnInvariant,
                diag::QueryArm::ShadowSource, diag::QueryArm::ShadowLearning};
            const char *names[] = {"Q0", "QF", "QH", "QL"};
            for (unsigned a = 0; a < 4; ++a) {
                auto q = diag::query(fault, shadow, layout, branches[i], options[a]);
                for (size_t bank = 0; bank < q.indices.size(); ++bank)
                    queries << i+1 << ',' << updates << ',' << names[a] << ',' << bank+1 << ','
                        << q.indices[bank] << ',' << q.tags[bank] << ',' << q.provider << ','
                        << q.selected_bank << ',' << q.hit_bank << ',' << q.alternate << ','
                        << q.prediction << ',' << (a != 0) << ",1\n";
            }
        };
        // The pre-event observation is explicit, rather than assumed from a lifetime bound.
        timeline << ordinal++ << ',' << event << ',' << branches[event-1].pc << ','
            << branches[event-1].conditional << ",0,0,PRE_INJECTION," << before.raw << ',' << before.path
            << ',' << before.nonspec_path << ',' << before.head << ',' << before.fold_invariant << ','
            << before.fold_reference << ',';
        learning(before);
        timeline << ',' <<
            "NOT_APPLICABLE,NOT_APPLICABLE,NOT_APPLICABLE,0,0,0,0,"
            "NOT_APPLICABLE,NOT_APPLICABLE,COMMITTED_ONLY_REPLAY";
        detail(before, nullptr, nullptr);
        for (size_t i = event-1; i < branches.size(); ++i) {
            auto d = diag::distance(fault, shadow, layout);
            if (!tau && !d.raw && !d.path && !d.nonspec_path && !d.head) {
                tau = i+1;
                auto faulty = fault.snapshot(), normal = shadow.snapshot();
                for (unsigned a = 0; a < 4; ++a)
                    arms[a] = diag::clone(diag::suffix_arm(faulty, normal, a & 1, a & 2));
                sanity = diag::clone(normal);
                query_all(i);
            }
            if (updates == 0 || updates == 8 || updates == 32 || updates == 128)
                query_all(i);
            const auto &b = branches[i];
            int cursor = fault.core.history_cursor();
            auto normal = step(shadow, b, layout.folds), damaged = step(fault, b, layout.folds);
            bool harmful = b.conditional && normal.prediction == b.taken && damaged.prediction != b.taken;
            bool helpful = b.conditional && normal.prediction != b.taken && damaged.prediction == b.taken;
            natural.observe(damaged.prediction, normal.prediction, b);
            timeline << ordinal++ << ',' << i+1 << ',' << b.pc << ',' << b.conditional << ',' << updates << ',' << conditional_updates
                << ",PRE_LOOKUP," << d.raw << ',' << d.path << ',' << d.nonspec_path << ',' << d.head << ',' << d.fold_invariant << ','
                << d.fold_reference << ',';
            learning(d);
            timeline << ','
                << (b.conditional ? std::to_string(damaged.indices != normal.indices) : "NOT_APPLICABLE") << ','
                << (b.conditional ? std::to_string(damaged.tags != normal.tags) : "NOT_APPLICABLE") << ','
                << (b.conditional ? std::to_string(damaged.provider != normal.provider || damaged.selected_bank != normal.selected_bank) : "NOT_APPLICABLE") << ','
                << (b.conditional && damaged.prediction != normal.prediction) << ',' << harmful << ','
                << helpful << ',' << natural.net() << ",NOT_APPLICABLE,NOT_APPLICABLE,COMMITTED_ONLY_REPLAY";
            detail(d, &damaged, &normal);
            if (tau) {
                for (unsigned a = 0; a < 4; ++a) {
                    bool prediction = arms[a]->step(b);
                    outcomes[a].observe(prediction, normal.prediction, b);
                    if (a == 3) y11_prediction_equal &= prediction == normal.prediction;
                }
                sanity_pass &= sanity->step(b) == normal.prediction;
            }
            bool wrote = cursor != fault.core.history_cursor();
            updates += wrote;
            conditional_updates += wrote && b.conditional;
        }
        auto last = diag::distance(fault, shadow, layout);
        timeline << ordinal << ',' << branches.size()+1 << ",NOT_APPLICABLE,NOT_APPLICABLE," << updates << ',' << conditional_updates
            << ",POST_FINAL_UPDATE," << last.raw << ',' << last.path << ',' << last.nonspec_path << ',' << last.head << ',' << last.fold_invariant
            << ',' << last.fold_reference << ',';
        learning(last);
        timeline << ",NOT_APPLICABLE,NOT_APPLICABLE,NOT_APPLICABLE,0,0,0," << natural.net()
            << ",NOT_APPLICABLE,NOT_APPLICABLE,COMMITTED_ONLY_REPLAY";
        detail(last, nullptr, nullptr);
        if (tau)
            sanity_pass &= sanity->core.equal(shadow.core) && sanity->predictor_rng == shadow.predictor_rng;
        std::ofstream suffix(output/"CAUSAL_SUFFIX_ARMS.csv"), effects(output/"CAUSAL_INTERACTIONS.csv");
        suffix << "arm,tau_branch_id,harmful,helpful,net_extra_misses,single_intervention_only,"
            "all_live_source_copies_aligned,is_oracle,trace_kind\n";
        effects << "tau_branch_id,fold_effect_given_faulty_learning,learning_effect_given_faulty_folds,"
            "joint_removable_effect,interaction,outcome_unit,trace_kind\n";
        const char *names[] = {"Y00", "Y10", "Y01", "Y11"};
        if (tau) {
            for (unsigned a = 0; a < 4; ++a)
                suffix << names[a] << ',' << tau << ',' << outcomes[a].harmful << ',' << outcomes[a].helpful
                    << ',' << outcomes[a].net() << ",1,1," << (a != 0) << ",COMMITTED_ONLY_REPLAY\n";
            auto y0 = outcomes[0].net(), yf = outcomes[1].net(), yl = outcomes[2].net(), yfl = outcomes[3].net();
            effects << tau << ',' << y0-yf << ',' << y0-yl << ',' << y0-yfl << ',' << y0-yf-yl+yfl
                << ",signed_net_extra_misses,COMMITTED_ONLY_REPLAY\n";
        }
        std::ofstream summary(output/"case.json");
        bool valid_partition = !tau || y11_prediction_equal;
        summary << "{\"execution_status\":\"" << (sanity_pass && valid_partition ? "COMPLETE" : "FAILED")
            << "\",\"trace_kind\":\"COMMITTED_ONLY_REPLAY\",\"speculation\":\"REMOVED\","
            "\"CPU_performance_result\":false,\"pre_fault_observed\":true,"
            "\"restorable_live_copies\":\"NOT_APPLICABLE_QUIESCENT_REPLAY\","
            "\"own_cycle\":null,\"own_sim_tick\":null,\"timing_recovery\":\"NOT_APPLICABLE\","
            "\"source_loss_observation_kind\":\"COMMON_REPLAY_SEMANTIC_ACTIVE_HISTORY\","
            "\"physical_cell_overwrite_time\":null,"
            "\"site\":" << std::quoted(sites) << ",\"applied_events\":1,\"applied_flips\":" << multiplicity
            << ",\"predictor_seed\":" << seed << ",\"trace_format\":" << std::quoted(format)
            << ",\"event_branch\":" << event
            << ",\"observation_end_branch\":" << branches.size()
            << ",\"tau_branch\":" << (tau ? std::to_string(tau) : "null")
            << ",\"all_state_sanity_status\":\"" << (tau ? sanity_pass ? "PASS" : "FAIL" : "NOT_OBSERVED")
            << "\",\"Y11_prediction_equals_shadow\":" << (!tau ? "null" : y11_prediction_equal ? "true" : "false")
            << ",\"harmful\":" << natural.harmful << ",\"helpful\":" << natural.helpful
            << ",\"net_extra_misses\":" << natural.net() << "}\n";
        std::cout << "case=" << output.filename() << " suffix_tau=" << tau
                  << " net_extra_misses=" << natural.net() << " sanity=" << sanity_pass
                  << " COMMITTED_ONLY_REPLAY_NOT_CPU\n";
        return sanity_pass && valid_partition ? 0 : 1;
    } catch (const std::exception &error) {
        std::cerr << "ERROR " << error.what() << '\n';
        return 1;
    }
}
