#!/usr/bin/env python3
"""Verify an algebraic batching prerequisite; no CPU or service change."""
from pathlib import Path
import importlib.util,json,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def main():
 m.budget();plan=BASE/'reports/INVERSE_JUMP_PLAN.lock.json'
 m.put(plan,{'status':'FROZEN_BEFORE_UNIT_PROOF','sources':[m.ref(p) for p in [BASE/'src/inverse_jump.hpp',BASE/'tests/jump_gate.cpp',Path('/home/youns/workspace/ele548-project-v10/cost_v10/tests/history_state_pinned_reference.hpp'),Path(__file__)]],
 'unit_rng_seed':0x12a10,'source_buffer':1130,'undo_spans':'0..1000','all_fold_SBU_bits':200,'source_faults':'Static deterministic unit fixtures; not measured MCU distribution','controller_integrated':False,'CPU':0})
 common=['-O2','-g0','-std=c++17','-I'+str(BASE/'src'),'-I'+str(m.V9/'src'),'-I'+str(m.V9/'src/standalone'),'-I'+str(m.V9/'third_party/gem5-native-v9r2/src')]
 binary=BASE/'runtime/jump_gate';build=m.invoke('jump_build',[m.CC,*common,'-static-libstdc++','-static-libgcc',BASE/'tests/jump_gate.cpp',BASE/'runtime/tage_base.cc','-o',binary]);run=m.invoke('jump_run',[binary]);result=json.loads((BASE/'runtime/jump_run/stdout').read_text())
 assert result['status']=='PASS_EXACT_INVERSE_JUMP_LEMMA_NOT_STAGED_CONTROLLER'
 m.put(BASE/'reports/INVERSE_JUMP_GATE.json',{'status':result['status'],'result':result,'plan':m.ref(plan),'build':build,'run':run,'resources':m.budget()});print(json.dumps(result))
if __name__=='__main__':main()
