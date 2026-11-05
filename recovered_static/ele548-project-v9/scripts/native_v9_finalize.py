"""Private, allowlisted v9 evidence closure; no simulator or EDA execution."""
import argparse, datetime, hashlib, json, os, subprocess, zipfile
from pathlib import Path
from native_v9_common import ROOT, OLD, OUT, BINARY, CONFIG, load, ref, sha, write, verify_sources, used_seconds, disk_gib

RESULTS=ROOT/'rate_state_v9/results'
R2=ROOT/'rate_state_v9/r2/runtime'
R2_BINARY=ROOT/'third_party/gem5-native-v9r2/build/X86_PIPELINE/gem5.opt'

def running():
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if (p/'exe').resolve() in [BINARY.resolve(),R2_BINARY.resolve()]:found.append(int(p.name))
        except (OSError,RuntimeError):pass
    return found

def audit():
    dest=RESULTS/'FINAL_EVIDENCE_AUDIT.json';assert not dest.exists(),'IMMUTABLE_FINAL_AUDIT'
    assert not running(),'V9_CPU_STILL_ACTIVE'
    source=verify_sources();producer=load(OUT/'configs/PRODUCER.lock.json')
    assert sha(BINARY)==producer['binary_sha256'] and sha(CONFIG)==producer['config_sha256']
    preservation=load(OUT/'configs/PRESERVED_V8.lock.json')
    for name,digest in preservation['hashes'].items():assert sha(OLD/name)==digest,('OLD_EVIDENCE_CHANGED',name)
    references=load(OUT/'configs/EXPERIMENT_REFERENCES.lock.json')
    for name,digest in references['files'].items():assert sha(ROOT/name)==digest,('FROZEN_HELPER_CHANGED',name)
    import native_v9r2_gate
    native_v9r2_gate.verify()
    assert load(R2/'configs/PRODUCER.lock.json')['status'].startswith('PASS_BOUNDED_R2_CORRECTNESS13')
    r2built=load(R2/'configs/BUILT_PRODUCER.pending.json')
    assert sha(R2_BINARY)==r2built['binary']['sha256']
    phases=[('R1.'+n,OUT,n) for n in ['GATE_NORMAL','GATE_SBU','GATE_DUE','CLEAN','DEVELOPMENT','HOLDOUT_CLEAN','HOLDOUT_FAULT']]
    phases += [('R1.SOURCE_CONTINUATION',ROOT/'rate_state_v9/source_continuation/runtime','SOURCE_CONTINUATION')]
    phases += [('R2.'+n,R2,n) for n in ['GATE_NORMAL','PENDING_ACTIVE_SBU','OLD_FAILURE_REPLAY']]
    rows=[];bindings={};failed=[];raw_count=0
    for phase,base,name in phases:
        f=base/'reports'/(name+'.json');d=load(f)
        assert d['status'] in ['PASS','FAIL_RETAINED','STOPPED_RETAINED'],('NONTERMINAL_PHASE',phase)
        assert len(d['tasks'])<=d['planned'],('INVALID_PHASE_COUNT',phase)
        if d['status']!='STOPPED_RETAINED':assert len(d['tasks'])==d['planned'],('INCOMPLETE_PHASE',phase)
        for r in d['tasks']:
            if phase.startswith('R2.'):
                assert r['producer_binary_sha256']==r2built['binary']['sha256'] and r['config_sha256']==r2built['config']['sha256']
            else:
                assert r['producer_binary_sha256']==producer['binary_sha256'] and r['config_sha256']==producer['config_sha256']
            for name,digest in r.get('hashes',{}).items():
                assert sha(ROOT/r['output']/name)==digest,('RAW_CHANGED',r['label'],name);raw_count+=1
            if r['status']!='PASS':
                assert r.get('cycles') is None,'FAILED_CYCLES_IMPUTED';failed.append(r['label'])
            rows.append(r)
        bindings[phase]=dict(report=ref(f),actual=len(d['tasks']),planned=d['planned'],status=d['status'])
    markers=list((ROOT/'rate_state_v9').glob('**/reports/run_starts/*.json'))
    assert len(rows)==len(markers)==len({r['output'] for r in rows}),'ATTEMPT_ACCOUNTING'
    assert 3009+len(markers)<=3200,'GLOBAL_CPU_CAP'
    assert not list((ROOT/'rate_state_v9').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT_ACCOUNTING'
    rtl_root=ROOT/'rate_state_v9/rtl_track';rtl=load(rtl_root/'reports/RTL_EVIDENCE.lock.json')
    for name,digest in rtl['files'].items():assert sha(rtl_root/name)==digest,('RTL_CHANGED',name)
    for name in ['ANALYSIS.lock.json','CONFIRMATION_ANALYSIS.lock.json']:
        f=RESULTS/name;assert f.exists(),('MISSING_ANALYSIS',name);bindings[name]=ref(f)
    confirm=load(RESULTS/'confirmation/ANALYSIS.lock.json')
    for name,digest in confirm['artifacts_sha256'].items():assert sha(RESULTS/'confirmation'/name)==digest,('CONFIRMATION_AGGREGATE_CHANGED',name)
    for folder in ['source_complete','source_complete_v2']:
        evidence=load(RESULTS/folder/'ANALYSIS.lock.json')
        for name,digest in evidence['artifacts_sha256'].items():assert sha(RESULTS/folder/name)==digest,('AGGREGATE_CHANGED',folder,name)
    prepared=ROOT/'rate_state_v9/r2_evaluation/runtime/configs/PREPARED.lock.json'
    if prepared.exists():
        d=load(prepared)
        assert d['status']=='PREPARED_NO_GEM5_TRIALS_NEEDS_BUDGET_AMENDMENT'
        for key in ['proposal','inputs','producer']:
            assert sha(ROOT/d[key]['path'])==d[key]['sha256'],('PREPARED_REFERENCE_CHANGED',key)
        assert not list((prepared.parents[1]/'reports/run_starts').glob('*.json')),'UNAUTHORIZED_EVALUATION_ATTEMPTS'
        assert not (prepared.parent/'BUDGET_AMENDMENT.lock.json').exists(),'REVIEW_AUDIT_EXPECTS_PENDING_APPROVAL'
        bindings['R2_PREPARED_NOT_EXECUTED']=ref(prepared)
    launcher=R2/'reports/BUILD_LAUNCHER_STATUS.json'
    assert load(launcher)['observed_outer_session_exit_code']==143
    bindings['R2_BUILD_LAUNCHER_STATUS']=ref(launcher)
    seconds=used_seconds();gib=disk_gib()
    assert seconds<12*3600 and 65.39845555555556+seconds/3600<108,'RECORDED_COREH_CAP'
    assert gib<8 and gib+20.54370880126953<34,'DISK_CAP'
    import shutil
    free=shutil.disk_usage(ROOT).free/1024**3;assert free>=10,'MIN_FREE_DISK'
    d=dict(status='PASS_V9_EVIDENCE_INTEGRITY_NOT_HARDWARE_QUALIFICATION',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
      source_files=len(source['sources']),transport_files=len(source['transport']),original_preserved_files=len(preservation['hashes']),
      checked_cpu_raw_references=raw_count,checked_rtl_allowlist_files=len(rtl['files']),cpu_attempts=len(markers),failures=failed,
      old_cpu_attempts=3009,global_cpu_attempts=3009+len(markers),remaining_cpu=3200-3009-len(markers),
      recorded_new_core_hours=seconds/3600,recorded_global_core_hours=65.39845555555556+seconds/3600,
      unknown_resource_time='Initial untimed auxiliary help/RTL setup and this audit/package overhead are not fabricated as zero; recorded core-hours are not all-inclusive exact usage.',
      worktree_gib=gib,combined_namespaces_plus_worktree_gib=20.54370880126953+gib,free_gib=free,active_cpu_pids=[],
      producer=ref(OUT/'configs/PRODUCER.lock.json'),r2_producer=ref(R2/'configs/PRODUCER.lock.json'),r1_preservation=ref(R2/'configs/PRESERVED_R1.lock.json'),preservation=ref(OUT/'configs/PRESERVED_V8.lock.json'),phase_bindings=bindings,
      original_holdout_unstarted=32,continued_source=20,remaining_original_whole_not_started=12,old_failure_retained_distinct_from_new_replay=True,
      actual_gem5_pin=source['pin'],no_pdk_upload=True,hardware_candidates_qualified=0,
      limitation='Native normal stage-fit and protected recovery timing assumptions persist. Logical fault populations are not full hardware area inventories. No universal or all-domain winner follows from small owner cohorts.')
    write(dest,d);print(json.dumps({k:d[k] for k in ['status','cpu_attempts','global_cpu_attempts','remaining_cpu','recorded_new_core_hours','original_preserved_files']},ensure_ascii=False))

def package():
    assert (RESULTS/'FINAL_REPORT.ko.md').exists() and (RESULTS/'FINAL_EVIDENCE_AUDIT.json').exists()
    bundle=RESULTS/'BUNDLE.json';assert not bundle.exists(),'IMMUTABLE_BUNDLE'
    assert not running(),'V9_CPU_STILL_ACTIVE'
    names=set()
    def add(p):
        p=Path(p)
        assert p.is_file() and not p.is_symlink(),('NONREGULAR_PACKAGE_FILE',str(p))
        rel=p.relative_to(ROOT)
        assert not any(s in rel.parts for s in ['__pycache__','fv']),('CACHE_IN_PACKAGE',str(rel))
        if 'xcelium.d' in rel.parts:assert p.name=='xcelium_bin_paths.log',('COMPILED_XCELIUM_CACHE_IN_PACKAGE',str(rel))
        assert p.open('rb').read(4)!=b'\x7fELF',('ELF_IN_PACKAGE',str(rel))
        names.add(str(rel))
    source=load(OUT/'configs/source.lock.json')
    for name in source['sources']:add(ROOT/name)
    for name in source['transport']:add(ROOT/'third_party/gem5-native-v9/src'/name)
    source2=load(R2/'configs/source.lock.json')
    for name in source2['files']:add(ROOT/name)
    add(ROOT/source2['config']['path'])
    for name in source2['transport']:add(ROOT/'third_party/gem5-native-v9r2/src'/name)
    for folder in ['rate_state_v9/runtime','rate_state_v9/rate_track','rate_state_v9/r2/runtime','rate_state_v9/source_continuation/runtime','rate_state_v9/r2_evaluation/runtime']:
        for p in (ROOT/folder).rglob('*'):
            if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts:continue
            if p.suffix in ['.o','.pyc','.so','.a','.zip'] or p.open('rb').read(4)==b'\x7fELF':continue
            add(p)
    rtl_root=ROOT/'rate_state_v9/rtl_track'
    for name in load(rtl_root/'reports/RTL_EVIDENCE.lock.json')['files']:add(rtl_root/name)
    add(rtl_root/'reports/RTL_EVIDENCE.lock.json')
    for p in RESULTS.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.zip' and p.name not in ['BUNDLE_CONTENTS.sha256','BUNDLE.json']:add(p)
    for pattern in ['scripts/native_v9*.py','setup/*native_v9*','gem5/o3_native_v9.py','rate_state_v9/*.md']:
        for p in ROOT.glob(pattern):
            if p.is_file() and p.suffix!='.zip' and p.name not in ['BUNDLE_CONTENTS.sha256','BUNDLE.json']:add(p)
    for name in load(OUT/'configs/EXPERIMENT_REFERENCES.lock.json')['files']:add(ROOT/name)
    for name in ['docs/00_LATEST_DECISIONS.ko.md','AGENTS.md']:add(ROOT/name)
    content=''.join(sha(ROOT/name)+'  '+name+'\n' for name in sorted(names))
    content_path=RESULTS/'BUNDLE_CONTENTS.sha256';assert not content_path.exists();content_path.write_text(content);names.add(str(content_path.relative_to(ROOT)))
    archives=ROOT/'rate_state_v9/artifacts';archives.mkdir(exist_ok=True)
    path=archives/'BP_SEU_L0_NATIVE_V9_LOCAL_RESULTS.zip';assert not path.exists()
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(names):z.write(ROOT/name,name)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name in sorted(names):assert hashlib.sha256(z.read(name)).hexdigest()==sha(ROOT/name),('ARCHIVE_HASH',name)
    write(bundle,dict(status='PASS_PRIVATE_LOCAL_ALLOWLIST_ARCHIVE_CRC_AND_SHA256',archive=ref(path),bytes=path.stat().st_size,files=len(names),contents=ref(content_path),
      private=True,no_external_upload=True,no_pdk_or_library_contents=True,no_elf_or_compiled_technology_cache=True,
      exclusions='Original archive/worktree, official unmodified gem5 tree, ELF builds, technology/model/PDK/library contents, mapped/routed DB and compiler/EDA caches. Upstream pin and local source patches are preserved.',
      rtl_policy=ref(rtl_root/'reports/PRIVATE_PACKAGE_POLICY.json')))
    print('PASS',path,len(names),path.stat().st_size)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','package']);a=p.parse_args()
    audit() if a.action=='audit' else package()
