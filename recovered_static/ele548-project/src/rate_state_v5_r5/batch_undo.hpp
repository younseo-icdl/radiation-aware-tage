#pragma once
#include <optional>
#include <stdexcept>
namespace bp::v5 {
// Reduction within one non-yielding BPU squash call. This is combinational
// packet construction, not a persistent shadow or an oracle recovery image.
struct UndoPacket {unsigned count,path,operations;};
class UndoBatch {
 unsigned depth_=0,count_=0,path_=0,operations_=0;
 public:
 bool active()const{return depth_!=0;}
 void begin(){if(depth_>=2)throw std::logic_error("BPU squash nesting exceeds two known overloads");if(!depth_)count_=path_=operations_=0;++depth_;}
 bool add(unsigned n,unsigned path){if(!active())return false;if(count_+n>1000)throw std::overflow_error("BPU undo span exceeds retained journal window");count_+=n;path_=path&65535;++operations_;return true;}
 std::optional<UndoPacket> take(){if(!operations_)return {};UndoPacket out{count_,path_,operations_};count_=path_=operations_=0;return out;}
 std::optional<UndoPacket> finish(){if(!active())throw std::logic_error("BPU squash end without begin");if(--depth_)return {};return take();}
};
}
