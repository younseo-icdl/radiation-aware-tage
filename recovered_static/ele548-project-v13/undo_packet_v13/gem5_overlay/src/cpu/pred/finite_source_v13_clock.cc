#include "cpu/pred/finite_source_v13_clock.hh"
namespace bp::v13 {
Gem5Clock::Gem5Clock(gem5::EventManager&owner,LookupPort&port,gem5::Tick period,
 Provider provider,const std::string&name):owner_(owner),port_(port),period_(period),provider_(std::move(provider)),
 clock_([this]{step();},name+".finite_source_v13",false,gem5::Event::CPU_Tick_Pri-2){
 if(!period_||!provider_||gem5::curTick()!=0)throw std::invalid_argument("finite source clock must be constructed at reset tick zero");
 arm();
}
Gem5Clock::~Gem5Clock(){if(clock_.scheduled())owner_.deschedule(clock_);}
void Gem5Clock::arm(){if(!clock_.scheduled())owner_.schedule(clock_,(gem5::curTick()/period_+1)*period_);}
void Gem5Clock::step(){
 port_.advance(provider_);
 // Free-running from reset: internal cycle == real owner cycle, including
 // idle II/repair/retire-port release. No uncharged fast-forward of work.
 arm();
}
std::optional<Token> Gem5Clock::request(uint64_t pc,bool conditional){auto t=port_.request(pc,conditional);arm();return t;}
std::optional<LookupPort::Output> Gem5Clock::take(Token t){return port_.take(t);}
std::optional<Token> Gem5Clock::source_command(Kind kind,unsigned n,unsigned bits,unsigned path){
 if(kind==Kind::Read)throw std::invalid_argument("use request for owned lookup");
 auto t=port_.source.accept(kind,n,bits,path);arm();return t;
}
bool Gem5Clock::retire(unsigned n){bool ready=port_.source.retire(n);if(!ready)arm();return ready;}
void Gem5Clock::cancel(){port_.cancel();arm();}
bool Gem5Clock::acknowledge_wrap(){bool ready=port_.acknowledge_wrap();arm();return ready;}
}
