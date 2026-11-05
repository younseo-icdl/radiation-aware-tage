"""Close the explicitly authorized R2 evaluation; no simulation or EDA launch."""
import argparse
import datetime
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
import native_v9_common as c
import native_v9r2_eval as e

ROOT=c.ROOT
BASE=ROOT/'rate_state_v9/r2_evaluation'
RESULTS=BASE/'results'

def put(path, value):
    assert not path.exists(), ('IMMUTABLE_R2_CLOSURE',str(path))
    c.write(path,value)

def active():
    pids=[]
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:
            if (proc/'exe').resolve()==e.BINARY.resolve():pids.append(int(proc.name))
        except (OSError,RuntimeError):pass
    return pids

def audit():
    assert not active(),'R2_CPU_STILL_RUNNING'
    e.authorization();e.verify_prepared();e.verify_producer()
    old=c.verify_sources()
    preserved=c.load(c.OUT/'configs/PRESERVED_V8.lock.json')
    for name,digest in preserved['hashes'].items():
        assert c.sha(c.OLD/name)==digest,('ORIGINAL_CHANGED',name)
    old_archive=c.load(ROOT/'rate_state_v9/results/BUNDLE.json')
    assert c.sha(ROOT/old_archive['archive']['path'])==old_archive['archive']['sha256'],'BASE_ARCHIVE_CHANGED'
    # New permission/live navigation may change; all prior source/raw/EDA evidence stays exact.
    mutable_documents={'docs/00_LATEST_DECISIONS.ko.md','rate_state_v9/RESUME.ko.md',
                       'rate_state_v9/USER_ACTIONS_REQUIRED.md','rate_state_v9/START_HERE.ko.md'}
    prior_files=0
    for line in (ROOT/'rate_state_v9/results/BUNDLE_CONTENTS.sha256').read_text().splitlines():
        digest,name=line.split('  ',1)
        if name in mutable_documents:continue
        assert c.sha(ROOT/name)==digest,('PRIOR_V9_EVIDENCE_CHANGED',name)
        prior_files+=1
    bindings={};attempts=[];raw_refs=0;failures=[]
    for phase in ['EVAL_CLEAN','EVAL_FAULT']:
        path=e.OUT/'reports'/(phase+'.json');report=c.load(path)
        assert report['status'] in ['PASS','STOPPED_RETAINED'],'NONTERMINAL_PHASE'
        assert report['planned']==e.COUNTS[phase] and len(report['tasks'])==report['actual_runs']
        assert report['actual_runs']+report['not_started']==report['planned']
        if report['status']=='PASS':assert report['actual_runs']==report['planned']
        lock=c.load(e.OUT/'configs'/(phase+'.lock.json'))
        assert lock['authorization']==c.ref(e.OUT/'configs/BUDGET_AMENDMENT.lock.json')
        assert lock['proposal']==c.ref(e.OUT/'configs/PROPOSAL.lock.json')
        bindings[phase]=c.ref(path)
        for row in report['tasks']:
            assert row['producer_binary_sha256']==c.sha(e.BINARY) and row['config_sha256']==c.sha(e.CONFIG)
            for name,digest in row.get('hashes',{}).items():
                assert c.sha(ROOT/row['output']/name)==digest,('RAW_CHANGED',row['label'],name)
                raw_refs+=1
            if row['status']!='PASS':
                assert row.get('cycles') is None,'FAILED_CYCLES_IMPUTED'
                failures.append(dict(label=row['label'],status=row['status'],failure=row.get('failure')))
            attempts.append(row)
    own=e.own_starts();all_starts=e.all_starts()
    assert len(attempts)==len(own)==len({r['output'] for r in attempts}),'ATTEMPT_ACCOUNTING'
    assert len(own)<=162 and 3009+len(all_starts)<=3361,'CPU_CAP'
    assert len(all_starts)-len(own)==190,'HISTORICAL_ATTEMPTS_CHANGED'
    assert not list((ROOT/'rate_state_v9').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT'
    analysis=c.load(RESULTS/'ANALYSIS.lock.json')
    for name,digest in analysis['artifacts_sha256'].items():
        assert c.sha(RESULTS/name)==digest,('ANALYSIS_ARTIFACT_CHANGED',name)
    for name in ['INDEPENDENT_AUDIT','RATE_EVENT_AUDIT']:
        path=BASE/'reports'/(name+('.ko.json' if name=='INDEPENDENT_AUDIT' else '.json'))
        assert c.load(path)['status'].startswith('PASS'),('INDEPENDENT_AUDIT_NOT_PASS',name)
        bindings[name]=c.ref(path)
    seconds=c.used_seconds();gib=c.disk_gib();free=shutil.disk_usage(ROOT).free/2**30
    assert seconds<12*3600 and 65.39845555555556+seconds/3600<108,'CORE_HOUR_CAP'
    assert gib<8 and gib+20.54370880126953<34 and free>=10,'DISK_CAP'
    put(RESULTS/'FINAL_EVIDENCE_AUDIT.json',dict(
        status='PASS_R2_EVALUATION_EVIDENCE_INTEGRITY_NOT_HARDWARE_QUALIFICATION',
        observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        original_preserved_files=len(preserved['hashes']),r1_sources=len(old['sources']),
        prior_v9_preserved_artifacts=prior_files,approved_updated_navigation_documents=sorted(mutable_documents),
        checked_raw_references=raw_refs,evaluation_actual_cpu=len(attempts),evaluation_planned_cpu=162,
        evaluation_failures=failures,historical_cpu_before=3199,global_actual_cpu=3009+len(all_starts),
        global_cap=3361,remaining_global_cpu=3361-3009-len(all_starts),
        retained_r1_execution_failures=1,r2_known_failure_replay_not_independent=True,
        recorded_new_v9_core_hours=seconds/3600,recorded_global_core_hours=65.39845555555556+seconds/3600,
        unknown_resource_time='Early untimed auxiliary EDA/setup and audit/package overhead remain unknown, not fabricated zero.',
        worktree_gib=gib,combined_gib=20.54370880126953+gib,free_gib=free,
        authorization=c.ref(e.OUT/'configs/BUDGET_AMENDMENT.lock.json'),
        proposal=c.ref(e.OUT/'configs/PROPOSAL.lock.json'),producer=c.ref(e.g2.OUT/'configs/PRODUCER.lock.json'),
        analysis=c.ref(RESULTS/'ANALYSIS.lock.json'),phase_and_audit_bindings=bindings,
        old_archive=c.ref(ROOT/old_archive['archive']['path']),active_cpu_pids=[],
        physical_fullstage='UNKNOWN',hardware_candidates_qualified=0,
        limitations='All-six C0/nativeL0/II0 endpoint; normal codec stage-fit assumed, not measured CPU or complete hardware safety. n2/cell exploratory paired inference. No new source-lifetime calibration.'))
    print('PASS_AUDIT',len(attempts),'global',3009+len(all_starts),'recorded_v9_coreh',seconds/3600,flush=True)

def package(revision=1):
    assert not active(),'R2_CPU_STILL_RUNNING'
    assert (RESULTS/'FINAL_REPORT.ko.md').exists() and (RESULTS/'FINAL_EVIDENCE_AUDIT.json').exists()
    suffix='' if revision==1 else '_V2'
    bundle_path=RESULTS/('BUNDLE'+suffix+'.json')
    assert not bundle_path.exists(),'IMMUTABLE_R2_PACKAGE'
    names=set()
    for path in BASE.rglob('*'):
        if not path.is_file() or path.is_symlink() or '__pycache__' in path.parts or 'artifacts' in path.parts:continue
        if path.name.startswith('BUNDLE') and path.suffix in ['.json','.sha256']:continue
        assert path.suffix.lower() not in ['.lib','.lef','.tch','.qrc','.db','.so','.o','.a'],('TECH_CACHE_NOT_ALLOWED',str(path))
        assert path.open('rb').read(4)!=b'\x7fELF',('ELF_NOT_ALLOWED',str(path))
        names.add(str(path.relative_to(ROOT)))
    for path in [ROOT/'scripts/native_v9r2_eval_finalize.py',ROOT/'scripts/native_v9r2_eval_analyze.py',ROOT/'scripts/native_v9r2_eval_plot.py',ROOT/'scripts/native_v9r2_eval.py',ROOT/'scripts/native_v9r2_eval_inputs.py',ROOT/'docs/00_LATEST_DECISIONS.ko.md',ROOT/'rate_state_v9/results/BUNDLE.json',ROOT/'rate_state_v9/results/software_r2.lock.json',ROOT/'rate_state_v9/START_HERE.ko.md',ROOT/'rate_state_v9/RESUME.ko.md',ROOT/'rate_state_v9/USER_ACTIONS_REQUIRED.md']:
        names.add(str(path.relative_to(ROOT)))
    listing=''.join(c.sha(ROOT/name)+'  '+name+'\n' for name in sorted(names))
    path=RESULTS/('BUNDLE_CONTENTS'+suffix+'.sha256');assert not path.exists();path.write_text(listing);names.add(str(path.relative_to(ROOT)))
    folder=BASE/'artifacts';folder.mkdir(exist_ok=True)
    archive=folder/('BP_SEU_R2_INDEPENDENT_EVALUATION_RESULTS'+suffix+'.zip');assert not archive.exists()
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(names):z.write(ROOT/name,name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in sorted(names):assert hashlib.sha256(z.read(name)).hexdigest()==c.sha(ROOT/name),('ZIP_SHA_MISMATCH',name)
    put(bundle_path,dict(status='PASS_PRIVATE_R2_DELTA_ARCHIVE_CRC_SHA256',revision=revision,archive=c.ref(archive),bytes=archive.stat().st_size,files=len(names),contents=c.ref(path),base_archive_reference=c.ref(ROOT/'rate_state_v9/results/BUNDLE.json'),prior_packaging=c.ref(RESULTS/'BUNDLE.json') if revision==2 else None,private=True,no_external_upload=True,no_pdk_library_or_elf=True,scope='R2 independent evaluation delta, code helpers, raw/config/input/evidence and report; R1/R2 implementation/base evidence stays in the referenced preserved archive.'))
    print('PASS_PACKAGE',archive,len(names),archive.stat().st_size,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['audit','package']);parser.add_argument('--revision',type=int,choices=[1,2],default=1);args=parser.parse_args()
    audit() if args.action=='audit' else package(args.revision)
