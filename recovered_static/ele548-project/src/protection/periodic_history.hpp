#pragma once
#include "history_controller.hpp"

namespace bp {
// Optional research policy. The legacy controller and its frozen sources are
// unchanged. Periodic inspection is enabled only for ED, on the same 23 words.
class PeriodicHistoryController {
    TageAccess& core;
    HistoryController base;
    std::vector<size_t> parity_ids;
    std::vector<bool> old_syndrome;
    bool writing=false;
    std::vector<StoredSite> extras;
    void finish_write(bool committed) {
        if(!interval) {
            if(committed)base.after_history_write();
            else base.after_speculative_history_write();
            return;
        }
        if(!writing)throw std::logic_error("periodic write missing begin");
        if(committed)base.after_history_write();
        else base.after_speculative_history_write();
        // base re-encodes the new payload. Reapply the OLD parity residual,
        // giving p_new = p_old XOR parity(data_old) XOR parity(data_new).
        // This is legitimate sidecar update, not an injected event; IDs are
        // the controller's own parity cells, never the injector's schedule.
        std::vector<size_t> toggle;
        for(unsigned w=0;w<old_syndrome.size();++w)
            if(old_syndrome[w])toggle.push_back(parity_ids[w]);
        base.corrupt(toggle);
        writing=false;
        if(progress<interval)++progress; // Saturate even after a counter SEU.
        ++history_writes;
    }
 public:
    const unsigned interval; // Synthesis/configuration constant, no stored bit.
    const Scheme scheme;
    const bool cpu_protocol;
    uint8_t& refill;
    uint32_t& epoch;
    bool& recovery_active;
    ProtectionStats& stats;
    uint8_t progress=0; // Eight real, separately exposed policy bits.
    uint64_t history_writes=0,inspections=0,skipped_calls=0;
    uint64_t delta_word_reads=0,delta_sidecar_reads=0,delta_parity_operations=0;
    explicit PeriodicHistoryController(TageAccess& c,Scheme s,bool cpu=false,unsigned k=0)
        :core(c),base(c,s,cpu),interval(k),scheme(s),cpu_protocol(cpu),
         refill(base.refill),epoch(base.epoch),recovery_active(base.recovery_active),stats(base.stats) {
        if(k>64||(k&&s!=Scheme::ED))throw std::invalid_argument("periodic ED interval1..64 only");
        extras=base.additional_sites();
        if(k) {
            for(const auto& site:extras)if(site.structure=="parity")parity_ids.push_back(site.id);
            if(parity_ids.size()!=specs().size())throw std::logic_error("periodic parity geometry");
            old_syndrome.resize(specs().size());
            size_t id=base.exposed_bits();
            for(unsigned bit=0;bit<8;++bit)extras.push_back({id++,"inspection_progress",0,bit,8,0});
        }
    }
    struct Snapshot {
        HistoryController::Snapshot base;
        uint8_t progress;
        uint64_t history_writes,inspections,skipped_calls,delta_word_reads,delta_sidecar_reads,delta_parity_operations;
    };
    Snapshot snapshot()const {
        if(writing)throw std::logic_error("snapshot inside atomic write");
        return {base.snapshot(),progress,history_writes,inspections,skipped_calls,
                delta_word_reads,delta_sidecar_reads,delta_parity_operations};
    }
    void restore(const Snapshot& s) {
        if(writing)throw std::logic_error("restore inside atomic write");
        base.restore(s.base);progress=s.progress;history_writes=s.history_writes;
        inspections=s.inspections;skipped_calls=s.skipped_calls;
        delta_word_reads=s.delta_word_reads;delta_sidecar_reads=s.delta_sidecar_reads;
        delta_parity_operations=s.delta_parity_operations;
    }
    bool inspection_due()const{return !interval||progress>=interval;}
    bool check(bool prediction_boundary=false) {
        if(!interval)return base.check();
        if(writing)throw std::logic_error("inspection inside atomic update");
        if(!prediction_boundary||!inspection_due()) {
            ++skipped_calls;core.tagged_enabled(!fallback());return false;
        }
        progress=0;++inspections;return base.check();
    }
    void begin_history_write() {
        if(!interval)return;
        if(writing)throw std::logic_error("nested periodic update");
        writing=true;
        for(unsigned w=0;w<specs().size();++w) {
            old_syndrome[w]=core.read_history_word(w).parity()^bool(base.stored_check(w));
            ++delta_word_reads;++delta_sidecar_reads;++delta_parity_operations;
        }
    }
    void after_speculative_history_write(){finish_write(false);}
    void after_history_write(){finish_write(true);}
    bool fallback()const{return base.fallback();}
    void complete_cpu_drain(){base.complete_cpu_drain();}
    void prediction(){base.prediction();}
    void synchronize(){base.synchronize();}
    const std::vector<TageAccess::HistoryWord>& specs()const{return base.specs();}
    const std::vector<StoredSite>& additional_sites()const{return extras;}
    size_t exposed_bits()const{return base.exposed_bits()+(interval?8:0);}
    void corrupt(const std::vector<size_t>& ids) {
        std::set<size_t> unique;std::vector<size_t> ordinary;
        for(auto id:ids)if(id>=exposed_bits()||!unique.insert(id).second)
            throw std::invalid_argument("invalid/duplicate periodic logical event");
        for(auto id:ids)if(id<base.exposed_bits())ordinary.push_back(id);
        base.corrupt(ordinary);
        for(auto id:ids)if(id>=base.exposed_bits())progress^=uint8_t(1)<<(id-base.exposed_bits());
    }
    bool logical_bit(size_t id)const {
        if(id>=exposed_bits())throw std::out_of_range("periodic logical bit");
        return id<base.exposed_bits()?base.logical_bit(id):bool((progress>>(id-base.exposed_bits()))&1);
    }
    uint16_t stored_check(unsigned w)const{return base.stored_check(w);}
};
}
