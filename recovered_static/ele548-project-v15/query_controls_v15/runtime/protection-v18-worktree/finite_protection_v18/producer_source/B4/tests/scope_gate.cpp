#include "controller.hpp"
#include "/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/state.hpp"
#include <iostream>
#include <random>
using namespace bp::v18b4;
static void need(bool x,const char*s){if(!x)throw std::runtime_error(s);}
static bp::v9::Payload dummy(uint64_t,bool,const std::array<unsigned,21>&,unsigned){return {};}
static void drain(Controller&c){for(unsigned i=0;i<300;++i){if(c.drained())return;c.advance(dummy);}throw std::runtime_error("scope drain");}
int main(){try{
 bp::RoundState native;auto words=native.history_words();std::vector<Geometry> g;for(unsigned w=0;w<21;++w)g.push_back({native.fold_length(w),words[w].width});
 Controller c(Mode::Recurrent,g);std::mt19937_64 rng(548);unsigned checks=0,deep=0,corrupts=0,writes=0;
 for(unsigned round=0;round<50;++round){
  unsigned span=round%4==0?1000:1+rng()%70;
  for(unsigned j=0;j<span;++j){c.append(1,rng()&1,rng()&1);drain(c);}
  auto before=c.port.source.selected_words();auto widths=c.port.source.selected_widths();unsigned sum=0;std::set<size_t> physical;
  auto snap=c.port.source.observe_source();
  for(unsigned w=0;w<23;++w){sum+=widths[w];for(unsigned bit=0;bit<widths[w];++bit){auto site=c.port.source.selected_site(w,bit);need(physical.insert(site).second,"non-bijective S* mapping");need(c.logical_bit(site)==before[w].bit(bit),"word/site mapping disagreement");++checks;}}
  need(sum==346&&physical.size()==346,"S* scope width");
  for(unsigned age=0;age<130;++age)need(before[21].bit(age)==snap.raw[age],"raw age/ring mapping");need(before[22].limb[0]==snap.path,"path mapping");
  if(round%10==0)for(unsigned w=0;w<23;++w)for(unsigned bit=0;bit<widths[w];++bit){Controller copy=c;auto site=copy.port.source.selected_site(w,bit);copy.corrupt({site});auto after=copy.port.source.selected_words();auto expect=before;expect[w].flip(bit);need(after==expect,"precise selected flip");need(c.port.source.selected_words()==before,"snapshot is not deep copy");copy.port.source.write_selected_word(w,before[w]);need(copy.port.source.selected_words()==before,"repair did not write actual source");++corrupts;++writes;}
  need(c.prepare_recovery(),"scope recovery admission");c.begin();c.restore(span,0);c.end();drain(c);need(c.port.source.source_depth()==0&&c.conserved(),"deep rollback ownership");if(span==1000)++deep;
 }
 Controller d(Mode::Direct,g);bool missing=false;try{d.port.source.selected_site(0,0);}catch(const std::invalid_argument&){missing=true;}need(missing,"phantom Direct fold site");
 // A retained cell outside S* remains a real, exposed logical bit. It can
 // reenter after undo; the mapping API does not repair or encode that bit.
 Controller retention(Mode::Recurrent,g);retention.append(1,1,0);drain(retention);auto active=retention.port.source.selected_site(21,129);auto outside=(active+1)%1130;retention.corrupt({outside});need(retention.port.source.logical_bit(outside),"retention fault not exposed");need(retention.prepare_recovery(),"retention rollback");retention.begin();retention.restore(1,0);retention.end();drain(retention);need(retention.port.source.selected_words()[21].bit(129),"unprotected retention fault incorrectly erased");
 std::cout<<"{\"status\":\"PASS_SSTAR346_MAPPING_NOT_PROTECTION\",\"mapping_bit_checks\":"<<checks<<",\"precise_SBU_and_deep_copy\":"<<corrupts<<",\"actual_source_word_writes\":"<<writes<<",\"deep1000_rollback_cases\":"<<deep<<",\"unprotected_retention_reentry_observed\":true,\"Direct_phantom_fold_rejected\":true,\"CPU_trials\":0}\n";
}catch(const std::exception&e){std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
