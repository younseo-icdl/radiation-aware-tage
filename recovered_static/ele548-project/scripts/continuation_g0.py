import json,subprocess,os
from pathlib import Path
from continuation_common import *
files=[]
for directory in ['src','scripts','configs','gem5_ext','gem5_periodic_ext','gem5','setup']:
 files += [p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in ['continuation_g0.py','continuation_common.py']]
for name in ['SOFTWARE_FINAL_REVIEW.json','E1_SUMMARY.json','E2_SUMMARY.json','E3_CPU_MAIN.json','E3_CPU_LATENCY.json','PERIODIC_EXTENSION_AUDIT.json']:
 p=ROOT/'reports'/name
 if p.exists():files.append(p)
files+=list((ROOT/'sources').glob('*.json'))
snapshot=dict(status='READ_ONLY_EVIDENCE_SNAPSHOT',commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),tracked_status=subprocess.check_output(['git','status','--short','-uno'],cwd=ROOT,text=True),files={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(files))},active_research_processes=subprocess.check_output(['pgrep','-af','gem5.opt|periodic_scheduled|e1_campaign'],text=True) if False else 'No previous research jobs observed; unrelated EDA untouched')
write(OUT/'reports/G0_SNAPSHOT.json',snapshot)
a=json.loads((ROOT/'reports/PERIODIC_EXTENSION_AUDIT.json').read_text())
assert a['status']=='PASS_REVIEWED_OPTIONAL_PERIODIC_SOFTWARE_PILOT'
for p,h in a['evidence_hashes'].items():assert sha(ROOT/p)==h,p
for name in ['gem5_e3_source.lock.json','gem5_periodic_source.lock.json']:
 x=json.loads((ROOT/'sources'/name).read_text());assert x['pin']=='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
 for p,h in x.get('shared_code',x.get('source_hashes',{})).items():assert sha(ROOT/p)==h,p
for name in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:
 for tree in ['gem5-e3','gem5-periodic']:assert sha(ROOT/'third_party'/tree/'src/cpu/pred'/name)==sha(ROOT/'third_party/gem5/src/cpu/pred'/name)
checks=[]
for cmd,label in [([ROOT/'build/predictor_e0'],'predictor_e0'),([ROOT/'build/periodic_correctness'],'periodic_correctness'),([ROOT/'.venv/bin/python','-m','unittest','discover','-s','tests','-v'],'python_tests')]:
 r=timed(cmd,OUT/f'reports/G0_{label}.log',timeout=180);checks.append(r);assert r['exit_code']==0,label
write(OUT/'reports/G0_AUDIT.json',dict(status='PASS_EXISTING_CORRECTED_BASELINE_PRESERVED',snapshot_sha256=sha(OUT/'reports/G0_SNAPSHOT.json'),checks=checks,source_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',previous_periodic_complete=True,new_adapters_implemented_at_snapshot=False,license_checkout_claim=False))
decision('G0','New kit is a continuation, not a replacement.', ['G0_SNAPSHOT.json','G0_AUDIT.json'],'Old periodic/e3 locks and upstream TAGE bytes match; baseline tests PASS.','Bind causal owners to local real trace windows; implement diagnostic adapter.')
print('PASS G0 corrected baseline/current WIP preserved')
