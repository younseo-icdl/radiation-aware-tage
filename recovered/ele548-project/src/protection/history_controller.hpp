#pragma once
#include "../predictor/tage_access.hpp"
#include <map>
#include <functional>

namespace bp {
enum class Scheme { P0,ED,ECC,TMR };
inline Scheme scheme_from(const std::string& name){if(name=="P0")return Scheme::P0;if(name=="P_ED")return Scheme::ED;if(name=="P_ECC")return Scheme::ECC;if(name=="P_TMR")return Scheme::TMR;throw std::invalid_argument("unknown scheme");}
inline const char* scheme_name(Scheme s){return s==Scheme::P0?"P0":s==Scheme::ED?"P_ED":s==Scheme::ECC?"P_ECC":"P_TMR";}
struct ProtectionStats {
    uint64_t checks=0,word_reads=0,word_writes=0,detected=0,corrected=0,due=0,reset_refill=0;
    uint64_t repair_words=0,replica_repairs=0,refill_updates=0,fallback_predictions=0;
    uint64_t sidecar_reads=0,sidecar_writes=0,encode_words=0,voted_words=0;
};
struct StoredSite {size_t id;std::string structure;unsigned word,bit,width,replica;};

class HistoryController {
    TageAccess& core;
    std::vector<TageAccess::HistoryWord> words;
    std::vector<WordSecded> codecs;
    std::vector<uint16_t> checks;
    std::vector<Word> replica1,replica2;
    std::vector<Site> base_sites;
    std::vector<StoredSite> extra_sites;
    void reset_refill(){
        core.reset_selected_history();refill=core.history_depth();++epoch;++stats.reset_refill;
        if(cpu_protocol)recovery_active=true;
        synchronize();
    }
 public:
    const Scheme scheme;
    const bool cpu_protocol;
    uint8_t refill=0;
    uint32_t epoch=0;
    bool recovery_active=false;
    ProtectionStats stats;
    explicit HistoryController(TageAccess& state,Scheme s,bool cpu=false):core(state),words(state.history_words()),scheme(s),cpu_protocol(cpu){
        for(const auto& w:words)codecs.emplace_back(w.width);
        checks.resize(words.size());replica1.resize(words.size());replica2.resize(words.size());synchronize();
        base_sites=core.sites();extra_sites=make_additional_sites();
        if(core.history_depth()>255)throw std::invalid_argument("refill exceeds 8-bit controller");
    }
    struct Snapshot {std::vector<uint16_t> checks;std::vector<Word> a,b;uint8_t refill;uint32_t epoch;bool recovery_active;ProtectionStats stats;};
    Snapshot snapshot()const{return {checks,replica1,replica2,refill,epoch,recovery_active,stats};}
    void restore(const Snapshot& s){if(s.checks.size()!=words.size()||s.a.size()!=words.size()||s.b.size()!=words.size())throw std::invalid_argument("protection snapshot");checks=s.checks;replica1=s.a;replica2=s.b;refill=s.refill;epoch=s.epoch;recovery_active=s.recovery_active;stats=s.stats;core.tagged_enabled(!fallback());}
    bool fallback()const{return (scheme==Scheme::ED||scheme==Scheme::ECC)&&(refill!=0||(cpu_protocol&&recovery_active));}
    void complete_cpu_drain(){if(!cpu_protocol||refill)throw std::logic_error("premature history drain");recovery_active=false;core.tagged_enabled(!fallback());}
    const std::vector<TageAccess::HistoryWord>& specs()const{return words;}
    // Only called after legitimate history writes/reset. Never called by
    // the fault injector and never refreshes parity on a mere read.
    void synchronize(){
        if(scheme==Scheme::P0)return;
        for(unsigned i=0;i<words.size();++i){auto data=core.read_history_word(i);
            if(scheme==Scheme::ED)checks[i]=data.parity();
            else if(scheme==Scheme::ECC)checks[i]=codecs[i].encode(data);
            else replica1[i]=replica2[i]=data;
        }
    }
    // Same atomic read/check/correct/fallback policy for lookup and history RMW.
    // No event ID, injected K, or golden state is visible to this detector.
    bool check(){
        if(scheme==Scheme::P0)return false;
        ++stats.checks;bool bad=false;
        for(unsigned i=0;i<words.size();++i){auto data=core.read_history_word(i);stats.word_reads+=scheme==Scheme::TMR?3:1;
            if(scheme==Scheme::ED||scheme==Scheme::ECC)++stats.sidecar_reads;
            if(scheme==Scheme::ED){if(data.parity()!=bool(checks[i])){++stats.detected;bad=true;}}
            else if(scheme==Scheme::ECC){auto result=codecs[i].decode(data,checks[i]);
                if(result.due){++stats.detected;++stats.due;bad=true;}
                else if(result.corrected){++stats.detected;++stats.corrected;++stats.repair_words;
                    core.write_history_word(i,result.payload);checks[i]=result.check;++stats.word_writes;++stats.sidecar_writes;}}
            else{auto voted=majority(data,replica1[i],replica2[i]);
                ++stats.voted_words;
                if(data!=replica1[i]||data!=replica2[i]){
                    ++stats.detected;++stats.corrected;++stats.repair_words;
                    stats.replica_repairs+=(data!=voted)+(replica1[i]!=voted)+(replica2[i]!=voted);
                    core.write_history_word(i,voted);replica1[i]=replica2[i]=voted;stats.word_writes+=3;
                }}
        }
        if(bad){reset_refill();stats.word_writes+=words.size();stats.sidecar_writes+=words.size();stats.encode_words+=words.size();}
        core.tagged_enabled(!fallback());return bad;
    }
    void after_speculative_history_write(){
        stats.word_writes+=words.size()*(scheme==Scheme::TMR?3:1);
        if(scheme==Scheme::ED||scheme==Scheme::ECC){stats.sidecar_writes+=words.size();stats.encode_words+=words.size();}
        synchronize();
    }
    void after_history_write(){
        after_speculative_history_write();
        if(refill&&(scheme==Scheme::ED||scheme==Scheme::ECC)){--refill;++stats.refill_updates;core.tagged_enabled(!fallback());}
    }
    void prediction(){if(fallback())++stats.fallback_predictions;}
    std::vector<StoredSite> make_additional_sites()const {
        std::vector<StoredSite> out;size_t id=base_sites.size();
        if(scheme==Scheme::ED||scheme==Scheme::ECC){
            for(unsigned w=0;w<words.size();++w){unsigned width=scheme==Scheme::ED?1:codecs[w].r+1;
                for(unsigned bit=0;bit<width;++bit)out.push_back({id++,scheme==Scheme::ED?"parity":"secded_check",w,bit,width,0});}
            for(unsigned bit=0;bit<8;++bit)out.push_back({id++,"refill_remaining",0,bit,8,0});
            for(unsigned bit=0;bit<32;++bit)out.push_back({id++,"history_epoch",0,bit,32,0});
            if(cpu_protocol)out.push_back({id++,"recovery_active",0,0,1,0});
        }else if(scheme==Scheme::TMR){
            for(unsigned rep=1;rep<=2;++rep)for(unsigned w=0;w<words.size();++w)
                for(unsigned bit=0;bit<words[w].width;++bit)out.push_back({id++,"replica",w,bit,words[w].width,rep});
        }
        return out;
    }
    const std::vector<StoredSite>& additional_sites()const{return extra_sites;}
    size_t exposed_bits()const{return base_sites.size()+extra_sites.size();}
    void corrupt(const std::vector<size_t>& ids){
        std::set<size_t> unique;
        for(auto id:ids)if(id>=exposed_bits()||!unique.insert(id).second)throw std::invalid_argument("invalid/duplicate protection event");
        // Validate entire event before applying any base/check/replica flips.
        for(auto id:ids){
            if(id<base_sites.size()){const auto& s=base_sites[id];core.write_payload(s,core.payload(s)^(1u<<s.bit));continue;}
            const auto& s=extra_sites[id-base_sites.size()];
            if(s.structure=="parity"||s.structure=="secded_check")checks[s.word]^=uint16_t(1)<<s.bit;
            else if(s.structure=="refill_remaining")refill^=uint8_t(1)<<s.bit;
            else if(s.structure=="history_epoch")epoch^=uint32_t(1)<<s.bit;
            else if(s.structure=="recovery_active")recovery_active=!recovery_active;
            else(s.replica==1?replica1[s.word]:replica2[s.word]).flip(s.bit);
        }
    }
    bool logical_bit(size_t id)const{
        if(id>=exposed_bits())throw std::out_of_range("logical protection bit");
        if(id<base_sites.size()){auto& s=base_sites[id];return (core.payload(s)>>s.bit)&1;}
        const auto& s=extra_sites[id-base_sites.size()];
        if(s.structure=="parity"||s.structure=="secded_check")return (checks[s.word]>>s.bit)&1;
        if(s.structure=="refill_remaining")return (refill>>s.bit)&1;
        if(s.structure=="history_epoch")return (epoch>>s.bit)&1;
        if(s.structure=="recovery_active")return recovery_active;
        return (s.replica==1?replica1[s.word]:replica2[s.word]).bit(s.bit);
    }
    // Debug-only exact replica/check access for tests and manifest audits.
    uint16_t stored_check(unsigned w)const{return checks.at(w);}
    Word stored_replica(unsigned w,unsigned rep)const{return rep==0?core.read_history_word(w):(rep==1?replica1.at(w):replica2.at(w));}
};
} // namespace bp
