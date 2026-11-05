#!/usr/bin/env python3
"""An independent source/build worktree; never replace the completed E3 producer."""
import json
import shutil
import subprocess
from pathlib import Path
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]
PIN='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
TARGET=ROOT/'third_party/gem5-periodic'

def main():
    old=json.loads((ROOT/'sources/gem5_e3_source.lock.json').read_text())
    assert old['pin']==PIN
    for rel,digest in old['shared_code'].items():assert sha(ROOT/rel)==digest
    for rel,digest in old['modified_files'].items():assert sha(ROOT/'third_party/gem5-e3'/rel)==digest
    if not TARGET.exists():
        subprocess.run(['git','-C',str(ROOT/'third_party/gem5'),'worktree','add','--detach',str(TARGET),PIN],check=True)
        subprocess.run(['git','-C',str(TARGET),'apply',str(ROOT/'reports/e3_integration/gem5_transport.patch')],check=True)
        for name in ['BPSEU.py','research_tage.hh','research_tage.cc']:
            shutil.copy2(ROOT/'gem5_ext'/name,TARGET/'src/cpu/pred'/name)
    assert subprocess.check_output(['git','-C',str(TARGET),'rev-parse','HEAD'],text=True).strip()==PIN
    path=TARGET/'src/cpu/pred/SConscript';s=path.read_text()
    addition="\nSimObject('BPPeriodic.py', sim_objects=['PeriodicTAGEBase', 'PeriodicTAGE'])\nSource('research_periodic_tage.cc')\n"
    if addition not in s:path.write_text(s+addition)
    for name in ['BPPeriodic.py','research_periodic_tage.hh','research_periodic_tage.cc']:
        shutil.copy2(ROOT/'gem5_periodic_ext'/name,TARGET/'src/cpu/pred'/name)
    for name in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:
        assert sha(TARGET/'src/cpu/pred'/name)==sha(ROOT/'third_party/gem5/src/cpu/pred'/name)
    locked=['src/protection/periodic_history.hpp','src/protection/periodic_spec_history.hpp','src/predictor/periodic_adapter.hpp','gem5/o3_periodic.py']
    locked+=['gem5_periodic_ext/'+n for n in ['BPPeriodic.py','research_periodic_tage.hh','research_periodic_tage.cc']]
    record={'status':'PREPARED_EXTENSION_SOURCE_CPU_GATE_PENDING','pin':PIN,'worktree':str(TARGET),'base_source_lock_sha256':sha(ROOT/'sources/gem5_e3_source.lock.json'),'scope_sha256':sha(ROOT/'sources/protection_scope.lock.json'),'base_sources_preserved':True,'source_hashes':{p:sha(ROOT/p) for p in locked},'modified_files':{rel:sha(TARGET/rel) for rel in old['modified_files']},'upstream_TAGE_unchanged':True,'RTL_PPA_measured':False}
    (ROOT/'sources/gem5_periodic_source.lock.json').write_text(json.dumps(record,indent=2)+'\n')
    print('PASS independent pinned periodic worktree; completed E3 source/binary preserved')
if __name__=='__main__':main()
