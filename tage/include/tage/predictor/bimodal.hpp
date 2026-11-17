#pragma once
#include <cstdint>
#include <stdexcept>
#include <vector>

namespace bp {
// Same prediction-bit/shared-hysteresis update as ordinary TAGE's base table.
// No raw/path history, tagged tables, chooser, fold, or speculative checkpoint.
class Bimodal {
    unsigned log_size_, ratio_;
  public:
    std::vector<bool> prediction, hysteresis;
    explicit Bimodal(unsigned log_size = 13, unsigned ratio = 2)
        : log_size_(log_size), ratio_(ratio) {
        if (log_size > 20 || log_size < 1 || ratio > log_size)
            throw std::invalid_argument("bimodal geometry");
        prediction.assign(size_t(1)<<log_size, false);
        hysteresis.assign(size_t(1)<<(log_size-ratio), true);
    }
    unsigned index(uint64_t pc) const { return pc & ((1u<<log_size_)-1); }
    bool predict(uint64_t pc) const { return prediction[index(pc)]; }
    void update(uint64_t pc, bool taken) {
        unsigned row = index(pc), h = row>>ratio_;
        unsigned value = unsigned(prediction[row])*2+unsigned(hysteresis[h]);
        if (taken) { if (value < 3) ++value; }
        else if (value) --value;
        prediction[row] = value>>1; hysteresis[h] = value&1;
    }
    void flip(size_t site) {
        if (site < prediction.size()) prediction[site] = !prediction[site];
        else if (site-prediction.size() < hysteresis.size()) {
            site -= prediction.size(); hysteresis[site] = !hysteresis[site];
        } else throw std::out_of_range("bimodal site");
    }
    size_t bits() const { return prediction.size()+hysteresis.size(); }
};
} // namespace bp
