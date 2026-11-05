#pragma once
#include "tage/pipeline/controller.hpp"
#include "tage/pipeline/early_receiver.hpp"
#include "tage/pipeline/source_protection.hpp"
#include "tage/history/history_access.hpp"
#include <memory>
namespace bp::pipeline {
// Shared implementation used by real gem5 core and standalone reference gate.
// Parent's fold/path fields are provider combinational scratch only. There is
// no authoritative second raw/fold source or saved recovery payload there.
template <class Parent> class SourceAccess : public Parent {
  public:
    std::unique_ptr<Controller> engine;
    std::unique_ptr<EarlyReceiver> early;
    std::array<Base::BranchInfo *, 4> host_owners{};
    uint64_t fallback_commits = 0, stale_training_suppressed = 0, stale_source_suppressed = 0,
             refill_drains = 0;
    template <class Params> explicit SourceAccess(const Params &p) : Parent(p) {}
    void configure(Mode mode, unsigned UL, unsigned QL, unsigned id = 16, unsigned epoch = 16) {
        if (engine || this->nHistoryTables != 7 || this->pathHistBits != 16 ||
            this->takenOnlyHistory)
            throw std::invalid_argument("finite plain TAGE scope");
        std::vector<Geometry> geometry;
        auto words = this->history_words();
        for (unsigned w = 0; w < 21; ++w)
            geometry.push_back({this->fold_length(w), words[w].width});
        engine = std::make_unique<Controller>(mode, geometry, UL, QL, id, epoch);
    }
    void enable_early() {
        if (!engine || early)
            throw IntegrityError("early configuration");
        early = std::make_unique<EarlyReceiver>(*engine);
    }
    void enable_protection(Protect p, Mode mode, unsigned epoch_bits = 32) {
        auto &source = engine->port.source;
        source.attach_guard(std::make_unique<FiniteProtection>(source.selected_widths(), p,
                                                               mode == Mode::Direct, epoch_bits));
    }
    FiniteProtection *protection() {
        return dynamic_cast<FiniteProtection *>(engine->port.source.guard());
    }
    bool fallback() {
        auto *g = engine->port.source.guard();
        return g && g->fallback();
    }
    bool refill_complete() {
        auto *g = protection();
        return g && g->unit.fallback() && g->unit.refill_remaining() == 0;
    }
    bool frontend_blocked(bool actual_cpu_history_empty) {
        auto *g = protection();
        if (!g || !g->unit.fallback() || g->unit.refill_remaining())
            return false;
        // Finish requests already issued before the refill barrier. A token0 NEW
        // request is blocked separately in the actual CPU admission interface.
        if (engine->port.pending() || (early && early->pending()))
            return false;
        if (!actual_cpu_history_empty || !drained() || engine->port.source.source_depth())
            return true;
        g->acknowledge_refill_and_epoch_drained();
        ++refill_drains;
        this->tagged_enabled(true);
        return false;
    }
    transport::Payload provider(uint64_t pc, bool conditional, const std::array<unsigned, 21> &fold,
                                unsigned path) {
        this->tagged_enabled(!fallback());
        for (unsigned w = 0; w < 21; ++w) {
            Word value;
            value.limb[0] = fold[w];
            this->write_history_word(w, value);
        }
        Word value;
        value.limb[0] = path;
        this->write_history_word(22, value);
        auto *bi = this->makeBranchInfo(pc, conditional);
        bi->pathHist = path;
        bool prediction = this->tagePredict(0, pc, conditional, bi);
        transport::Payload result;
        result.capture_response(*bi);
        result.put(25, prediction);
        delete bi;
        return result;
    }
    void advance() {
        engine->advance([this](auto pc, auto conditional, const auto &fold, auto path) {
            return provider(pc, conditional, fold, path);
        });
        if (early)
            early->advance([this](unsigned slot, unsigned path) {
                if (!host_owners[slot])
                    throw IntegrityError("late CPU owner missing");
                host_owners[slot]->pathHist = path;
                host_owners[slot] = nullptr;
            });
    }
    std::optional<Token> request(uint64_t pc, bool conditional) {
        return early && !early->ready() ? std::optional<Token>{} : engine->request(pc, conditional);
    }
    bool early_ready(Token token, uint64_t pc) { return early && early->claimable(token, pc); }
    Base::BranchInfo *consume_early(uint64_t pc, Base::BranchInfo *existing = nullptr) {
        if (!early)
            throw IntegrityError("early disabled");
        auto slot = early->claim(pc);
        if (!slot || host_owners[*slot])
            throw IntegrityError("early owner slot unavailable");
        auto *bi = existing ? existing : this->makeBranchInfo(pc, false);
        if (bi->branchPC != pc || bi->condBranch || !this->tagePredict(0, pc, false, bi))
            throw IntegrityError("pinned unconditional direction/owner changed");
        host_owners[*slot] = bi;
        return bi;
    }
    bool prepare_recovery() { return (!early || early->quiescent()) && engine->prepare_recovery(); }
    bool can_retire(unsigned n) {
        return (!early || early->quiescent()) && engine->can_retire(n) &&
               (!fallback() || engine->committed_ready());
    }
    bool retire(unsigned n) { return can_retire(n) && engine->retire(n); }
    // Called at ACTUAL architectural retirement, with a resolved BPU outcome.
    // Check and enqueue are non-yielding. Training may arrive later or in a batch;
    // it cannot consume a credit checked several CPU cycles earlier.
    bool retire_with_outcome(unsigned n, bool actual, uint64_t pc) {
        if (!can_retire(n))
            return false;
        const bool refill = fallback();
        if (!engine->retire(n))
            throw IntegrityError("retirement lost checked source credit");
        if (refill) {
            engine->committed_history(actual, (pc >> this->instShiftAmt) & 1);
            ++fallback_commits;
        }
        return true;
    }
    void cancel() {
        if (early)
            early->cancel();
        else
            engine->cancel();
    }
    bool drained() { return (!early || early->quiescent()) && engine->drained(); }
    bool conserved() { return engine->conserved() && (!early || early->conserved()); }
    std::vector<Service::Region> model_manifest() const {
        auto r = engine->manifest();
        if (early) {
            auto more = early->manifest();
            for (auto &e : more) {
                e.start += engine->bits();
                r.push_back(e);
            }
        }
        return r;
    }
    size_t model_bits() const { return engine->bits() + (early ? early->bits() : 0); }
    bool model_bit(size_t n) const {
        if (n >= model_bits())
            throw std::out_of_range("model bit");
        return n < engine->bits() ? engine->logical_bit(n) : early->logical_bit(n - engine->bits());
    }
    void corrupt_model(const std::vector<size_t> &ids) {
        std::set<size_t> unique;
        std::vector<size_t> a, b;
        for (auto id : ids) {
            if (id >= model_bits() || !unique.insert(id).second)
                throw std::invalid_argument("model atomic sites");
            (id < engine->bits() ? a : b).push_back(id < engine->bits() ? id : id - engine->bits());
        }
        engine->corrupt(a);
        if (early)
            early->corrupt(b);
    }
    Base::BranchInfo *consume(Token token) {
        auto r = engine->take(token);
        if (!r)
            throw IntegrityError("consume before owned source/provider response");
        auto *bi = this->makeBranchInfo(r->pc, r->conditional);
        r->payload.restore_response(*bi);
        bi->pathHist = r->path;
        return bi;
    }
    void recordHistState(gem5::ThreadID tid, Base::BranchInfo *) override {
        if (tid)
            throw std::invalid_argument(
                "single-thread finite TAGE"); /* captured actual path is already in consumed BI */
    }
    void updatePathAndGlobalHistory(gem5::ThreadID tid, int, bool taken, gem5::Addr pc, gem5::Addr,
                                    Base::BranchInfo *bi) override {
        if (tid)
            throw std::invalid_argument("single-thread finite TAGE");
        bi->ghist = taken ? 1 : 0;
        if (fallback()) {
            bi->nGhist = 0;
            ++stale_source_suppressed;
            return;
        }
        bi->nGhist = 1;
        engine->append(1, bi->ghist, (pc >> this->instShiftAmt) & 1);
    }
    void condBranchUpdate(gem5::ThreadID tid, gem5::Addr pc, bool taken, Base::BranchInfo *bi,
                          int nrand, gem5::Addr target, bool pred, bool pre = false) override {
        if (fallback()) {
            this->fallback_update(pc, taken, bi, nrand);
            ++stale_training_suppressed;
            return;
        }
        Parent::condBranchUpdate(tid, pc, taken, bi, nrand, target, pred, pre);
    }
    void updateHistories(gem5::ThreadID tid, gem5::Addr pc, bool speculative, bool taken,
                         gem5::Addr target, const gem5::StaticInstPtr &inst,
                         Base::BranchInfo *bi) override {
        // Recovery history is queued at actual retirement. This delayed BPU training
        // callback must not publish it a second time or introduce pre-reset commits.
        Parent::updateHistories(tid, pc, speculative, taken, target, inst, bi);
    }
    void updateGHist(gem5::ThreadID, uint64_t, uint8_t) override {
        throw IntegrityError("finite source requires atomic path/global command");
    }
    void restoreHistState(gem5::ThreadID tid, Base::BranchInfo *bi) override {
        if (tid)
            throw std::invalid_argument("single-thread finite TAGE");
        if (!this->speculativeHistUpdate || !bi->modified)
            return;
        unsigned n = bi->nGhist;
        engine->restore(n, bi->pathHist);
        if (n) {
            bi->nGhist = 0;
            bi->modified = false;
        }
    }
};
} // namespace bp::pipeline
