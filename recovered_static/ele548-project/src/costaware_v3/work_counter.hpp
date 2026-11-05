#pragma once
#include <cstdint>
#include <algorithm>
#include <stdexcept>
namespace bp {
// One bounded burst descriptor replaces one token per inverse-rollback callback.
// All work is retained: service one reserved cycle per clock. The absolute clock
// tag is simulator timing metadata; the12-bit debt is real, separately exposed.
class BurstWorkCounter {
 public:
 static constexpr unsigned width=12;
 static constexpr uint16_t limit=(1u<<width)-1;
 uint16_t remaining=0;
 uint64_t last_cycle=0,jobs=0,max_debt=0,serviced=0;
 void advance(uint64_t cycle){
  if(cycle<last_cycle)throw std::invalid_argument("work counter clock reversed");
  auto elapsed=cycle-last_cycle;auto n=std::min<uint64_t>(elapsed,remaining);
  remaining-=n;serviced+=n;last_cycle=cycle;
 }
 void reserve(uint64_t work,uint64_t cycle){
  advance(cycle);if(work>limit-remaining)throw std::overflow_error("finite4095cycle work descriptor overflow");
  remaining+=work;jobs+=work;max_debt=std::max<uint64_t>(max_debt,remaining);
 }
 bool bit(unsigned bit)const{if(bit>=width)throw std::out_of_range("work bit");return (remaining>>bit)&1;}
 void flip(unsigned bit){if(bit>=width)throw std::out_of_range("work bit");remaining^=uint16_t(1)<<bit;}
};
}
