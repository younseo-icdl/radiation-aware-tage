#pragma once
#include "lookup_port.hpp"
namespace bp::v16 {
// Actual four-register source ingress. A non-yielding BPU squash transaction
// reserves TWO slots before callbacks: at most one opaque undo + correction
// append. The CPU retains the ORIGINAL input time-buffer while admission is
// false; it does not drop, reconstruct or oracle-replay a source operation.
class Controller {
 struct State {unsigned head=0,tail=0,count=0,reserved=0,level=0,pending_append=0,undo=0,path=0,recovery=0;bool prepared=false,cancelled_cycle=false,has=false;};
 struct Command {bool valid=false;Kind kind=Kind::Hold;unsigned n=0,bits=0,arg=0;bool recovery=false;};
 Cell state_{48};std::array<Cell,4> commands_{{Cell{33},Cell{33},Cell{33},Cell{33}}};
 uint64_t hold_until_=0;
 void hold(){++metadata_repairs;hold_until_=std::max(hold_until_,port.source.cycle()+1);}
 static Word pack(State s){Word w;put(w,0,2,s.head);put(w,2,2,s.tail);put(w,4,3,s.count);put(w,7,2,s.reserved);put(w,9,2,s.level);w.set(11,s.prepared);w.set(12,s.cancelled_cycle);put(w,13,4,s.pending_append);put(w,17,10,s.undo);put(w,27,16,s.path);w.set(43,s.has);put(w,44,4,s.recovery);return w;}
 State load(){bool fixed=false;auto w=state_.load(fixed);if(fixed)hold();return {get(w,0,2),get(w,2,2),get(w,4,3),get(w,7,2),get(w,9,2),get(w,13,4),get(w,17,10),get(w,27,16),get(w,44,4),w.bit(11),w.bit(12),w.bit(43)};}
 void store(State s){state_.store(pack(s));}
 static Word pack(Command c){Word w;w.set(0,c.valid);put(w,1,3,unsigned(c.kind));put(w,4,10,c.n);put(w,14,2,c.bits);put(w,16,16,c.arg);w.set(32,c.recovery);return w;}
 Command command(unsigned i){bool fixed=false;auto w=commands_[i].load(fixed);if(fixed)hold();return {w.bit(0),Kind(get(w,1,3)),get(w,4,10),get(w,14,2),get(w,16,16),w.bit(32)};}
 bool poll(){try{
  auto s=load();if(s.count>4||s.count+s.reserved>4||s.reserved>2||s.level>2||s.undo>1000||s.pending_append>8||s.recovery>14||(s.head+s.count)%4!=s.tail)throw IntegrityError("ingress control encoding");
  unsigned pending=0;for(unsigned i=0;i<4;++i){auto c=command(i);bool live=false;for(unsigned n=0;n<s.count;++n)live|=i==(s.head+n)%4;if(c.valid!=live)throw IntegrityError("ingress FIFO validity relation");
   if(live){if((c.kind!=Kind::Append&&c.kind!=Kind::Undo)||c.n>1000||c.kind==Kind::Append&&(!c.n||c.n>2))throw IntegrityError("ingress command encoding");if(c.kind==Kind::Append)pending+=c.n;}}
  if(pending!=s.pending_append)throw IntegrityError("ingress credit conservation");return port.source.cycle()>=hold_until_;
 }catch(const v9::MirrorUncorrectable&e){++integrity_failures;throw IntegrityError(e.what());}}
 void push(State&s,Command c,bool reserved){
  if(s.count==4||reserved&&!s.reserved||!reserved&&s.count+s.reserved==4)throw IntegrityError("source callback without ingress credit");
  if(reserved){--s.reserved;++s.recovery;c.recovery=true;}commands_[s.tail].store(pack(c));s.tail=(s.tail+1)%4;++s.count;if(c.kind==Kind::Append)s.pending_append+=c.n;++enqueued;max_count=std::max(max_count,uint64_t(s.count));
 }
 void flush(State&s){if(s.has){push(s,{true,Kind::Undo,s.undo,0,s.path},true);s.has=false;s.undo=0;}}
 public:
 LookupPort port;
 uint64_t enqueued=0,issued=0,max_count=0,metadata_repairs=0,integrity_failures=0,recovery_waits=0,source_issue_waits=0,read_ingress_waits=0,normal_capacity_waits=0;
 Controller(Mode mode,std::vector<Geometry> geometry,unsigned UL=1,unsigned QL=1,unsigned id=16,unsigned epoch=16):port(mode,geometry,UL,QL,id,epoch){store({});for(auto&c:commands_)c.store(pack(Command{}));}
 bool normal_ready(unsigned n=1){
  if(!poll())return false;auto s=load();if(s.level||s.prepared||s.reserved||s.count==4){++normal_capacity_waits;return false;}
  return port.source.can_append(s.pending_append+n);
 }
 bool prepare_recovery(){
  if(!poll()){++recovery_waits;return false;}auto s=load();if(s.level)throw IntegrityError("CPU attempted admission inside squash");
  if(!s.prepared){port.cancel();s.prepared=true;s.cancelled_cycle=true;store(s);}
  if(s.reserved==2)return true;
  if(s.count+2>4){++recovery_waits;return false;}
  s.reserved=2;store(s);return true;
 }
 void begin(){if(!poll())throw IntegrityError("squash admitted during correction hold");auto s=load();if(!s.level&&(!s.prepared||s.reserved!=2)||s.level==2)throw IntegrityError("squash without reserved transaction");++s.level;s.cancelled_cycle=true;store(s);}
 void restore(unsigned n,unsigned path){
  if(n>1000||path>65535)throw std::invalid_argument("undo fields");if(!poll())throw IntegrityError("restore without ready reservation");auto s=load();
  if(!s.level)throw IntegrityError("unbounded restore callback outside admitted BPU transaction");
  if(s.undo+n>1000)throw IntegrityError("opaque undo retention span");s.undo+=n;s.path=path;s.has=true;store(s);
 }
 void append(unsigned n,unsigned bits,unsigned pcbit){
  if(!n||n>2||bits>3||pcbit>1)throw std::invalid_argument("append fields");if(!poll())throw IntegrityError("append during ingress correction hold");auto s=load();
  if(s.level){flush(s);push(s,{true,Kind::Append,n,bits,pcbit},true);}
  else {if(!normal_ready(n))throw IntegrityError("prediction consumed without source credit");s=load();push(s,{true,Kind::Append,n,bits,pcbit},false);}store(s);
 }
 void end(){if(!poll())throw IntegrityError("squash completion during metadata hold");auto s=load();if(!s.level)throw IntegrityError("squash end without begin");if(!--s.level){flush(s);s.reserved=0;s.prepared=false;}store(s);}
 void cancel(){(void)poll();auto s=load();if(!s.cancelled_cycle){port.cancel();s.cancelled_cycle=true;store(s);}}
 std::optional<Token> request(uint64_t pc,bool conditional){
  if(!poll())return {};auto s=load();if(s.count||s.level||s.prepared){++read_ingress_waits;return {};}
  if(!normal_ready())return {};return port.request(pc,conditional);
 }
 std::optional<LookupPort::Output> head(){if(!normal_ready())return {};return port.head();}
 std::optional<LookupPort::Output> peek(Token t){auto h=head();if(!h||h->token!=t)return {};return h;}
 std::optional<LookupPort::Output> take(Token t){if(!normal_ready())return {};return port.take(t);}
 // A checkpoint already owns its prediction/append credit. Completing it must
 // remain possible even when all1000 source credits await retirement.
 std::optional<LookupPort::Output> checkpoint_head(){if(!poll())return {};return port.head();}
 std::optional<LookupPort::Output> take_checkpoint(Token t){if(!poll())return {};return port.take(t);}
 bool discard_checkpoint(Token t){return poll()&&port.discard_ready(t);}
 template<class Provider>void advance(Provider provider){
  port.advance(provider,[this](const Reply&r){if(r.recovery){auto state=load();if(!state.recovery)throw IntegrityError("recovery ACK without ownership");--state.recovery;store(state);}});if(!poll())return;auto s=load();s.cancelled_cycle=false;
  // Auto ACK only when both the finite receiver and ACTUAL Service are empty.
  // Ingress commands not yet assigned IDs survive the barrier and issue later.
  if(port.source.wrap_waiting()&&port.receiver_drained())port.acknowledge_wrap();
  if(s.count){auto c=command(s.head);auto t=port.source.accept(c.kind,c.n,c.bits,c.arg,c.recovery);if(t){commands_[s.head].store(pack(Command{}));s.head=(s.head+1)%4;--s.count;if(c.kind==Kind::Append)s.pending_append-=c.n;++issued;}else ++source_issue_waits;}
  store(s);
 }
 bool can_retire(unsigned n){return poll()&&!load().recovery&&!load().prepared&&!load().level&&(!n||port.source.can_retire(n));}
 bool retire(unsigned n){return can_retire(n)&&(!n||port.source.retire(n));}
 bool drained(){return poll()&&!load().count&&!load().level&&!load().recovery&&port.receiver_drained()&&port.source.drained();}
 unsigned queued(){if(!poll())return 4;return load().count;}
 bool conserved(){return poll()&&enqueued==issued+load().count&&port.conserved();}
 std::vector<Service::Region> manifest()const{auto r=port.manifest();size_t at=port.bits();r.push_back({"ingress_control_mirrored_SECDED",at,state_.bits()});at+=state_.bits();for(unsigned i=0;i<4;++i){r.push_back({"ingress_payload_mirrored_SECDED_"+std::to_string(i),at,commands_[i].bits()});at+=commands_[i].bits();}return r;}
 // OBSERVATION_BEGIN
 bool diagnostic_recovery_waiting()const{auto w=state_.a.data;return get(w,44,4)||get(w,9,2)||w.bit(11);}
 // OBSERVATION_END
 size_t bits()const{auto r=manifest();return r.back().start+r.back().bits;}
 bool logical_bit(size_t n)const{if(n>=bits())throw std::out_of_range("controller bit");if(n<port.bits())return port.logical_bit(n);n-=port.bits();if(n<state_.bits())return state_.bit(n);n-=state_.bits();for(auto&c:commands_){if(n<c.bits())return c.bit(n);n-=c.bits();}throw std::logic_error("ingress bit");}
 void corrupt(const std::vector<size_t>&ids){std::set<size_t> unique;for(auto n:ids)if(n>=bits()||!unique.insert(n).second)throw std::invalid_argument("controller atomic sites");for(auto n:ids){if(n<port.bits()){port.corrupt({n});continue;}n-=port.bits();if(n<state_.bits()){state_.flip(n);continue;}n-=state_.bits();for(auto&c:commands_){if(n<c.bits()){c.flip(n);break;}n-=c.bits();}}}
};
}
{
  "parent_commit": "8879e43340a286225795cda258380a3c97e95ea9",
  "preserved": [
    {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/reports/CPU18_PROPOSAL.lock.json",
      "sha256": "0f580dec97adc4e10466364fcaa6be2beef9336b9a96c626714a7449e5fdb191"
    },
    {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/reports/CPU_BUILD_A1.json",
      "sha256": "28ca787c2ce3ac90aca04a9a657d53e368b50860ea2828391c17662a797bdac0"
    },
    {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/reports/early_gate_A3.json",
      "sha256": "4b6ea6dc1340aaf6d6cf8f28bcb84ecd2a3b85d83443aa68a4f94ca7cf17c9be"
    },
    {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/reports/POST_EXPORT_VERIFICATION.json",
      "sha256": "13517bd37ef9a83d219e154871413c18f26f8dc5175671a25d492ec5dd3443c2"
    },
    {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/artifacts/BP_SEU_V15_PREPARED_QUERY_EARLY.zip",
      "sha256": "23fcbbc893202b64973cf33a9e0828f8a2ab2899ee29be9353951d282a785d22"
    },
    {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/gem5_build_A1/gem5.query_early.opt",
      "sha256": "ffd9d1013f9dc567e84b984dce799626fa3609e276c0b91cddd2d66c4921854c"
    }
  ],
  "new_CPU": 0
}
{
  "result": {
    "status": "PASS_EARLY_UNCOND_ACTUAL_CHECKPOINT_PROTOCOL_NOT_CPU",
    "normal_controls": 13008,
    "nested_squash_frames": 720,
    "metadata_SBU": 848,
    "expected_DUE": 1,
    "tiny_wrap_completions": 1944,
    "max_lookup_pending_native_stream": 4,
    "CPU_trials": 0,
    "timing_cases": [
      {
        "mode": 0,
        "query_L": 1,
        "update_L": 1,
        "conditional": false,
        "early": false,
        "prediction_done_cycle": 637,
        "checkpoint_done_cycle": 640,
        "retirement_done_cycle": 767,
        "max_lookup_pending": 1
      },
      {
        "mode": 0,
        "query_L": 1,
        "update_L": 1,
        "conditional": false,
        "early": true,
        "prediction_done_cycle": 127,
        "checkpoint_done_cycle": 131,
        "retirement_done_cycle": 258,
        "max_lookup_pending": 4
      },
      {
        "mode": 0,
        "query_L": 1,
        "update_L": 1,
        "conditional": true,
        "early": false,
        "prediction_done_cycle": 637,
        "checkpoint_done_cycle": 640,
        "retirement_done_cycle": 767,
        "max_lookup_pending": 1
      },
      {
        "mode": 0,
        "query_L": 1,
        "update_L": 1,
        "conditional": true,
        "early": true,
        "prediction_done_cycle": 637,
        "checkpoint_done_cycle": 640,
        "retirement_done_cycle": 767,
        "max_lookup_pending": 1
      },
      {
        "mode": 0,
        "query_L": 2,
        "update_L": 1,
        "conditional": false,
        "early": false,
        "prediction_done_cycle": 765,
        "checkpoint_done_cycle": 768,
        "retirement_done_cycle": 895,
        "max_lookup_pending": 1
      },
      {
        "mode": 0,
        "query_L": 2,
        "update_L": 1,
        "conditional": false,
        "early": true,
        "prediction_done_cycle": 152,
        "checkpoint_done_cycle": 157,
        "retirement_done_cycle": 284,
        "max_lookup_pending": 4
      },
      {
        "mode": 0,
        "query_L": 2,
        "update_L": 1,
        "conditional": true,
        "early": false,
        "prediction_done_cycle": 765,
        "checkpoint_done_cycle": 768,
        "retirement_done_cycle": 895,
        "max_lookup_pending": 1
      },
      {
        "mode": 0,
        "query_L": 2,
        "update_L": 1,
        "conditional": true,
        "early": true,
        "prediction_done_cycle": 765,
        "checkpoint_done_cycle": 768,
        "retirement_done_cycle": 895,
        "max_lookup_pending": 1
      },
      {
        "mode": 1,
        "query_L": 1,
        "update_L": 1,
        "conditional": false,
        "early": false,
        "prediction_done_cycle": 510,
        "checkpoint_done_cycle": 513,
        "retirement_done_cycle": 640,
        "max_lookup_pending": 1
      },
      {
        "mode": 1,
        "query_L": 1,
        "update_L": 1,
        "conditional": false,
        "early": true,
        "prediction_done_cycle": 127,
        "checkpoint_done_cycle": 130,
        "retirement_done_cycle": 257,
        "max_lookup_pending": 3
      },
      {
        "mode": 1,
        "query_L": 1,
        "update_L": 1,
        "conditional": true,
        "early": false,
        "prediction_done_cycle": 510,
        "checkpoint_done_cycle": 513,
        "retirement_done_cycle": 640,
        "max_lookup_pending": 1
      },
      {
        "mode": 1,
        "query_L": 1,
        "update_L": 1,
        "conditional": true,
        "early": true,
        "prediction_done_cycle": 510,
        "checkpoint_done_cycle": 513,
        "retirement_done_cycle": 640,
        "max_lookup_pending": 1
      },
      {
        "mode": 1,
        "query_L": 2,
        "update_L": 1,
        "conditional": false,
        "early": false,
        "prediction_done_cycle": 638,
        "checkpoint_done_cycle": 641,
        "retirement_done_cycle": 768,
        "max_lookup_pending": 1
      },
      {
        "mode": 1,
        "query_L": 2,
        "update_L": 1,
        "conditional": false,
        "early": true,
        "prediction_done_cycle": 127,
        "checkpoint_done_cycle": 131,
        "retirement_done_cycle": 258,
        "max_lookup_pending": 4
      },
      {
        "mode": 1,
        "query_L": 2,
        "update_L": 1,
        "conditional": true,
        "early": false,
        "prediction_done_cycle": 638,
        "checkpoint_done_cycle": 641,
        "retirement_done_cycle": 768,
        "max_lookup_pending": 1
      },
      {
        "mode": 1,
        "query_L": 2,
        "update_L": 1,
        "conditional": true,
        "early": true,
        "prediction_done_cycle": 638,
        "checkpoint_done_cycle": 641,
        "retirement_done_cycle": 768,
        "max_lookup_pending": 1
      },
      {
        "mode": 2,
        "query_L": 1,
        "update_L": 1,
        "conditional": false,
        "early": false,
        "prediction_done_cycle": 637,
        "checkpoint_done_cycle": 640,
        "retirement_done_cycle": 767,
        "max_lookup_pending": 1
      },
      {
        "mode": 2,
        "query_L": 1,
        "update_L": 1,
        "conditional": false,
        "early": true,
        "prediction_done_cycle": 127,
        "checkpoint_done_cycle": 131,
        "retirement_done_cycle": 258,
        "max_lookup_pending": 4
      },
      {
        "mode": 2,
        "query_L": 1,
        "update_L": 1,
        "conditional": true,
        "early": false,
        "prediction_done_cycle": 637,
        "checkpoint_done_cycle": 640,
        "retirement_done_cycle": 767,
        "max_lookup_pending": 1
      },
      {
        "mode": 2,
        "query_L": 1,
        "update_L": 1,
        "conditional": true,
        "early": true,
        "prediction_done_cycle": 637,
        "checkpoint_done_cycle": 640,
        "retirement_done_cycle": 767,
        "max_lookup_pending": 1
      },
      {
        "mode": 2,
        "query_L": 2,
        "update_L": 1,
        "conditional": false,
        "early": false,
        "prediction_done_cycle": 765,
        "checkpoint_done_cycle": 768,
        "retirement_done_cycle": 895,
        "max_lookup_pending": 1
      },
      {
        "mode": 2,
        "query_L": 2,
        "update_L": 1,
        "conditional": false,
        "early": true,
        "prediction_done_cycle": 152,
        "checkpoint_done_cycle": 157,
        "retirement_done_cycle": 284,
        "max_lookup_pending": 4
      },
      {
        "mode": 2,
        "query_L": 2,
        "update_L": 1,
        "conditional": true,
        "early": false,
        "prediction_done_cycle": 765,
        "checkpoint_done_cycle": 768,
        "retirement_done_cycle": 895,
        "max_lookup_pending": 1
      },
      {
        "mode": 2,
        "query_L": 2,
        "update_L": 1,
        "conditional": true,
        "early": true,
        "prediction_done_cycle": 765,
        "checkpoint_done_cycle": 768,
        "retirement_done_cycle": 895,
        "max_lookup_pending": 1
      }
    ]
  },
  "source_lock": {
    "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/reports/early_gate_A3.source.lock.json",
    "sha256": "e9d2b2763b2056ad368ddb38b7ba7a3b73060627a6297840a56cd41788a75cf3"
  },
  "binary": {
    "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3",
    "sha256": "d7e142d5c8416dd6e74d5c04d0c2745b7c7683cd7e548510796066fa606f6a23"
  },
  "build": {
    "command": [
      "/opt/rh/gcc-toolset-11/root/usr/bin/g++",
      "-O2",
      "-g0",
      "-std=c++17",
      "-I/home/youns/workspace/ele548-project-v15/query_controls_v15/src",
      "-I/home/youns/workspace/ele548-project-v9/src",
      "-I/home/youns/workspace/ele548-project-v9/src/standalone",
      "-I/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src",
      "-static-libstdc++",
      "-static-libgcc",
      "/home/youns/workspace/ele548-project-v15/query_controls_v15/tests/early_gate.cpp",
      "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/tage_base.cc",
      "-o",
      "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3"
    ],
    "exit_code": 0,
    "stdout": {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3_build/stdout",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "stderr": {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3_build/stderr",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "time": {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3_build/job.time",
      "sha256": "99bcc22d9aa2d71b96477696a7829e6a6b575e1cb302bc01c7c26d40c36385ce"
    }
  },
  "run": {
    "command": [
      "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3"
    ],
    "exit_code": 0,
    "stdout": {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3_run/stdout",
      "sha256": "28b8ead0381cecec5dd8c8fb69474cdac6ad1f66e0e80f81f98de1d7500dac2e"
    },
    "stderr": {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3_run/stderr",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    "time": {
      "path": "/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/early_gate_A3_run/job.time",
      "sha256": "20a5d90a4a0318acad10b6d5ea765f98d31d72a5d6a11552a44446923c9b50a5"
    }
  },
  "resources": {
    "CPU_global": 3511,
    "CPU_cap": 3513,
    "CPU_new": 0,
    "reserve2": "failed-stage regression only",
    "preparation_coreh": 0.115525,
    "recent_coreh": 3.7757666666666663,
    "v9_onward_coreh": 14.947575,
    "global_coreh": 80.34603055555556,
    "v15_MiB": 64.24609375,
    "preparation_MiB": 234.50390625,
    "recent_MiB": 308.3359375,
    "all7_GiB": 7.853794097900391
  }
}
