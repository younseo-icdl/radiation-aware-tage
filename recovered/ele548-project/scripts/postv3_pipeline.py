"""One bounded software round; no evaluation or new protocol without analysis."""
import os
import subprocess
import time
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'postv3/runtime'
def active_build():
    target=ROOT/'third_party/gem5-postv3'
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            if b'scons build/X86_STAGE0/gem5.opt' in (p/'cmdline').read_bytes().replace(b'\0',b' ') and (p/'cwd').resolve()==target:return True
        except (FileNotFoundError,PermissionError,ProcessLookupError):pass
    return False
resume='--resume-after-build3' in sys.argv
build_log=OUT/('reports/BUILD_3.log' if resume else 'reports/BUILD_2.log')
while True:
    log=build_log.read_text() if build_log.exists() else ''
    if not active_build() and ('error:' in log or 'scons: ***' in log):raise SystemExit('BUILD_ERROR_RETAINED; inspect before continuing')
    if not active_build() and 'scons: done building targets.' in log:break
    time.sleep(10)
steps=[('FINAL_OBSERVERS',['.venv/bin/python','scripts/postv3_finalize_observers.py']),
       ('BUILD3',['bash','setup/build_postv3.sh','3']),
       ('CPP_FINAL',['bash','setup/run_postv3_cpp.sh']),
       ('CPU_GATE',['.venv/bin/python','scripts/postv3_gate.py']),
       ('CLEAN',['.venv/bin/python','scripts/postv3_clean.py']),
       ('G0_ANALYSIS',['.venv/bin/python','scripts/postv3_analyze_clean.py']),
       ('G2',['.venv/bin/python','scripts/postv3_campaign.py'])]
if resume:steps=steps[2:]
for name,cmd in steps:
    path=OUT/'reports'/('PIPELINE_'+name+'.log');assert not path.exists()
    with path.open('w') as f:r=subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
    print('Completed',name,'exit',r.returncode,flush=True)
    if r.returncode:raise SystemExit('FAILED '+name+'; raw logs retained, later stages not dispatched')
print('G0→G2_COMPLETE; inspect paired results before deciding G3/G4',flush=True)
