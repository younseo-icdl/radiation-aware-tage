#pragma once
#include <cstdint>
#include <vector>
#include <stdexcept>
namespace bp {
class GshareAdapter {
 public:
 static constexpr unsigned history_bits=17,entries=1u<<history_bits;
 uint32_t history=0;std::vector<uint8_t> counters=std::vector<uint8_t>(entries,2);
 bool predict(uint32_t pc)const{return counters[(pc^history)&(entries-1)]>1;}
 void update(uint32_t pc,bool taken){auto& c=counters[(pc^history)&(entries-1)];if(taken){if(c<3)++c;}else if(c)--c;history=((history<<1)|unsigned(taken))&(entries-1);}
 void corrupt(size_t id){if(id>=size_t(entries)*2+history_bits)throw std::out_of_range("logical Gshare bit");if(id<size_t(entries)*2)counters[id/2]^=1u<<(id%2);else history^=1u<<(id-size_t(entries)*2);}
};
}
