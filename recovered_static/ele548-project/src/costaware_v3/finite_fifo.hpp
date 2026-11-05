#pragma once
#include "../protection/word.hpp"
#include <optional>
#include <algorithm>
#include <vector>
#include <stdexcept>
namespace bp {
struct QueueIntegrityError:std::runtime_error{using std::runtime_error::runtime_error;};
// One dependent RMW in flight per queue. State is sampled/published by the
// consumer only when the service counter reaches zero, never at enqueue.
class FiniteRmwQueue {
 struct Cell {Word data{};uint16_t check=0;};
 std::vector<Cell> cells;Cell control;
 WordSecded payload_code,control_code{42};
 uint64_t corrected_=0,due_=0;
 static unsigned get(const Word&w,unsigned off,unsigned n){unsigned v=0;for(unsigned i=0;i<n;++i)v|=unsigned(w.bit(off+i))<<i;return v;}
 static void put(Word&w,unsigned off,unsigned n,unsigned v){for(unsigned i=0;i<n;++i)w.set(off+i,(v>>i)&1);}
 Word decode(Cell&c,const WordSecded&codec){auto r=codec.decode(c.data,c.check);if(r.due){++due_;throw QueueIntegrityError("queue SECDED DUE");}if(r.corrected){++corrected_;c.data=r.payload;c.check=r.check;}return c.data;}
 void store(Cell&c,Word w,const WordSecded&codec){c.data=w;c.check=codec.encode(w);}
 Word header(){auto w=decode(control,control_code);if(get(w,0,8)>=depth||get(w,8,8)>=depth||get(w,16,9)>depth||(!get(w,16,9)&&get(w,25,1)))throw QueueIntegrityError("illegal queue control encoding");return w;}
 public:
 struct Snapshot{std::vector<Cell>cells;Cell control;uint64_t accepted,completed,cancelled,max_count,service_cycles,corrected,due;};
 Snapshot save()const{return {cells,control,accepted,completed,cancelled,max_count,service_cycles,corrected_,due_};}
 void restore(const Snapshot&s){if(s.cells.size()!=depth)throw std::invalid_argument("queue snapshot geometry");cells=s.cells;control=s.control;accepted=s.accepted;completed=s.completed;cancelled=s.cancelled;max_count=s.max_count;service_cycles=s.service_cycles;corrected_=s.corrected;due_=s.due;}
 const unsigned width,depth,latency,ii;
 uint64_t accepted=0,completed=0,cancelled=0,max_count=0,service_cycles=0;
 FiniteRmwQueue(unsigned bits,unsigned slots,unsigned L,unsigned II):cells(slots),payload_code(bits),width(bits),depth(slots),latency(L),ii(II){if(!slots||slots>256||!L||L>64||!II||II>64)throw std::invalid_argument("finite queue bounds");for(auto&c:cells)c.check=payload_code.encode(c.data);control.check=control_code.encode(control.data);}
 unsigned count(){return get(header(),16,9);}bool busy(){return get(header(),25,1);}
 bool can_accept(unsigned reserved=0){return count()+reserved<depth;}
 bool can_start(){auto w=header();return get(w,16,9)&&!get(w,25,1)&&!get(w,34,8);}
 void push(const Word&w){auto h=header();unsigned n=get(h,16,9),tail=get(h,8,8);if(n==depth)throw std::overflow_error("queue overflow; producer must backpressure");store(cells[tail],w,payload_code);put(h,8,8,(tail+1)%depth);put(h,16,9,n+1);store(control,h,control_code);++accepted;max_count=std::max(max_count,uint64_t(n+1));}
 Word peek(){auto h=header();if(!get(h,16,9))throw QueueIntegrityError("peek empty");return decode(cells[get(h,0,8)],payload_code);}
 bool start(unsigned factor=1){auto h=header();if(!can_start())return false;put(h,25,1,1);if(factor<1||factor>2)throw QueueIntegrityError("service factor");put(h,26,8,latency*factor);put(h,34,8,ii);store(control,h,control_code);return true;}
 std::optional<Word> tick(){auto h=header();auto gap=get(h,34,8);if(gap)put(h,34,8,gap-1);std::optional<Word> result;
  if(get(h,25,1)){auto remaining=get(h,26,8);if(!remaining)throw QueueIntegrityError("busy queue without service remaining");--remaining;put(h,26,8,remaining);++service_cycles;
   if(!remaining){unsigned head=get(h,0,8);result=decode(cells[head],payload_code);put(h,0,8,(head+1)%depth);put(h,16,9,get(h,16,9)-1);put(h,25,1,0);++completed;}}
  store(control,h,control_code);return result;
 }
 bool clock_needed(){auto h=header();return get(h,16,9)||get(h,34,8);}
 void clear(){cancelled=accepted-completed;control={};control.check=control_code.encode(control.data);}
 bool conserved(){return accepted==completed+cancelled+count();}
 uint64_t corrected()const{return corrected_;}uint64_t due()const{return due_;}
 unsigned payload_check_bits()const{return payload_code.r+1;}
 size_t bits()const{return 42+control_code.r+1+depth*(width+payload_code.r+1);}
 bool bit(size_t id)const{if(id>=bits())throw std::out_of_range("queue logical bit");unsigned control_width=42+control_code.r+1;if(id<control_width)return id<42?control.data.bit(id):((control.check>>(id-42))&1);id-=control_width;auto&c=cells[id/(width+payload_code.r+1)];unsigned b=id%(width+payload_code.r+1);return b<width?c.data.bit(b):((c.check>>(b-width))&1);}
 void flip(size_t id){if(id>=bits())throw std::out_of_range("queue logical bit");unsigned control_width=42+control_code.r+1;if(id<control_width){if(id<42)control.data.flip(id);else control.check^=uint16_t(1)<<(id-42);return;}id-=control_width;auto&c=cells[id/(width+payload_code.r+1)];unsigned b=id%(width+payload_code.r+1);if(b<width)c.data.flip(b);else c.check^=uint16_t(1)<<(b-width);}
};
}
