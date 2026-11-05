#pragma once
#include "/home/youns/workspace/ele548-project-v9/src/rate_pipeline_v9/mirror_secded.hpp"
#include "inverse_jump.hpp"
#include <algorithm>
#include <array>
#include <cstdint>
#include <optional>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace bp::v18 {
enum class Mode {Recurrent,Direct,Overwrite};
enum class Kind:unsigned {Read,Append,Undo,Commit,Hold};
struct Geometry {unsigned length,width;};
struct Token {
 uint16_t id=0,epoch=0;
 bool operator==(Token b)const{return id==b.id&&epoch==b.epoch;}
 bool operator!=(Token b)const{return !(*this==b);}
 uint32_t packed()const{return uint32_t(id)|(uint32_t(epoch)<<16);}
 static Token unpack(uint32_t v){return {uint16_t(v),uint16_t(v>>16)};}
};
struct Reply {Token token;Kind kind;uint32_t source_version;std::array<unsigned,21> folds{};unsigned path=0;bool recovery=false;};
struct IntegrityError:std::runtime_error {using std::runtime_error::runtime_error;};

// Actual stored two-copy SECDED, no saved/expected payload used by decode.
struct Cell {
 v9::MirrorCell a{},b{};v9::MirrorSecded code;
 explicit Cell(unsigned n):code(n){}
 Word load(bool& repaired){auto r=code.decode(a,b);repaired|=r.repaired;return r.data;}
 void store(Word w){code.store(a,b,w);}
 unsigned bits()const{return 2*(code.data_bits()+code.check_bits());}
 bool bit(unsigned n)const{
  const unsigned stride=bits()/2;const auto& c=n<stride?a:b;n%=stride;
  return n<code.data_bits()?c.data.bit(n):(c.check>>(n-code.data_bits()))&1;
 }
 void flip(unsigned n){
  const unsigned stride=bits()/2;auto& c=n<stride?a:b;n%=stride;
  if(n<code.data_bits())c.data.flip(n);else c.check^=uint16_t(1u<<(n-code.data_bits()));
 }
};
inline uint32_t get(const Word&w,unsigned off,unsigned n){uint32_t v=0;for(unsigned i=0;i<n;++i)v|=uint32_t(w.bit(off+i))<<i;return v;}
inline void put(Word&w,unsigned off,unsigned n,uint32_t v){for(unsigned i=0;i<n;++i)w.set(off+i,(v>>i)&1);}

class Service {
 // Widths are the implemented logical encodings, not C++ sizeof values.
 struct Header {
  unsigned qh=0,qt=0,qn=0,rh=0,rt=0,rn=0,head=0,depth=0,reserved=0,id=1,epoch=0,gap=0;
  uint32_t rawver=0,foldver=0;
  bool wrap=false,ack=false,kill=false,turn=false,issued=false,consumed=false,cancel_pending=false;
 };
 struct Meta {
  bool valid=false;Kind kind=Kind::Read;Token token{};unsigned n=0,bits=0,arg=0;uint32_t version=0;
 };
 struct Payload {
  std::array<uint8_t,130> raw{},before{};
  std::array<unsigned,21> input{},partial{},before_partial{};
  std::array<std::array<uint8_t,7>,2> outgoing{};std::array<uint8_t,2> incoming{};
  unsigned path=0;
 };
 struct Entry {Cell meta{88};Payload data{};};
 Cell header_{156};
 std::array<Entry,4> commands_,responses_;
 std::vector<Entry> updates_,lookups_;
 std::array<uint8_t,1130> raw_{};unsigned path_=0;
 std::array<unsigned,21> folds_{};
 uint64_t cycle_=0,hold_until_=0;
 std::vector<Geometry> geometry_;
 Mode mode_;unsigned update_L_,lookup_L_,ii_,id_mask_,epoch_mask_;
 static Word pack(const Header&h){
  Word w;put(w,0,2,h.qh);put(w,2,2,h.qt);put(w,4,3,h.qn);
  put(w,7,2,h.rh);put(w,9,2,h.rt);put(w,11,3,h.rn);
  put(w,14,11,h.head);put(w,25,10,h.depth);put(w,35,10,h.reserved);
  put(w,45,16,h.id);put(w,61,16,h.epoch);put(w,77,32,h.rawver);put(w,109,32,h.foldver);put(w,141,8,h.gap);
  w.set(149,h.wrap);w.set(150,h.ack);w.set(151,h.kill);w.set(152,h.turn);w.set(153,h.issued);w.set(154,h.consumed);w.set(155,h.cancel_pending);return w;
 }
 static Header unpack(const Word&w){
  Header h;h.qh=get(w,0,2);h.qt=get(w,2,2);h.qn=get(w,4,3);h.rh=get(w,7,2);h.rt=get(w,9,2);h.rn=get(w,11,3);
  h.head=get(w,14,11);h.depth=get(w,25,10);h.reserved=get(w,35,10);h.id=get(w,45,16);h.epoch=get(w,61,16);
  h.rawver=get(w,77,32);h.foldver=get(w,109,32);h.gap=get(w,141,8);
  h.wrap=w.bit(149);h.ack=w.bit(150);h.kill=w.bit(151);h.turn=w.bit(152);h.issued=w.bit(153);h.consumed=w.bit(154);h.cancel_pending=w.bit(155);return h;
 }
 static Word pack(const Meta&m){Word w;w.set(0,m.valid);put(w,1,3,unsigned(m.kind));put(w,4,32,m.token.packed());put(w,36,2,m.n);put(w,38,2,m.bits);put(w,40,16,m.arg);put(w,56,32,m.version);return w;}
 static Meta unpack_meta(const Word&w){return {w.bit(0),Kind(get(w,1,3)),Token::unpack(get(w,4,32)),get(w,36,2),get(w,38,2),get(w,40,16),get(w,56,32)};}
 Header hload(){bool repaired=false;auto h=unpack(header_.load(repaired));if(repaired)repair();return h;}
 Meta mload(Entry&e){bool repaired=false;auto m=unpack_meta(e.meta.load(repaired));if(repaired)repair();return m;}
 static Meta observe(const Entry&e){return unpack_meta(e.meta.a.data);}
 void hstore(const Header&h){header_.store(pack(h));}
 static void mstore(Entry&e,const Meta&m){e.meta.store(pack(m));}
 void repair(){++stats.metadata_repairs;hold_until_=std::max(hold_until_,cycle_+1);}
 void apply_cancel(Header&h){
  if(h.wrap||h.epoch==epoch_mask_){if(!h.wrap)++stats.wrap_drains;h.wrap=true;h.kill=true;h.ack=false;}
  else ++h.epoch;
  h.cancel_pending=false;
 }
 bool stale(const Header&h,const Meta&m)const{return m.kind==Kind::Read&&(h.kill||m.token.epoch!=h.epoch);}
 static bool bulk(const Meta&m){return m.kind==Kind::Undo&&m.n>2;}
 static bool arithmetic(const Meta&m){return (m.kind==Kind::Append||m.kind==Kind::Undo)&&m.n;}
 bool raw_bit(const Header&h,unsigned age)const{return raw_[(h.head+age)%raw_.size()]&1;}
 SourceGuard::Words selected_for(const Header&h)const{
  SourceGuard::Words out{};if(mode_!=Mode::Direct)for(unsigned w=0;w<21;++w)out[w].limb[0]=folds_[w];
  for(unsigned age=0;age<130;++age)out[21].set(age,raw_bit(h,age));out[22].limb[0]=path_;return out;
 }
 unsigned mask(unsigned word)const{return (1u<<geometry_[word].width)-1;}
 unsigned recurrent_word(const Meta&m,const Payload&p,unsigned w)const{
  unsigned v=p.input[w],width=geometry_[w].width,outpoint=geometry_[w].length%width;
  for(unsigned n=0;n<m.n;++n){
   if(m.kind==Kind::Append){v=(v<<1)|p.incoming[n];v^=unsigned(p.outgoing[n][w/3])<<outpoint;v^=v>>width;v&=mask(w);}
   else {v^=unsigned(p.outgoing[n][w/3])<<outpoint;auto top=(v&1)^p.incoming[n];v=(top<<(width-1))|(v>>1);}
  }return v;
 }
 std::array<unsigned,21> reduce(const Entry&e,const Meta&m,bool lookup,bool low,bool high)const{
  auto out=e.data.partial;
  if(!lookup&&mode_==Mode::Recurrent&&bulk(m)){
   for(unsigned w=0;w<21;++w){
    unsigned pre=low?0:e.data.before_partial[w],post=low?0:e.data.partial[w];
    const unsigned begin=low?0:65,end=high?geometry_[w].length:std::min(65u,geometry_[w].length);
    for(unsigned age=begin;age<end;++age){if(e.data.before[age]&1)pre^=1u<<(age%geometry_[w].width);if(e.data.raw[age]&1)post^=1u<<(age%geometry_[w].width);}
    if(high){const unsigned width=geometry_[w].width,r=m.n%width,d=e.data.input[w]^pre;
     out[w]=((r?((d>>r)|(d<<(width-r))):d)&mask(w))^post;
    }else out[w]=post;
   }return out;
  }
  const bool full=(lookup?mode_==Mode::Direct:mode_==Mode::Overwrite);
  for(unsigned w=0;w<21;++w){
   if(full){
    if(low){out[w]=0;for(unsigned age=0;age<std::min(65u,geometry_[w].length);++age)if(e.data.raw[age])out[w]^=1u<<(age%geometry_[w].width);}
    if(high)for(unsigned age=65;age<geometry_[w].length;++age)if(e.data.raw[age])out[w]^=1u<<(age%geometry_[w].width);
   }else if((low&&w<10)||(high&&w>=10))out[w]=lookup?e.data.input[w]:recurrent_word(m,e.data,w);
  }return out;
 }
 bool empty(const Header&h)const{
  if(h.qn||h.rn)return false;
  for(const auto&e:updates_)if(observe(e).valid)return false;
  for(const auto&e:lookups_)if(observe(e).valid)return false;
  return true;
 }
 void pop_command(Header&h){mstore(commands_[h.qh],{});h.qh=(h.qh+1)%4;--h.qn;}
 void push_response(Header&h,const Meta&m,const std::array<unsigned,21>&data,unsigned path){
  auto& e=responses_[h.rt];mstore(e,m);e.data.input=data;e.data.path=path;
  h.rt=(h.rt+1)%4;++h.rn;++stats.produced;
 }
 bool finish(std::vector<Entry>&lane,Header&h,bool lookup,bool&write_used){
  auto& e=lane.back();auto m=mload(e);if(!m.valid)return false;
  if(stale(h,m)){mstore(e,{});++stats.cancelled;++stats.stale_discarded;return true;}
  if(write_used||h.rn==4){++stats.response_stalls;return false;}
  std::array<unsigned,21> out{};
  if(lookup||arithmetic(m)&&mode_!=Mode::Direct){
   out=reduce(e,m,lookup,lane.size()==1,true);
   if(lookup)++stats.lookup_reductions;else ++stats.update_reductions;
  }
  if(!lookup&&arithmetic(m)&&mode_!=Mode::Direct){folds_=out;h.foldver=m.version;++stats.fold_publications;}
  push_response(h,m,lookup?out:std::array<unsigned,21>{},lookup?e.data.path:0);
  mstore(e,{});write_used=true;h.turn=!h.turn;return true;
 }
 void shift(std::vector<Entry>&lane,const Header&h,bool lookup){
  if(lane.size()!=2)return;
  auto a=mload(lane[0]),b=mload(lane[1]);if(!a.valid||b.valid)return;
  if(!stale(h,a)&&(lookup||arithmetic(a))){
   lane[0].data.partial=reduce(lane[0],a,lookup,true,false);
   if(!lookup&&mode_==Mode::Recurrent&&bulk(a)){
    for(unsigned w=0;w<21;++w){unsigned v=0;for(unsigned age=0;age<std::min(65u,geometry_[w].length);++age)if(lane[0].data.before[age]&1)v^=1u<<(age%geometry_[w].width);lane[0].data.before_partial[w]=v;}
   }
   ++stats.partial_stages;
  }
  lane[1].data=lane[0].data;mstore(lane[1],a);mstore(lane[0],{});
 }
 void dispatch(Header&h){
  if(!h.qn)return;auto m=mload(commands_[h.qh]);
  if(stale(h,m)){pop_command(h);++stats.cancelled;++stats.stale_discarded;return;}
  const bool lookup=m.kind==Kind::Read;
  auto& lane=lookup?lookups_:updates_;
  if(mload(lane[0]).valid){++stats.stage_stalls;return;}
  if(mode_!=Mode::Direct&&h.foldver!=h.rawver&&(lookup||mode_==Mode::Recurrent&&arithmetic(m))){++stats.dependency_stalls;return;}
  Payload p;
  if(lookup){
   if(mode_==Mode::Direct)for(unsigned a=0;a<130;++a)p.raw[a]=raw_bit(h,a);
   else p.input=folds_;
   p.path=path_;m.version=h.rawver;++stats.lookup_samples;
  }else{
   p.input=folds_;
   if(m.kind==Kind::Append){
    if(h.depth+m.n>1000)throw IntegrityError("source retention overflow at service");
    for(unsigned n=0;n<m.n;++n){
     h.head=(h.head+raw_.size()-1)%raw_.size();raw_[h.head]=(m.bits>>n)&1;
     p.incoming[n]=raw_bit(h,0);
     for(unsigned b=0;b<7;++b)p.outgoing[n][b]=raw_bit(h,geometry_[b*3].length);
    }
    h.depth+=m.n;path_=((path_<<1)|(m.arg&1))&65535;
   }else if(m.kind==Kind::Undo){
    if(m.n>h.depth||m.n>h.reserved)throw IntegrityError("undo outside reserved source");
    if(bulk(m)){
     if(mode_==Mode::Recurrent)for(unsigned age=0;age<130;++age)p.before[age]=raw_bit(h,age);
     h.head=(h.head+m.n)%raw_.size();
     if(mode_==Mode::Recurrent)for(unsigned age=0;age<130;++age)p.raw[age]=raw_bit(h,age);
     ++stats.bulk_undos;stats.bulk_bits+=m.n;
    }else for(unsigned n=0;n<m.n;++n){
     p.incoming[n]=raw_bit(h,0);
     for(unsigned b=0;b<7;++b)p.outgoing[n][b]=raw_bit(h,geometry_[b*3].length);
     h.head=(h.head+1)%raw_.size();
    }
    h.depth-=m.n;h.reserved-=m.n;path_=m.arg;
   }else if(m.kind==Kind::Commit){
    if(m.n>h.depth||m.n>h.reserved)throw IntegrityError("commit outside reserved source");
    h.depth-=m.n;h.reserved-=m.n;
   }
   if(arithmetic(m)){
    h.rawver=m.token.packed();if(mode_==Mode::Direct)h.foldver=h.rawver;
    if(mode_==Mode::Overwrite)for(unsigned a=0;a<130;++a)p.raw[a]=raw_bit(h,a);
   }
   m.version=h.rawver;++stats.source_services;
  }
  lane[0].data=p;mstore(lane[0],m);pop_command(h);++stats.started;
 }
 void validate(const Header&h){
  if(h.qn>4||h.rn>4||h.head>=1130||h.depth>1000||h.reserved>1000||h.depth>h.reserved||h.id>id_mask_||h.epoch>epoch_mask_)throw IntegrityError("illegal source/control range");
  for(unsigned j=0;j<4;++j){
   bool qlive=false,rlive=false;for(unsigned n=0;n<h.qn;++n)qlive|=j==(h.qh+n)%4;for(unsigned n=0;n<h.rn;++n)rlive|=j==(h.rh+n)%4;
   if(mload(commands_[j]).valid!=qlive||mload(responses_[j]).valid!=rlive)throw IntegrityError("FIFO occupancy/valid mismatch");
  }
  auto check=[&](Entry&e){auto m=mload(e);if(m.valid&&(unsigned(m.kind)>4||m.n>1000||(m.kind==Kind::Append&&(!m.n||m.n>2))||((m.kind==Kind::Read||m.kind==Kind::Hold)&&m.n)||m.token.epoch>epoch_mask_||m.token.id>id_mask_))throw IntegrityError("illegal transaction metadata");};
  for(auto&e:commands_)check(e);for(auto&e:responses_)check(e);for(auto&e:updates_)check(e);for(auto&e:lookups_)check(e);
 }
 bool poll(){
  try{
   auto h=hload();for(auto&e:commands_)mload(e);for(auto&e:responses_)mload(e);for(auto&e:updates_)mload(e);for(auto&e:lookups_)mload(e);validate(h);
   return cycle_>=hold_until_;
  }catch(const v9::MirrorUncorrectable&e){++stats.integrity_failures;throw IntegrityError(e.what());}
 }
 unsigned field_bit(const std::array<unsigned,21>&a,unsigned bit)const{
  for(unsigned w=0;w<21;++w){if(bit<geometry_[w].width)return (a[w]>>bit)&1;bit-=geometry_[w].width;}throw std::out_of_range("fold bit");
 }
 void flip_field(std::array<unsigned,21>&a,unsigned bit){
  for(unsigned w=0;w<21;++w){if(bit<geometry_[w].width){a[w]^=1u<<bit;return;}bit-=geometry_[w].width;}throw std::out_of_range("fold bit");
 }
 unsigned payload_bits(bool lookup,unsigned stage,bool response=false)const{
  if(response)return 216;
  unsigned n=lookup?(mode_==Mode::Direct?130:200)+16:
     mode_==Mode::Direct?0:mode_==Mode::Overwrite?130:476;
  return n+(stage==1?(lookup||mode_!=Mode::Recurrent?200:400):0);
 }
 bool payload_bit(const Payload&p,unsigned n,bool lookup,unsigned stage,bool response=false)const{
  if(response){return n<200?field_bit(p.input,n):(p.path>>(n-200))&1;}
  const unsigned base=payload_bits(lookup,0);
  if(n>=base){n-=base;return n<200?field_bit(p.partial,n):field_bit(p.before_partial,n-200);}
  if(lookup){const unsigned data=mode_==Mode::Direct?130:200;if(n>=data)return (p.path>>(n-data))&1;return mode_==Mode::Direct?p.raw[n]:field_bit(p.input,n);}
  if(mode_==Mode::Overwrite)return p.raw[n];
  if(n<200)return field_bit(p.input,n);n-=200;if(n<2)return p.incoming[n];n-=2;if(n<14)return p.outgoing[n/7][n%7];n-=14;return n<130?p.before[n]:p.raw[n-130];
 }
 void flip_payload(Payload&p,unsigned n,bool lookup,unsigned stage,bool response=false){
  if(response){if(n<200)flip_field(p.input,n);else p.path^=1u<<(n-200);return;}
  const unsigned base=payload_bits(lookup,0);
  if(n>=base){n-=base;if(n<200)flip_field(p.partial,n);else flip_field(p.before_partial,n-200);return;}
  if(lookup){const unsigned data=mode_==Mode::Direct?130:200;if(n>=data)p.path^=1u<<(n-data);else if(mode_==Mode::Direct)p.raw[n]^=1;else flip_field(p.input,n);return;}
  if(mode_==Mode::Overwrite){p.raw[n]^=1;return;}
  if(n<200){flip_field(p.input,n);return;}n-=200;if(n<2)p.incoming[n]^=1;else{n-=2;if(n<14)p.outgoing[n/7][n%7]^=1;else{n-=14;if(n<130)p.before[n]^=1;else p.raw[n-130]^=1;}}
 }
 public:
 struct Counters {
  uint64_t bulk_undos=0,bulk_bits=0;
  uint64_t accepted=0,started=0,produced=0,completed=0,cancelled=0;
  uint64_t source_services=0,lookup_samples=0,lookup_reductions=0,update_reductions=0,partial_stages=0,fold_publications=0;
  uint64_t input_full_stalls=0,stage_stalls=0,response_stalls=0,dependency_stalls=0,II_stalls=0,credit_stalls=0;
  uint64_t metadata_repairs=0,integrity_failures=0,stale_discarded=0,wrap_drains=0,wrap_completions=0;
 } stats;
 Service(Mode mode,std::vector<Geometry> geometry,unsigned update_L=1,unsigned lookup_L=1,unsigned ii=1,unsigned id_bits=16,unsigned epoch_bits=16):
  updates_(mode==Mode::Direct?1:update_L),lookups_(lookup_L),geometry_(std::move(geometry)),mode_(mode),update_L_(update_L),lookup_L_(lookup_L),ii_(ii),
  id_mask_((1u<<std::min(16u,id_bits))-1),epoch_mask_((1u<<std::min(16u,epoch_bits))-1){
  if((update_L!=1&&update_L!=2)||(lookup_L!=1&&lookup_L!=2)||ii<1||ii>64||id_bits<2||id_bits>16||epoch_bits<2||epoch_bits>16)throw std::invalid_argument("finite service geometry");
  if(geometry_.size()!=21)throw std::invalid_argument("21-fold geometry required");
  unsigned width=0;for(unsigned w=0;w<21;++w){auto g=geometry_[w];if(!g.length||g.length>130||!g.width||g.width>16||g.length!=geometry_[w/3*3].length)throw std::invalid_argument("pinned fold geometry");width+=g.width;}
  if(width!=200)throw std::invalid_argument("200-bit fold boundary required");
  hstore(Header{});for(auto&e:commands_)mstore(e,{});for(auto&e:responses_)mstore(e,{});for(auto&e:updates_)mstore(e,{});for(auto&e:lookups_)mstore(e,{});
 }
 uint64_t cycle()const{return cycle_;}
 // S* is the active raw130/path16/fold200, not the1130-bit retention ring.
 // Word order is the existing frozen21 folded words, raw130, path16.
 std::array<Word,23> selected_words(){
  if(!poll())throw IntegrityError("selected source sampled during metadata hold");
  auto h=hload();if(mode_!=Mode::Direct&&h.rawver!=h.foldver)throw IntegrityError("selected source sampled before fold publication");
  std::array<Word,23> out{};
  if(mode_!=Mode::Direct)for(unsigned w=0;w<21;++w)out[w].limb[0]=folds_[w];
  for(unsigned age=0;age<130;++age)out[21].set(age,raw_bit(h,age));out[22].limb[0]=path_;return out;
 }
 std::array<unsigned,23> selected_widths()const{
  std::array<unsigned,23> out{};for(unsigned w=0;w<21;++w)out[w]=geometry_[w].width;out[21]=130;out[22]=16;return out;
 }
 size_t selected_site(unsigned word,unsigned bit){
  auto widths=selected_widths();if(word>=23||bit>=widths[word])throw std::out_of_range("selected logical word bit");
  if(!poll())throw IntegrityError("selected mapping during metadata hold");auto h=hload();
  if(word==21)return (h.head+bit)%1130;
  if(word==22)return 1130+bit;
  if(mode_==Mode::Direct)throw std::invalid_argument("Direct has no stored folded bit");
  size_t at=1146;for(unsigned w=0;w<word;++w)at+=widths[w];return at+bit;
 }
 void write_selected_word(unsigned word,const Word&value){
  auto widths=selected_widths();if(word>=23)throw std::out_of_range("selected write word");
  if(!value.fits(widths[word]))throw std::invalid_argument("nonlogical selected upper bit");
  if(!poll())throw IntegrityError("selected write during metadata hold");auto h=hload();
  if(word<21){if(mode_==Mode::Direct)throw std::invalid_argument("Direct has no folded write");folds_[word]=unsigned(value.limb[0]);}
  else if(word==21)for(unsigned age=0;age<130;++age)raw_[(h.head+age)%1130]=value.bit(age);
  else path_=unsigned(value.limb[0]);
 }
 std::optional<Token> accept(Kind kind,unsigned n=0,unsigned bits=0,unsigned arg=0,bool recovery=false){
  if(unsigned(kind)>4||n>1000||(kind==Kind::Append&&n>2)||bits>3||arg>65535||((kind==Kind::Read||kind==Kind::Hold)&&n)||kind==Kind::Append&&!n)throw std::invalid_argument("invalid service command");
  if(!poll())return {};auto h=hload();
  if(h.wrap)return {};
  if(h.qn==4){++stats.input_full_stalls;return {};}
  if(h.issued||h.gap){++stats.II_stalls;return {};}
  if(kind==Kind::Append&&h.reserved+n>1000){++stats.credit_stalls;return {};}
  Token t{uint16_t(h.id),uint16_t(h.epoch)};Meta m{true,kind,t,n,bits,arg,0};m.recovery=recovery;
  mstore(commands_[h.qt],m);h.qt=(h.qt+1)%4;++h.qn;
  if(kind==Kind::Append)h.reserved+=n;
  if(h.id==id_mask_){h.wrap=true;h.ack=false;++stats.wrap_drains;}else ++h.id;
  h.issued=true;h.gap=ii_;hstore(h);++stats.accepted;return t;
 }
 void tick(){
  ++cycle_;if(!poll())return;auto h=hload();if(h.cancel_pending)apply_cancel(h);h.issued=false;h.consumed=false;if(h.gap)--h.gap;
  if(h.rn){auto m=mload(responses_[h.rh]);if(stale(h,m)){mstore(responses_[h.rh],{});h.rh=(h.rh+1)%4;--h.rn;h.consumed=true;++stats.cancelled;++stats.stale_discarded;}}
  bool used=false;
  if(h.turn){finish(lookups_,h,true,used);finish(updates_,h,false,used);}
  else {finish(updates_,h,false,used);finish(lookups_,h,true,used);}
  shift(updates_,h,false);shift(lookups_,h,true);dispatch(h);
  if(h.wrap&&h.ack&&empty(h)){h.epoch=(h.epoch+1)&epoch_mask_;h.id=1;h.wrap=false;h.kill=false;h.ack=false;++stats.wrap_completions;}
  hstore(h);
 }
 std::optional<Reply> take(std::optional<Token> expected={}){
  if(!poll())return {};auto h=hload();if(h.consumed||!h.rn)return {};
  auto&mcell=responses_[h.rh];auto m=mload(mcell);
  if(stale(h,m)||expected&&m.token!=*expected)return {};
  Reply out{m.token,m.kind,m.version,mcell.data.input,mcell.data.path};mstore(mcell,{});
  h.rh=(h.rh+1)%4;--h.rn;h.consumed=true;hstore(h);++stats.completed;return out;
 }
 void cancel_reads(){
  const bool ready=poll();auto h=hload();
  // Correctable metadata has now been repaired in actual cells, but service
  // must wait. Preserve the squash request in an exposed protected bit. No
  // caller retry is required, and no old response can escape during the hold.
  if(ready)apply_cancel(h);else h.cancel_pending=true;
  hstore(h);
 }
 bool acknowledge_receiver_drained(){
  if(!poll())return false;auto h=hload();if(!h.wrap||!empty(h))return false;h.ack=true;hstore(h);return true;
 }
 bool drained(){if(!poll())return false;return empty(hload());}
 bool wrap_waiting(){if(!poll())return false;return hload().wrap;}
 bool coherent(){if(!poll())return false;auto h=hload();return h.rawver==h.foldver;}
 unsigned source_path(){if(!poll())throw IntegrityError("source read while metadata held");return path_;}
 unsigned source_depth(){if(!poll())throw IntegrityError("depth read while metadata held");return hload().depth;}
 struct Observation {std::array<uint8_t,130> raw;std::array<unsigned,21> folds;unsigned path;};
 // Read-only software observation, no correcting accessor, no golden state.
 // Not an additional free production port. Used only by the native TAGE
 // verification harness and scoreboards, never by service/recovery decisions.
 Observation observe_source()const{
  auto h=unpack(header_.a.data);if(h.head>=1130)throw IntegrityError("invalid observed source head");
  Observation out{{},folds_,path_};for(unsigned i=0;i<130;++i)out.raw[i]=raw_bit(h,i);return out;
 }
 bool source_bit(unsigned age){if(age>=130)throw std::out_of_range("active source age");if(!poll())throw IntegrityError("source read while metadata held");return raw_bit(hload(),age);}
 std::array<unsigned,21> stored_folds(){if(mode_==Mode::Direct)throw std::logic_error("direct has no stored folds");if(!poll())throw IntegrityError("fold read while metadata held");return folds_;}
 uint64_t pending()const{
  auto h=unpack(header_.a.data);uint64_t n=std::min(h.qn,4u)+std::min(h.rn,4u);
  for(auto&e:updates_)n+=observe(e).valid;for(auto&e:lookups_)n+=observe(e).valid;return n;
 }
 bool conserved()const{return stats.accepted==stats.completed+stats.cancelled+pending();}
 struct Region {std::string name;size_t start,bits;};
 std::vector<Region> manifest()const{
  std::vector<Region> r;size_t at=0;auto add=[&](std::string s,size_t n){if(n){r.push_back({s,at,n});at+=n;}};
  add("raw_ring",1130);add("path",16);if(mode_!=Mode::Direct)add("fold",200);add("controller_mirrored_SECDED",header_.bits());
  for(unsigned i=0;i<4;++i)add("command_metadata_"+std::to_string(i),commands_[i].meta.bits());
  for(unsigned i=0;i<4;++i){add("response_metadata_"+std::to_string(i),responses_[i].meta.bits());add("response_payload_"+std::to_string(i),216);}
  for(unsigned i=0;i<updates_.size();++i){add("update_metadata_"+std::to_string(i),updates_[i].meta.bits());add("update_payload_"+std::to_string(i),payload_bits(false,i));}
  for(unsigned i=0;i<lookups_.size();++i){add("lookup_metadata_"+std::to_string(i),lookups_[i].meta.bits());add("lookup_payload_"+std::to_string(i),payload_bits(true,i));}
  return r;
 }
 size_t bits()const{auto r=manifest();return r.back().start+r.back().bits;}
 size_t active_raw_site(unsigned age)const{if(age>=130)throw std::out_of_range("active raw site");auto h=unpack(header_.a.data);if(h.head>=1130)throw IntegrityError("cannot resolve active alias with invalid source head");return (h.head+age)%1130;}
 bool logical_bit(size_t id)const {
  if(id>=bits())throw std::out_of_range("service logical bit");
  if(id<1130)return raw_[id];id-=1130;if(id<16)return (path_>>id)&1;id-=16;
  if(mode_!=Mode::Direct){if(id<200)return field_bit(folds_,id);id-=200;}
  if(id<header_.bits())return header_.bit(id);id-=header_.bits();
  for(const auto&e:commands_){if(id<e.meta.bits())return e.meta.bit(id);id-=e.meta.bits();}
  for(const auto&e:responses_){if(id<e.meta.bits())return e.meta.bit(id);id-=e.meta.bits();if(id<216)return payload_bit(e.data,id,true,0,true);id-=216;}
  for(unsigned i=0;i<updates_.size();++i){const auto&e=updates_[i];if(id<e.meta.bits())return e.meta.bit(id);id-=e.meta.bits();auto n=payload_bits(false,i);if(id<n)return payload_bit(e.data,id,false,i);id-=n;}
  for(unsigned i=0;i<lookups_.size();++i){const auto&e=lookups_[i];if(id<e.meta.bits())return e.meta.bit(id);id-=e.meta.bits();auto n=payload_bits(true,i);if(id<n)return payload_bit(e.data,id,true,i);id-=n;}
  throw std::logic_error("manifest traversal");
 }
 void flip_one(size_t id){
  if(id<1130){raw_[id]^=1;return;}id-=1130;if(id<16){path_^=1u<<id;return;}id-=16;
  if(mode_!=Mode::Direct){if(id<200){flip_field(folds_,id);return;}id-=200;}
  if(id<header_.bits()){header_.flip(id);return;}id-=header_.bits();
  for(auto&e:commands_){if(id<e.meta.bits()){e.meta.flip(id);return;}id-=e.meta.bits();}
  for(auto&e:responses_){if(id<e.meta.bits()){e.meta.flip(id);return;}id-=e.meta.bits();if(id<216){flip_payload(e.data,id,true,0,true);return;}id-=216;}
  for(unsigned i=0;i<updates_.size();++i){auto&e=updates_[i];if(id<e.meta.bits()){e.meta.flip(id);return;}id-=e.meta.bits();auto n=payload_bits(false,i);if(id<n){flip_payload(e.data,id,false,i);return;}id-=n;}
  for(unsigned i=0;i<lookups_.size();++i){auto&e=lookups_[i];if(id<e.meta.bits()){e.meta.flip(id);return;}id-=e.meta.bits();auto n=payload_bits(true,i);if(id<n){flip_payload(e.data,id,true,i);return;}id-=n;}
  throw std::out_of_range("service bit");
 }
 void corrupt(const std::vector<size_t>&ids){std::set<size_t> unique;for(auto id:ids)if(id>=bits()||!unique.insert(id).second)throw std::invalid_argument("invalid atomic service event");for(auto id:ids)flip_one(id);}
};
} // namespace bp::v18
