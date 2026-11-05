#pragma once
#include "overwrite.hpp"
#include <string>

namespace bp::v11 {
// Compile/elaboration configuration only: no adaptive/oracle policy. Existing
// six representations keep their original virtual hooks when disabled.
template<class Parent> class CpuSelectOverwrite : public OverwriteAccess<Parent> {
 public:
  const bool overwrite_enabled;
  CpuSelectOverwrite(const CpuSelectOverwrite&)=delete;
  CpuSelectOverwrite(CpuSelectOverwrite&&)=delete;
  CpuSelectOverwrite& operator=(const CpuSelectOverwrite&)=delete;
  CpuSelectOverwrite& operator=(CpuSelectOverwrite&&)=delete;
  template<class Params>
  CpuSelectOverwrite(const Params& p,const std::string& mode,unsigned budget):
    OverwriteAccess<Parent>(p,mode=="overwrite"?"recurrent":mode,budget),
    overwrite_enabled(mode=="overwrite") {}
  void updateGHist(gem5::ThreadID tid,uint64_t bits,uint8_t n) override {
    if(overwrite_enabled)OverwriteAccess<Parent>::updateGHist(tid,bits,n);
    else Parent::updateGHist(tid,bits,n);
  }
  void restoreHistState(gem5::ThreadID tid,bp::Base::BranchInfo* bi) override {
    if(overwrite_enabled)OverwriteAccess<Parent>::restoreHistState(tid,bi);
    else Parent::restoreHistState(tid,bi);
  }
};
} // namespace bp::v11
