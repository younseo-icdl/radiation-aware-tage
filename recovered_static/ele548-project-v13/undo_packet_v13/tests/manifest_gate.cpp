#include "lookup_port.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
#include <fstream>
using namespace bp::v13;
int main(int argc,char**argv){try{
 if(argc!=2)throw std::runtime_error("manifest output required");bp::RoundState ref;auto words=ref.history_words();std::vector<Geometry> g;for(unsigned w=0;w<21;++w)g.push_back({ref.fold_length(w),words[w].width});
 std::ofstream out(argv[1]);out<<"{\"scope\":\"FINITE_SOURCE_AND_PROVIDER_BOUNDARY_NOT_FULL_CPU\",\"models\":[";bool first=true;unsigned tested=0;
 for(auto mode:{Mode::Recurrent,Mode::Direct,Mode::Overwrite})for(unsigned L:{1u,2u}){
  LookupPort port(mode,g,L,L);if(!first)out<<',';first=false;out<<"{\"mode\":"<<unsigned(mode)<<",\"source_update_L\":"<<(mode==Mode::Direct?1:L)<<",\"source_query_L\":"<<L<<",\"provider_extra_L\":1,\"source_bits\":"<<port.source.bits()<<",\"total_bits\":"<<port.bits()<<",\"regions\":[";
  bool region=true;for(auto&r:port.manifest()){if(!region)out<<',';region=false;out<<"{\"name\":\""<<r.name<<"\",\"start\":"<<r.start<<",\"bits\":"<<r.bits<<'}';}out<<"]}";
  for(size_t bit=0;bit<port.bits();++bit){bool before=port.logical_bit(bit);port.corrupt({bit});if(port.logical_bit(bit)==before)throw std::runtime_error("unmapped bit");port.corrupt({bit});if(port.logical_bit(bit)!=before)throw std::runtime_error("bit XOR irreversible");++tested;}
  auto copy=port;copy.corrupt({0});if(copy.logical_bit(0)==port.logical_bit(0))throw std::runtime_error("snapshot source alias");
 }
 out<<"],\"excluded\":[\"C++ padding, pointers and combinational temporaries\",\"configuration geometry, mode and L/II\",\"absolute software timing helpers and counters\",\"original tagged/bimodal tables, allocator and CPU-owned consumed BranchInfo/BTB/RAS/PC stream storage outside this component scope\",\"provider test helper fold/path arrays are combinational operands, no authoritative second source or recovery image\"],\"assumptions\":[\"raw register/tap interface with simultaneous pre/post window taps, not one-port SRAM\",\"parallel actual SECDED encode/decode stage fit unmeasured\",\"source L1/2 and additional hash/table/provider 1cycle are modeled timing, not achieved technology clock\",\"clock adapter absolute reset at gem5 tick0, free-running real events; not an instantiated BPU\"]}\n";out.close();if(!out)throw std::runtime_error("manifest write");
 std::cout<<"{\"status\":\"PASS_ACTUAL_SOURCE_PROVIDER_BITS_NOT_FULL_PREDICTOR_MANIFEST\",\"model_geometries\":6,\"reversible_physical_bit_tests\":"<<tested<<"}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
