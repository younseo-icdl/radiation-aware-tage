#include "model.hpp"
#include <iostream>
#include <sstream>
#include "/home/youns/workspace/ele548-project-v10/cost_v10/tests/history_state_pinned_reference.hpp"

using bp::Base;using bp::Branch;using bp::RoundState;
using bp::v11::State;using bp::v11::OverwriteAdapter;using bp::v11::BaselineAdapter;
static void need(bool ok,const char* s) {if(!ok)throw std::runtime_error(s);}
static bool folds_coherent(const State& s) {
  static const auto specs=s.history_words();
  for(unsigned w=0;w<21;++w) {
    history_state_pinned::FoldedHistory reference;
    const unsigned length=s.fold_length(w);
    reference.init(length,specs[w].width);
    uint8_t scratch[131]={};
    // Independent pinned recurrent replay from zero, oldest source bit first.
    // At <=length pushes the outgoing bit remains zero.
    for(int age=int(length)-1;age>=0;--age) {
      scratch[0]=s.raw_bit(unsigned(age));reference.update(scratch);
    }
    if(s.read_history_word(w).limb[0]!=reference.comp)return false;
  }
  return true;
}
static void compare_bi(const Base::BranchInfo& a,const Base::BranchInfo& b,bool cond) {
  if(cond) {
    need(a.tagePred==b.tagePred&&a.hitBank==b.hitBank&&a.provider==b.provider,"prediction/provider differs");
    for(unsigned bank=1;bank<=7;++bank)
      need(a.tableIndices[bank]==b.tableIndices[bank]&&a.tableTags[bank]==b.tableTags[bank],"index/tag differs");
  }
}
static gem5::TAGEBaseParams spec_params() {
  gem5::TAGEBaseParams p;p.speculativeHistUpdate=true;p.histBufferSize=4096;return p;
}
int main() {try {
  uint64_t normal=0,spec_reads=0,spec_undos=0,fold_flips=0,raw_evictions=0;
  BaselineAdapter rec;OverwriteAdapter ow;std::mt19937_64 input(0x11f01d);
  for(unsigned i=0;i<150000;++i) {
    Branch b{0x4000+(input()%4096),0x8000+(input()%1024),bool(input()&1),bool(i%9)};
    std::vector<int> left,right;
    auto capture=[](const Base::BranchInfo& bi,std::vector<int>& v,bool cond) {
      v.clear();
      if(cond) {
        v={int(bi.tagePred),bi.hitBank,int(bi.provider)};
        for(unsigned bank=1;bank<=7;++bank) {v.push_back(bi.tableIndices[bank]);v.push_back(bi.tableTags[bank]);}
      }
    };
    bool a=rec.step(b,[&](const auto&bi){capture(bi,left,b.conditional);});
    bool d=ow.step(b,[&](const auto&bi){capture(bi,right,b.conditional);});
    need(a==d&&left==right,"full normal schedule mismatch");
    if(i%997==0)need(ow.core.equal(rec.core)&&ow.rng==rec.rng,"normal training/state/RNG mismatch");
    ++normal;
  }
  need(ow.core.equal(rec.core)&&ow.rng==rec.rng,"terminal normal state");
  auto saved=ow.core.save();State copy;copy.load(saved);
  need(copy.equal(ow.core),"snapshot roundtrip");
  auto all=copy.sites();copy.corrupt({all.front().id});
  need(!copy.equal(ow.core),"snapshot alias");copy.load(saved);
  auto signed_site=std::find_if(all.begin(),all.end(),[](const auto&s){return s.kind==1&&s.row==0&&s.bank==1&&s.bit==2;});
  auto before=copy.payload(*signed_site);copy.corrupt({signed_site->id});
  need(copy.payload(*signed_site)==(before^4u),"signed logical MSB flip");
  copy.load(saved);
  bool rejected=false;try {copy.corrupt({all.front().id,all.front().id});} catch(const std::invalid_argument&) {rejected=true;}
  need(rejected&&copy.equal(ow.core),"invalid atomic event changed state");

  // Every physical fold bit: lookup and n=0 HOLD must NOT repair it. Only the
  // next real history transition overwrites from the actually stored source.
  for(const auto& s:all)if(s.kind==5) {
    copy.load(saved);copy.corrupt({s.id});auto dirty=copy.read_history_word((s.bank-1)*3+s.row);
    auto* bi=copy.makeBranchInfo(0x4013,true);copy.tagePredict(0,0x4013,true,bi);
    need(copy.read_history_word((s.bank-1)*3+s.row)==dirty,"lookup silently repaired fold");
    copy.updateGHist(0,0,0);
    need(copy.read_history_word((s.bank-1)*3+s.row)==dirty,"HOLD silently repaired fold");
    copy.updateHistories(0,0x4013,false,true,0,{},bi);delete bi;
    need(folds_coherent(copy),"fold upset persists after overwrite");++fold_flips;
  }
  need(fold_flips==200,"fold manifest geometry changed");

  // All source ages: bad source is used as bad source, then leaves active
  // history under a fixed forward stream. No table/full-buffer recovery claim.
  for(unsigned age=0;age<130;++age) {
    State clean,bad;auto sites=bad.sites();
    auto p=std::find_if(sites.begin(),sites.end(),[&](auto&s){return s.kind==4&&!s.bank&&s.row==age;});
    bad.corrupt({p->id});
    for(unsigned i=0;i<130;++i) {clean.updateGHist(0,i&1,1);bad.updateGHist(0,i&1,1);need(folds_coherent(bad),"bad source is not used coherently");}
    for(unsigned w=0;w<23;++w)need(clean.read_history_word(w)==bad.read_history_word(w),"active source did not evict");
    ++raw_evictions;
  }

  // Same pinned speculative record lifecycle, including corrected oldest
  // branch, committed training and repeated finite-buffer rollovers.
  RoundState base(spec_params());State next(spec_params());std::mt19937_64 r(548);
  for(unsigned round=0;round<4000;++round) {
    std::vector<Base::BranchInfo*> a,b;
    for(unsigned i=0;i<32;++i) {
      uint64_t pc=0x1001+((round*17+i*3)%4096);bool cond=(i+round)%7;
      auto* ai=base.makeBranchInfo(pc,cond);auto* bi=next.makeBranchInfo(pc,cond);
      need(base.tagePredict(0,pc,cond,ai)==next.tagePredict(0,pc,cond,bi),"spec prediction");compare_bi(*ai,*bi,cond);
      base.updateHistories(0,pc,true,i&1,0,{},ai);next.updateHistories(0,pc,true,i&1,0,{},bi);
      a.push_back(ai);b.push_back(bi);++spec_reads;
    }
    for(int i=31;i>0;--i) {base.restoreHistState(0,a[i]);next.restoreHistState(0,b[i]);delete a[i];delete b[i];++spec_undos;}
    base.updateHistories(0,a[0]->branchPC,true,true,0,{},a[0]);next.updateHistories(0,b[0]->branchPC,true,true,0,{},b[0]);
    int nr=int(r()%std::numeric_limits<int>::max())&3;
    if(a[0]->condBranch) {base.condBranchUpdate(0,a[0]->branchPC,true,a[0],nr,0,a[0]->tagePred);next.condBranchUpdate(0,b[0]->branchPC,true,b[0],nr,0,b[0]->tagePred);}
    base.updateHistories(0,a[0]->branchPC,false,true,0,{},a[0]);next.updateHistories(0,b[0]->branchPC,false,true,0,{},b[0]);
    need(next.equal(base),"spec corrected/commit state mismatch");
    delete a[0];delete b[0];
  }
  need(next.activity.rollovers>=2,"finite-buffer rollover not exercised");

  // Nested512 outstanding records and an upset in the middle of rollback.
  RoundState ref(spec_params());State dut(spec_params());std::vector<Base::BranchInfo*> aa,bb;
  for(unsigned i=0;i<512;++i) {
    auto* a=ref.makeBranchInfo(0x1001+i,true);auto* b=dut.makeBranchInfo(0x1001+i,true);
    ref.updateHistories(0,a->branchPC,true,i&1,0,{},a);dut.updateHistories(0,b->branchPC,true,i&1,0,{},b);aa.push_back(a);bb.push_back(b);
  }
  for(int i=511;i>=0;--i) {
    if(i==257) {auto s=dut.sites();auto f=std::find_if(s.begin(),s.end(),[](auto&x){return x.kind==5;});dut.corrupt({f->id});}
    ref.restoreHistState(0,aa[i]);dut.restoreHistState(0,bb[i]);
    need(dut.equal(ref),"undo retained dirty fold or stale snapshot");delete aa[i];delete bb[i];++spec_undos;
  }

  // Source corruption can re-enter active history after rollback. Full-fold
  // overwrite does not magically restore raw retention storage.
  State source_bad(spec_params());auto ss=source_bad.sites();auto raw=std::find_if(ss.begin(),ss.end(),[](auto&s){return s.kind==4&&!s.bank&&s.row==64;});source_bad.corrupt({raw->id});
  std::vector<Base::BranchInfo*> retained;
  for(unsigned i=0;i<130;++i) {auto* bi=source_bad.makeBranchInfo(0x2001+i,true);source_bad.updateHistories(0,bi->branchPC,true,false,0,{},bi);retained.push_back(bi);}
  need(source_bad.read_history_word(21)==bp::Word{},"source did not leave active window");
  for(int i=129;i>=0;--i) {source_bad.restoreHistState(0,retained[i]);delete retained[i];}
  need(source_bad.raw_bit(64)&&folds_coherent(source_bad),"rollback incorrectly restored a golden source");

  std::cout<<"{\"status\":\"PASS_FULL_PREDICTOR_CPP_FUNCTIONAL_NOT_CPU_TIMING\",\"normal_branches\":"<<normal
    <<",\"speculative_reads\":"<<spec_reads<<",\"undo_checks\":"<<spec_undos<<",\"rollovers\":"<<next.activity.rollovers
    <<",\"fold_SBU_bits\":"<<fold_flips<<",\"raw_age_evictions\":"<<raw_evictions
    <<",\"nested_outstanding\":512,\"source_rollback_resurrection_verified\":true,\"snapshot_signed_atomic\":true"
    <<",\"normal_full_fold_calls\":"<<ow.core.activity.forward_calls<<",\"normal_source_bits_sampled\":"<<ow.core.activity.source_bits_sampled
    <<",\"normal_fold_tap_terms\":"<<ow.core.activity.fold_tap_terms<<",\"normal_fold_bit_writes\":"<<ow.core.activity.fold_bit_writes
    <<",\"spec_forward_calls\":"<<next.activity.forward_calls<<",\"spec_undo_calls\":"<<next.activity.undo_calls<<"}\n";
  return 0;
} catch(const std::exception&e) {std::cerr<<"FAIL "<<e.what()<<'\n';return 1;}}
