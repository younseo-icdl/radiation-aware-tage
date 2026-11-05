#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <utility>

namespace bp::v7 {

// Transport only: accept captures address operands, never a prediction.
// Payload supplies a fixed bits()/bit(index)/flip(index) logical-bit interface.
// Host pointers inside Payload must be excluded by that interface. Absolute
// cycle/deadline tags and observation counters are simulator helpers, excluded
// from logical storage; queue controls, phases, IDs, epochs and operands are not.
template<class Payload> class RequestPipeline {
 public:
  static constexpr unsigned request_capacity=4,response_capacity=4;
  struct Token {
    uint16_t id=0,epoch=0;
    bool operator==(const Token& other)const {
      return id==other.id && epoch==other.epoch;
    }
    bool operator!=(const Token& other)const {return !(*this==other);}
  };
  struct Context {Token token{};uint64_t pc=0;bool conditional=false;};
  enum class Phase:uint8_t {Address=0,Table=1,Response=2,Cancelled=3};
  struct Entry:Context {Payload payload{};bool valid=false;Phase phase=Phase::Address;};

  uint64_t accepted=0,produced=0,completed=0,cancelled=0;
  uint64_t maxinflight=0,max_request_outstanding=0;
  uint64_t stallfull=0,stallII=0,staleresponse=0;

  explicit RequestPipeline(unsigned latency,unsigned initiation_interval=1)
      :latency_(latency),ii_(initiation_interval),payload_bits_(Payload{}.bits()) {
    if((latency!=1 && latency!=2)||!ii_)
      throw std::invalid_argument("pipeline requires L1/L2 and positive II");
  }

  unsigned latency()const{return latency_;}
  unsigned initiation_interval()const{return ii_;}
  unsigned request_occupancy()const {validate_controls();return request_count_;}
  unsigned response_occupancy()const {validate_controls();return response_count_;}
  uint64_t pending()const {
    validate_controls();
    uint64_t count=response_count_;
    for(unsigned n=0;n<request_count_;++n)
      if(requests_[(request_head_+n)%request_capacity].entry.phase!=Phase::Cancelled)
        ++count;
    return count;
  }
  uint16_t epoch()const{return epoch_;}

  std::optional<Token> accept(uint64_t cycle,uint64_t pc,bool conditional,
                              Payload payload) {
    validate_controls();
    if(payload.bits()!=payload_bits_)
      throw std::invalid_argument("pipeline payload logical width changed");
    if(request_count_==request_capacity){++stallfull;return std::nullopt;}
    if(have_issue_ && (cycle<last_issue_ || cycle-last_issue_<ii_)){
      ++stallII;return std::nullopt;
    }
    const Token token{next_id_,epoch_};
    for(const auto& slot:requests_)
      if(slot.entry.valid && slot.entry.phase!=Phase::Cancelled &&
         slot.entry.token==token) fail("request ID reused while outstanding");
    for(const auto& entry:responses_)
      if(entry.valid && entry.token==token) fail("response ID reused while outstanding");
    auto& slot=requests_[request_tail_];
    slot=Slot{};
    slot.entry.token=token;slot.entry.pc=pc;slot.entry.conditional=conditional;
    slot.entry.payload=std::move(payload);slot.entry.valid=true;
    slot.issued=cycle;
    if(cycle>std::numeric_limits<uint64_t>::max()-latency_)
      fail("pipeline deadline overflow");
    slot.due=cycle+latency_;
    request_tail_=(request_tail_+1)%request_capacity;++request_count_;
    next_id_=uint16_t(next_id_+1);last_issue_=cycle;have_issue_=true;
    ++accepted;
    if(pending()>maxinflight)maxinflight=pending();
    if(request_count_>max_request_outstanding)max_request_outstanding=request_count_;
    return token;
  }

  // A blocked response queue retains the complete request and does not invoke
  // provider. One provider read port serves at most one request per cycle.
  // Repeated advance(cycle) calls cannot create extra same-cycle bandwidth.
  template<class Provider> void advance(uint64_t cycle,Provider&& provider) {
    validate_controls();
    for(unsigned n=0;n<request_count_;++n){
      auto& slot=requests_[(request_head_+n)%request_capacity];
      if(!slot.entry.valid)fail("invalid occupied request slot");
      if(slot.entry.phase==Phase::Response)fail("response phase in request queue");
      if(latency_==2 && cycle>slot.issued && slot.entry.phase==Phase::Address)
        slot.entry.phase=Phase::Table;
    }
    while(request_count_){
      auto& slot=requests_[request_head_];
      if(cycle<slot.due)return;
      if(slot.entry.phase==Phase::Cancelled || slot.entry.token.epoch!=epoch_){
        account_cancel(slot);++staleresponse;pop_request();continue;
      }
      if(response_count_==response_capacity){++stallfull;return;}
      if(have_provider_ && cycle<=last_provider_)return;
      Context context{slot.entry.token,slot.entry.pc,slot.entry.conditional};
      provider(slot.entry.payload,context);
      Entry result=std::move(slot.entry);result.phase=Phase::Response;
      auto& response=responses_[response_tail_];
      if(response.valid)fail("response tail overwrites live entry");
      response=std::move(result);
      response_tail_=(response_tail_+1)%response_capacity;++response_count_;
      ++produced;last_provider_=cycle;have_provider_=true;pop_request();
      return;
    }
  }

  const Entry* peek()const {
    validate_controls();
    if(!response_count_)return nullptr;
    const auto& response=responses_[response_head_];
    if(!response.valid || response.phase!=Phase::Response)
      fail("invalid occupied response slot");
    return &response;
  }
  std::optional<Entry> consume(Token expected) {
    const auto* front=peek();
    if(!front || front->token!=expected)return std::nullopt;
    if(front->token.epoch!=epoch_){
      ++cancelled;++staleresponse;pop_response();return std::nullopt;
    }
    Entry value=*front;pop_response();++completed;return value;
  }

  // Cancellation never calls provider and never restores a golden predictor.
  // Requests retain physical occupancy until their old due stage discards them.
  void cancel() {
    validate_controls();
    if(epoch_==std::numeric_limits<uint16_t>::max() &&
       (request_count_||response_count_))fail("epoch wrap requires drained pipeline");
    epoch_=uint16_t(epoch_+1);
    for(unsigned n=0;n<request_count_;++n){
      auto& slot=requests_[(request_head_+n)%request_capacity];
      if(!slot.entry.valid)fail("invalid occupied request during cancellation");
      account_cancel(slot);slot.entry.phase=Phase::Cancelled;
    }
    while(response_count_){++cancelled;++staleresponse;pop_response();}
  }

  // Fixed populations include inactive slots; faults are never host pointer or
  // C++ padding flips. Widths: controls46 + eight*(metadata100 + payload bits).
  size_t bits()const{return 46+8*(100+payload_bits_);}
  bool bit(size_t index)const {
    if(index>=bits())throw std::out_of_range("pipeline logical bit");
    if(index<46)return control_bit(index);
    index-=46;const size_t stride=100+payload_bits_;
    const auto& entry=index/stride<4?requests_[index/stride].entry:
                                        responses_[index/stride-4];
    return entry_bit(entry,index%stride);
  }
  void flip(size_t index) {
    if(index>=bits())throw std::out_of_range("pipeline logical bit");
    if(index<46){flip_control(index);return;}
    index-=46;const size_t stride=100+payload_bits_;
    auto& entry=index/stride<4?requests_[index/stride].entry:
                                  responses_[index/stride-4];
    flip_entry(entry,index%stride);
  }

 private:
  struct Slot {
    Entry entry{};
    uint64_t issued=0,due=0; // excluded scheduler tags, not hidden operands
    bool cancellation_accounted=false; // statistics only, no provider decision
  };
  const unsigned latency_,ii_;
  const size_t payload_bits_;
  std::array<Slot,4> requests_{};
  std::array<Entry,4> responses_{};
  uint16_t next_id_=0,epoch_=0;
  unsigned request_head_=0,request_tail_=0,request_count_=0;
  unsigned response_head_=0,response_tail_=0,response_count_=0;
  uint64_t last_issue_=0,last_provider_=0;
  bool have_issue_=false,have_provider_=false;

  [[noreturn]] static void fail(const char* message){throw std::runtime_error(message);}
  void validate_controls()const {
    if(request_head_>=4||request_tail_>=4||request_count_>4||
       response_head_>=4||response_tail_>=4||response_count_>4)
      fail("invalid pipeline queue control");
    if((request_head_+request_count_)%4!=request_tail_ ||
       (response_head_+response_count_)%4!=response_tail_)
      fail("inconsistent pipeline queue control");
  }
  void account_cancel(Slot& slot){
    if(!slot.cancellation_accounted){++cancelled;slot.cancellation_accounted=true;}
  }
  void pop_request(){
    requests_[request_head_]=Slot{};
    request_head_=(request_head_+1)%4;--request_count_;
  }
  void pop_response(){
    responses_[response_head_]=Entry{};
    response_head_=(response_head_+1)%4;--response_count_;
  }
  bool control_bit(size_t n)const {
    if(n<16)return (epoch_>>n)&1;
    if(n<32)return (next_id_>>(n-16))&1;
    n-=32;
    if(n<2)return (request_head_>>n)&1;
    n-=2;
    if(n<2)return (request_tail_>>n)&1;
    n-=2;
    if(n<3)return (request_count_>>n)&1;
    n-=3;
    if(n<2)return (response_head_>>n)&1;
    n-=2;
    if(n<2)return (response_tail_>>n)&1;
    n-=2;
    return (response_count_>>n)&1;
  }
  void flip_control(size_t n) {
    if(n<16){epoch_^=uint16_t(1u<<n);return;}
    if(n<32){next_id_^=uint16_t(1u<<(n-16));return;}
    n-=32;
    if(n<2){request_head_^=1u<<n;return;}n-=2;
    if(n<2){request_tail_^=1u<<n;return;}n-=2;
    if(n<3){request_count_^=1u<<n;return;}n-=3;
    if(n<2){response_head_^=1u<<n;return;}n-=2;
    if(n<2){response_tail_^=1u<<n;return;}n-=2;
    response_count_^=1u<<n;
  }
  static bool field_bit(uint64_t value,size_t bit){return (value>>bit)&1;}
  bool entry_bit(const Entry& e,size_t n)const {
    if(n==0)return e.valid;
    if(n<3)return field_bit(unsigned(e.phase),n-1);
    if(n<19)return field_bit(e.token.id,n-3);
    if(n<35)return field_bit(e.token.epoch,n-19);
    if(n<99)return field_bit(e.pc,n-35);
    if(n==99)return e.conditional;
    return e.payload.bit(n-100);
  }
  void flip_entry(Entry& e,size_t n) {
    if(n==0){e.valid=!e.valid;return;}
    if(n<3){e.phase=Phase(unsigned(e.phase)^(1u<<(n-1)));return;}
    if(n<19){e.token.id^=uint16_t(1u<<(n-3));return;}
    if(n<35){e.token.epoch^=uint16_t(1u<<(n-19));return;}
    if(n<99){e.pc^=uint64_t(1)<<(n-35);return;}
    if(n==99){e.conditional=!e.conditional;return;}
    e.payload.flip(n-100);
  }
};

} // namespace bp::v7
