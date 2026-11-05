#pragma once
#include "/home/youns/workspace/ele548-project-v13/undo_packet_v13/src/lookup_port.hpp"
#include "sim/eventq.hh"
#include <functional>
namespace bp::v13 {
// gem5 clock adapter only. This is not registered as a SimObject/BPU and does
// not modify an old predictor or binary. An O3 owner must explicitly wire
// request/take/cancel, source callback admission, retire and receiver wrap ACK.
class Gem5Clock {
 public:
 using Provider=std::function<v9::Payload(uint64_t,bool,const std::array<unsigned,21>&,unsigned)>;
 private:
 gem5::EventManager& owner_;LookupPort& port_;const gem5::Tick period_;
 Provider provider_;gem5::EventFunctionWrapper clock_;
 void step();
 public:
 Gem5Clock(gem5::EventManager&,LookupPort&,gem5::Tick,Provider,const std::string&);
 ~Gem5Clock();
 Gem5Clock(const Gem5Clock&)=delete;Gem5Clock& operator=(const Gem5Clock&)=delete;
 void arm();
 std::optional<Token> request(uint64_t,bool);
 std::optional<LookupPort::Output> take(Token);
 std::optional<Token> source_command(Kind,unsigned=0,unsigned=0,unsigned=0);
 bool retire(unsigned);
 void cancel();
 bool acknowledge_wrap();
};
}
