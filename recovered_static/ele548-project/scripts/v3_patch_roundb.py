"""Generate isolated Round B controller variants from the audited A controller."""
from pathlib import Path
root=Path(__file__).resolve().parents[1];src=root/'src/costaware_v3';dst=root/'src/costaware_v3_roundb'
for name in ['history_access.hpp','state.hpp','role_history.hpp','role_spec_history.hpp','role_adapter.hpp','scheduled.cpp','correctness.cpp','fault_properties.cpp']:
 s=(src/name).read_text()
 for a,b in [('CostAccess','RoundAccess'),('CostState','RoundState'),('CostHistory','RoundHistory'),('CostProtocol','RoundProtocol'),('CostAdapter','RoundAdapter'),('CostPolicy','RoundPolicy'),('CostTransition','RoundTransition')]:s=s.replace(a,b)
 s=s.replace('costaware_v3/','costaware_v3_roundb/');(dst/name).write_text(s)
p=dst/'history_access.hpp';s=p.read_text();position=s.rindex('\n};')
s=s[:position]+'''
 void admitted(unsigned mask){for(unsigned i=1;i<=nHistoryTables;++i)noSkip[i]=(mask>>(i-1))&1;}
 protected:
 void handleAllocAndUReset(bool alloc,bool taken,Base::BranchInfo* bi,int nrand) override {
  bool all=true;for(unsigned i=1;i<=nHistoryTables;++i)all&=noSkip[i];
  if(all){Base::handleAllocAndUReset(alloc,taken,bi,nrand);return;}
  if(alloc){
   uint8_t minimum=1;for(int i=nHistoryTables;i>bi->hitBank;--i)if(noSkip[i])minimum=std::min(minimum,gtable[i][bi->tableIndices[i]].u);
   int Y=nrand&((1ULL<<(nHistoryTables-bi->hitBank-1))-1);int X=bi->hitBank+1;if(Y&1){++X;if(Y&2)++X;}
   while(X<=int(nHistoryTables)&&!noSkip[X])++X;
   if(X<=int(nHistoryTables)){
    if(minimum>0)gtable[X][bi->tableIndices[X]].u=0;
    unsigned allocated=0;for(int i=X;i<=int(nHistoryTables);++i)if(noSkip[i]&&gtable[i][bi->tableIndices[i]].u==0){gtable[i][bi->tableIndices[i]].tag=bi->tableTags[i];gtable[i][bi->tableIndices[i]].ctr=taken?0:-1;if(++allocated==maxNumAlloc)break;}
   }
  }
  // Keep the upstream aging schedule; only invalid-bank allocations are blocked.
  Base::handleAllocAndUReset(false,taken,bi,nrand);
 }
''' +s[position:];p.write_text(s)
p=dst/'role_history.hpp';s=p.read_text().replace('LEGACY,N1,H1,REV','LEGACY,N1,H1,REV,STAGED')
s=s.replace('const bool full_delta,reset_recovery;', 'const bool full_delta,reset_recovery,external_shadow;')
s=s.replace('bool full=false,bool reset=false):core(c)', 'bool full=false,bool reset=false,bool separate=false):core(c)').replace('reset_recovery(reset){','reset_recovery(reset),external_shadow(separate){')
s=s.replace('policy==RoundPolicy::N1||policy==RoundPolicy::H1','policy==RoundPolicy::N1||policy==RoundPolicy::H1||policy==RoundPolicy::STAGED')
s=s.replace('p==RoundPolicy::N1||p==RoundPolicy::H1','p==RoundPolicy::N1||p==RoundPolicy::H1||p==RoundPolicy::STAGED')
s=s.replace('p==RoundPolicy::N1)mode.assign','(p==RoundPolicy::N1||p==RoundPolicy::STAGED))mode.assign')
s=s.replace('policy!=RoundPolicy::N1&&policy!=RoundPolicy::H1','policy!=RoundPolicy::N1&&policy!=RoundPolicy::H1&&policy!=RoundPolicy::STAGED')
s=s.replace('policy==RoundPolicy::N1?0:', '(policy==RoundPolicy::N1||policy==RoundPolicy::STAGED)?0:')
s=s.replace('if(committed&&refill)', 'if(committed&&refill&&policy!=RoundPolicy::STAGED)')
s=s.replace('core.tagged_enabled(!fallback());', 'apply_admission();')
s=s.replace('core.tagged_enabled(true);', 'apply_admission();')
s=s.replace('std::array<Word,2> shadow{};', 'Word stage_state{};uint16_t stage_check=0;WordSecded stage_codec{16};\n uint32_t shadow_generation=0;uint16_t generation_check=0;WordSecded generation_codec{32};\n std::array<Word,2> shadow{};')
s=s.replace('void reset_refill(){core.reset_selected_history();', 'void reset_refill(){if(external_shadow){++shadow_generation;Word g;g.limb[0]=shadow_generation;generation_check=generation_codec.encode(g);}if(policy==RoundPolicy::STAGED){stage_state={};stage_state.set(15,true);stage_check=stage_codec.encode(stage_state);}core.reset_selected_history();')
s=s.replace(' struct Snapshot {', ' struct Snapshot {Word stage_state;uint16_t stage_check;uint32_t shadow_generation;uint16_t generation_check;')
s=s.replace('return {checks,a,b,refill,', 'return {stage_state,stage_check,shadow_generation,generation_check,checks,a,b,refill,')
s=s.replace('checks=s.checks;a=s.a;', 'stage_state=s.stage_state;stage_check=s.stage_check;shadow_generation=s.shadow_generation;generation_check=s.generation_check;checks=s.checks;a=s.a;')
s=s.replace('bool fallback()const{return refill||(cpu_protocol&&recovery_active)||phase;}', 'bool fallback()const{if(policy==RoundPolicy::STAGED)return (stage_active()&&!ready_mask())||(cpu_protocol&&recovery_active);return refill||(cpu_protocol&&recovery_active)||phase;}')
s=s.replace(' bool check(bool boundary=false){', ' bool check(bool boundary=false){\n  if(policy==RoundPolicy::STAGED&&!validate_stage())return true;')
s=s.replace('void commit_source(uint64_t pc,bool taken){if(policy!=RoundPolicy::H1)return;validate_shadow();', 'void commit_source(uint64_t pc,bool taken){if(policy==RoundPolicy::STAGED){stage_commit();return;}if(policy!=RoundPolicy::H1||external_shadow)return;commit_shadow_complete(pc,taken);}\n void commit_shadow_complete(uint64_t pc,bool taken){validate_shadow();')
s=s.replace('void complete_cpu_drain(){if(refill)', 'void complete_cpu_drain(){if(policy==RoundPolicy::STAGED){if(!validate_stage())return;set_stage(stage_count(),eligible_mask(),eligible_mask()!=127);recovery_active=false;apply_admission();return;}if(refill)')
# Finish constructor: coded role state exists only for variants that use it.
anchor='\n }\n struct Snapshot'
init='''
  if(policy==RoundPolicy::STAGED){set_stage(0,127,false);for(unsigned bit=0;bit<16;++bit)extra.push_back({id++,"staged_control",0,bit,16,0});for(unsigned bit=0;bit<stage_codec.r+1;++bit)extra.push_back({id++,"staged_control_check",0,bit,stage_codec.r+1,0});}
  if(external_shadow){Word g;g.limb[0]=shadow_generation;generation_check=generation_codec.encode(g);for(unsigned bit=0;bit<32;++bit)extra.push_back({id++,"shadow_generation",0,bit,32,0});for(unsigned bit=0;bit<generation_codec.r+1;++bit)extra.push_back({id++,"shadow_generation_check",0,bit,generation_codec.r+1,0});}
'''
s=s.replace(anchor,init+anchor)
# Controller checks use only stored codes/counts/epochs; no fault map or oracle.
anchor=' bool inspection_due()const'
methods='''
 unsigned stage_count()const{return unsigned(stage_state.limb[0]&255);}
 unsigned ready_mask()const{return unsigned((stage_state.limb[0]>>8)&127);}
 bool stage_active()const{return stage_state.bit(15);}
 unsigned eligible_mask()const{auto n=stage_count();return n>=130?127:n>=44?31:n>=16?7:0;}
 bool stage_drain_due()const{return policy==RoundPolicy::STAGED&&stage_active()&&ready_mask()!=eligible_mask();}
 void set_stage(unsigned count,unsigned mask,bool active){stage_state={};stage_state.limb[0]=count|(mask<<8)|(unsigned(active)<<15);stage_check=stage_codec.encode(stage_state);}
 bool validate_stage(){auto d=stage_codec.decode(stage_state,stage_check);if(d.due){++stats.detected;++stats.due;reset_refill();return false;}if(d.corrected){stage_state=d.payload;stage_check=d.check;++stats.detected;++stats.corrected;}
  if(stage_count()>130||(stage_active()&&ready_mask()>eligible_mask())){++stats.detected;reset_refill();return false;}return true;}
 void stage_commit(){if(!validate_stage()||!stage_active())return;auto n=std::min(130u,stage_count()+1);set_stage(n,ready_mask(),true);refill=130-n;++stats.refill_updates;apply_admission();}
 void apply_admission(){if(policy==RoundPolicy::STAGED)core.admitted(stage_active()?ready_mask():127);else core.tagged_enabled(!fallback());}
 void force_refill(){reset_refill();apply_admission();}
 uint32_t shadow_gen(){Word g;g.limb[0]=shadow_generation;auto d=generation_codec.decode(g,generation_check);if(d.due){++stats.detected;++stats.due;shadow_generation=0;generation_check=0;reset_refill();return shadow_generation;}if(d.corrected){shadow_generation=d.payload.limb[0];generation_check=d.check;++stats.corrected;}return shadow_generation;}
'''
s=s.replace(anchor,methods+anchor)
# Logical state getters/corruption.
s=s.replace('  if(n=="recovery_active")return recovery_active;', '  if(n=="staged_control")return stage_state.bit(s.bit);\n  if(n=="staged_control_check")return (stage_check>>s.bit)&1;\n  if(n=="shadow_generation")return (shadow_generation>>s.bit)&1;\n  if(n=="shadow_generation_check")return (generation_check>>s.bit)&1;\n  if(n=="recovery_active")return recovery_active;')
s=s.replace('   else if(n=="refill_remaining")', '   else if(n=="staged_control")stage_state.flip(s.bit);\n   else if(n=="staged_control_check")stage_check^=uint16_t(1)<<s.bit;\n   else if(n=="shadow_generation")shadow_generation^=uint32_t(1)<<s.bit;\n   else if(n=="shadow_generation_check")generation_check^=uint16_t(1)<<s.bit;\n   else if(n=="refill_remaining")')
p.write_text(s)
p=dst/'role_spec_history.hpp';s=p.read_text();s=s.replace('        if(protection.policy==RoundPolicy::H1&&protection.phase>=2)', '        if(protection.policy==RoundPolicy::STAGED){protection.validate_stage();if(protection.stage_drain_due()){if(!cpu_history_empty)return true;protection.complete_cpu_drain();++drains_completed;return false;}}\n        if(protection.policy==RoundPolicy::H1&&protection.phase>=2)');p.write_text(s)
p=dst/'role_adapter.hpp';s=p.read_text().replace('protection.commit_source(b.pc,b.taken);delete bi;', 'protection.commit_source(b.pc,b.taken);if(protection.policy==RoundPolicy::STAGED&&protection.stage_drain_due())protection.complete_cpu_drain();delete bi;');p.write_text(s)
p=dst/'scheduled.cpp';s=p.read_text().replace('std::string(argv[9])=="REV"?', 'std::string(argv[9])=="STAGED"?RoundPolicy::STAGED:std::string(argv[9])=="REV"?');p.write_text(s)
print('Round B controller prototypes generated; not yet adopted or evaluated')
