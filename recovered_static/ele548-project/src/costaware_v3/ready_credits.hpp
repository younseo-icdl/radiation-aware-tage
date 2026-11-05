#pragma once
#include "../protection/word.hpp"
#include "finite_fifo.hpp"
namespace bp {
// Each protected 48-bit word holds sixteen 3-bit pending-operation credits.
// The original CPU BranchInfo payload remains in the declared shared scope.
class ReadyCredits {
 std::vector<Word> data;std::vector<uint16_t> checks;WordSecded code{48};
 Word read(unsigned group){auto d=code.decode(data.at(group),checks.at(group));if(d.due)throw QueueIntegrityError("pending-credit DUE");if(d.corrected){++corrected;data[group]=d.payload;checks[group]=d.check;}return data[group];}
 public:
 const unsigned slots;uint64_t corrected=0;
 explicit ReadyCredits(unsigned n):data((n+15)/16),checks((n+15)/16),slots(n){for(unsigned j=0;j<data.size();++j)checks[j]=code.encode(data[j]);}
 unsigned get(unsigned id){if(id>=slots)throw QueueIntegrityError("invalid CPU metadata handle");auto w=read(id/16);unsigned r=0;for(unsigned i=0;i<3;++i)r|=unsigned(w.bit((id%16)*3+i))<<i;return r;}
 void set(unsigned id,unsigned value){if(id>=slots||value>7)throw QueueIntegrityError("invalid credit value");auto w=read(id/16);for(unsigned i=0;i<3;++i)w.set((id%16)*3+i,(value>>i)&1);data[id/16]=w;checks[id/16]=code.encode(w);}
 void increment(unsigned id){auto n=get(id);if(n==7)throw QueueIntegrityError("pending credit capacity exceeded");set(id,n+1);}
 void decrement(unsigned id){auto n=get(id);if(!n)throw QueueIntegrityError("pending credit underflow");set(id,n-1);}
 void clear(){for(unsigned j=0;j<data.size();++j){data[j]={};checks[j]=code.encode(data[j]);}}
 size_t bits()const{return data.size()*(48+code.r+1);}
 bool bit(size_t id)const{if(id>=bits())throw std::out_of_range("credit bit");unsigned row=id/(48+code.r+1),b=id%(48+code.r+1);return b<48?data[row].bit(b):((checks[row]>>(b-48))&1);}
 void flip(size_t id){if(id>=bits())throw std::out_of_range("credit bit");unsigned row=id/(48+code.r+1),b=id%(48+code.r+1);if(b<48)data[row].flip(b);else checks[row]^=uint16_t(1)<<(b-48);}
};
}
