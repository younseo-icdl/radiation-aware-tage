#include "work_counter.hpp"
#include <iostream>
using namespace bp;
int main(){try{
 BurstWorkCounter b;b.reserve(60,10);b.reserve(80,10);if(b.remaining!=140||b.jobs!=140)throw std::runtime_error("same cycle work lost");b.advance(25);if(b.remaining!=125||b.serviced!=15)throw std::runtime_error("finite service");b.advance(300);if(b.remaining)throw std::runtime_error("no progress while CPU idle");
 for(unsigned bit=0;bit<12;++bit){b.flip(bit);if(!b.bit(bit))throw std::runtime_error("work FI");b.flip(bit);}
 b.reserve(4095,300);try{b.reserve(1,300);throw std::runtime_error("overflow accepted");}catch(const std::overflow_error&){}if(b.remaining!=4095)throw std::runtime_error("overflow mutated descriptor");
 std::cout<<"PASS burst coalescing, finite onecycle service, idle progression,12bit FI,4095bound\n";
 }catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
