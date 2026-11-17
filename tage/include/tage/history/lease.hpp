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
    bool busy() const { return busy_; }
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
        if(!busy_) {busy_=true;ready_=now+latency_;}
        if(now<ready_) {++service_wait_calls;return false;}
        publish(); // Publish at a real charged completion boundary, from own H.
        age_=0;busy_=false;++publications;
        return true;
    }
};

inline void publish_own_folds(TageAccess &core) {
    auto words=core.history_words();
    if(words.size()!=23) throw std::invalid_argument("plain seven-bank lease scope");
    auto raw=core.read_history_word(21);
    std::array<Word,21> folds{};
    for(unsigned w=0;w<21;++w)
        for(unsigned age=0;age<core.fold_history_length(w);++age)
            if(raw.bit(age)) folds[w].flip(age%words[w].width);
    for(unsigned w=0;w<21;++w) core.write_history_word(w,folds[w]);
}
} // namespace bp
