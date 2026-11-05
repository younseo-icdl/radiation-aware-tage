#include "costaware_v3_roundb/role_spec_history.hpp"
#include "costaware_v3_roundb/state.hpp"
#include <iostream>
using namespace bp;
int main(){try{
 gem5::TAGEBaseParams params;params.speculativeHistUpdate=true;
 RoundState core(params);RoundHistory p(core,Scheme::ED,true,RoundPolicy::STAGED,64);RoundProtocol protocol(core,p);
 auto record=protocol.capture();auto*bi=core.makeBranchInfo(0x4001,true);core.tagePredict(0,0x4001,true,bi);
 std::vector<size_t> ids;for(const auto&s:p.additional_sites())if(s.structure=="staged_control"&&(s.bit==0||s.bit==1))ids.push_back(s.id);
 if(ids.size()!=2)throw std::runtime_error("stage physical codeword fixture");p.corrupt(ids);
 bool classified_before=protocol.bypass(record);auto before=protocol.committed_refill_writes;
 protocol.commit(0,0x4001,true,0,{},bi,record,1);delete bi;
 if(classified_before||protocol.committed_refill_writes!=before+1||p.stats.due!=1)throw std::runtime_error("counterexample not reproduced");
 std::cout<<"EXPECTED_RESOURCE_COUNTEREXAMPLE unvalidated normal commit classification changed inside metadata check; actual history refill written\n";
 // Corrected preflight is exercised by the real C O3 gate; this observation
 // demonstrates the B resource boundary, not a new deployable predictor.
 return 0;
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
