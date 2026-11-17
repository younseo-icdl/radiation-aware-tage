#pragma once
#include "tage/predictor/tage_access.hpp"
#include <cstdint>

namespace bp {
// First lease protocol: stop new admissions, drain actual restore owners, then
// charge a finite service interval and publish Phi(current own H). No oracle.
class QuiescentLease {
    uint32_t period_, age_ = 0;
    uint64_t latency_, ready_ = 0, last_time_ = 0;
    bool busy_ = false;
  public:
    uint64_t publications = 0, drain_wait_calls = 0, service_wait_calls = 0;
    explicit QuiescentLease(uint32_t period, uint64_t latency)
        : period_(period), latency_(latency) {
        if(period>65535 || (period && !latency))
            throw std::invalid_argument("lease period/latency");
    }
    bool due() const { return period_ && (busy_ || age_>=period_); }
    bool enabled() const { return period_ != 0; }
    bool busy() const { return busy_; }
    uint64_t ready_time() const { return ready_; }
    uint32_t age() const { return age_; }
    unsigned age_bits() const {
        unsigned bits=0; for(auto value=period_;value;value>>=1) ++bits; return bits;
    }
    void append(unsigned count) {
        if(busy_ && count) throw std::logic_error("history append during quiescent service");
        if(period_ && age_<period_) age_=std::min(uint64_t(period_),uint64_t(age_)+count);
    }
    void xor_age(unsigned bit) {
        if(bit>=age_bits()) throw std::out_of_range("lease age bit");
        age_^=uint32_t(1)<<bit;
    }
    template<class Publish> bool service(uint64_t now, bool no_restore_owners, Publish publish) {
        if(now<last_time_) throw std::logic_error("lease time reversed");
        last_time_=now;
        if(!due()) return true;
        if(busy_ && !no_restore_owners)
            throw std::logic_error("restore owner entered quiescent service");
        if(!no_restore_owners) {++drain_wait_calls;return false;}
        if(!busy_) {
            if(latency_>UINT64_MAX-now) throw std::overflow_error("lease completion tick overflow");
            busy_=true;ready_=now+latency_;
        }
        if(now<ready_) {++service_wait_calls;return false;}
        publish(); // Publish at a real charged completion boundary, from own H.
        age_=0;busy_=false;++publications;
        return true;
    }
};

inline void publish_own_folds(TageAccess &core,
                              const std::vector<TageAccess::HistoryWord> &words,
                              unsigned bank_mask=127) {
    if(words.size()!=23) throw std::invalid_argument("plain seven-bank lease scope");
    if(bank_mask>=128) throw std::invalid_argument("lease bank mask");
    if(!bank_mask) return;
    auto raw=core.read_history_word(21);
    std::array<Word,21> folds{};
    for(unsigned w=0;w<21;++w) if((bank_mask>>(w/3))&1)
        for(unsigned age=0;age<core.fold_history_length(w);++age)
            if(raw.bit(age)) folds[w].flip(age%words[w].width);
    for(unsigned w=0;w<21;++w) if((bank_mask>>(w/3))&1) core.write_history_word(w,folds[w]);
}
inline void publish_own_folds(TageAccess &core) {
    publish_own_folds(core,core.history_words());
}
} // namespace bp
