#pragma once
#include "cpu/pred/conditional.hh"
#include "params/BimodalMin.hh"
#include "sim/eventq.hh"
#include "tage/predictor/bimodal.hpp"

namespace bp {
class BimodalMin : public gem5::branch_prediction::ConditionalPredictor {
    struct Info { bool conditional; };
    Bimodal table_;
    std::string summary_path_;
    gem5::Tick fault_tick_;
    uint64_t fault_site_, applied_ = 0, retired_ops_ = 0, retired_inst_ = 0;
    uint64_t identity_ = 14695981039346656037ULL, lookups_ = 0, updates_ = 0;
    bool frozen_ = false;
    gem5::EventFunctionWrapper injection_;
  public:
    explicit BimodalMin(const gem5::BimodalMinParams &);
    ~BimodalMin() override { if (injection_.scheduled()) deschedule(injection_); }
    void startup() override;
    bool lookup(gem5::ThreadID, gem5::Addr, void *&) override;
    void updateHistories(gem5::ThreadID, gem5::Addr, bool, bool, gem5::Addr,
                         const gem5::StaticInstPtr &, void *&) override;
    void branchPlaceholder(gem5::ThreadID, gem5::Addr, bool, void *&) override;
    void update(gem5::ThreadID, gem5::Addr, bool, void *&, bool,
                const gem5::StaticInstPtr &, gem5::Addr) override;
    void squash(gem5::ThreadID, void *&) override;
    void seuAuditCommit(uint64_t, uint64_t, unsigned, bool, bool, void *) override;
    void dumpResearch();
};
} // namespace bp
