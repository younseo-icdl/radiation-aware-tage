#include "controller.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
using namespace bp::v15;
static void need(bool b,const char*s){if(!b)throw std::runtime_error(s);}
static bp::v9::Payload provider(uint64_t,bool,const std::array<unsigned,21>&,unsigned){return {};}
static void drain(Controller&c){for(unsigned n=0;n<100;++n){if(c.drained())return;c.advance(provider);}throw std::runtime_error("recovery drain");}
int main(){try{
 bp::RoundState ref;auto words=ref.history_words();std::vector<Geometry> g;for(unsigned w=0;w<21;++w)g.push_back({ref.fold_length(w),words[w].width});
 Controller seed(Mode::Recurrent,g,2,2);for(unsigned i=0;i<20;++i){while(!seed.normal_ready())seed.advance(provider);seed.append(1,i&1,0);}drain(seed);
 need(seed.prepare_recovery(),"frame prepare");seed.begin();seed.restore(16,0);seed.append(1,1,1);seed.end();
 need(!seed.can_retire(1),"retire before queued recovery executed");seed.advance(provider);seed.advance(provider);need(!seed.can_retire(1),"retire before actual recovery ACK");
 unsigned checked=0,late_acks=0,negative=0;
 for(auto&r:seed.manifest())if(r.name.find("metadata")!=std::string::npos||r.name.find("mirrored_SECDED")!=std::string::npos){
  for(size_t bit=r.start;bit<r.start+r.bits;++bit){Controller c=seed;bool before=c.logical_bit(bit);c.corrupt({bit});need(c.logical_bit(bit)!=before,"physical metadata bit absent");need(!c.can_retire(1),"SBU bypassed real recovery fence");
   drain(c);need(c.can_retire(1)&&c.port.source.source_depth()==5&&c.port.source.source_bit(0)&&c.port.acks==22&&c.conserved(),"recovery ACK corrupted/dropped operand");
   need(c.metadata_repairs+c.port.metadata_repairs+c.port.source.stats.metadata_repairs==1,"metadata correction not from actual word");++checked;
  }
 }
 // A second SEU during the first repair must delay service and retain its tag.
 {Controller c=seed;std::vector<size_t> fields;for(auto&r:c.manifest())if(r.name.find("command_metadata_")==0)fields.push_back(r.start);need(fields.size()==4,"source metadata fields");
  c.corrupt({fields[0]});c.advance(provider);c.corrupt({fields[1]});c.advance(provider);need(!c.can_retire(1),"mid-repair SEU ignored recovery fence");drain(c);need(c.port.source.stats.metadata_repairs==2&&c.can_retire(1)&&c.conserved(),"mid-repair tag/operand loss");++late_acks;}
 {Controller c=seed;for(auto&r:c.manifest())if(r.name=="update_metadata_0"){
   c.corrupt({r.start,r.start+1,r.start+r.bits/2,r.start+r.bits/2+1});bool failed=false;try{c.advance(provider);}catch(const IntegrityError&){failed=true;}need(failed,"both actual source copies DUE passed");++negative;break;}}
 std::cout<<"{\"status\":\"PASS_ACTUAL_RECOVERY_ACK_FENCE_AND_ALL_METADATA_SBU_NOT_CPU\",\"metadata_physical_SBU\":"<<checked<<",\"mid_repair_SEU\":"<<late_acks<<",\"expected_source_DUE\":"<<negative<<",\"premature_retire_rejected\":true,\"CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
