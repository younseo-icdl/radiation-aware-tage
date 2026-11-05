#!/usr/bin/env python3
"""Create a new private followup bundle only after terminal evidence acceptance.

No dispatcher imports, no simulator calls, no modification of the component ZIP.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
EXCLUDED = {'artifacts', '__pycache__', 'xcelium.d', '.git', 'cache'}
SUFFIXES = {'.py', '.md', '.txt', '.json', '.csv', '.ticks', '.time', '.log',
            '.stdout', '.stderr', '.dat', '.strace', '.ini', '.bib', '.sha256'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def disk_scope():
    def mib(path):
        text = subprocess.check_output(['du', '-sk', str(path)], text=True)
        return int(text.split()[0]) / 1024
    followup = mib(BASE)
    whole = mib(ROOT)
    old = mib(Path('/home/youns/workspace/ele548-project-v9'))
    scope = dict(followup_mib=followup,
                 completed_root_excluding_followup_mib=whole-followup,
                 v9_v10_worktrees_gib=(whole+old)/1024,
                 combined_gib=20.54370880126953+(whole+old)/1024,
                 free_gib=shutil.disk_usage(ROOT).free/(1024**3))
    assert followup < 384 and whole-followup < 512, scope
    assert scope['v9_v10_worktrees_gib'] < 8 and scope['combined_gib'] < 34, scope
    assert scope['free_gib'] >= 10, scope
    return scope


def allowed(path):
    if not path.is_file() or path.is_symlink():
        return False
    if any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
        return False
    if path.name.startswith(('PRIVATE_BUNDLE', 'POST_PACKAGE')):
        return False
    generated_plot = path.is_relative_to(BASE/'plots/final') and path.suffix in {'.png', '.pdf'}
    if path.suffix not in SUFFIXES and path.name != '.gitignore' and not generated_plot:
        return False
    data = path.read_bytes()
    assert not data.startswith(b'\x7fELF'), ('ELF_NOT_ALLOWED', str(path))
    if generated_plot:
        expected = b'\x89PNG\r\n\x1a\n' if path.suffix == '.png' else b'%PDF-'
        assert data.startswith(expected), ('GENERATED_PLOT_MAGIC_MISMATCH', str(path))
    else:
        data.decode('utf-8')
    return True


def main():
    gate_path = BASE / 'reports/FINAL_GATES.json'
    gate = json.loads(gate_path.read_text())
    assert gate['status'] == 'PASS_ACTUAL108_FINAL_EVIDENCE_NOT_HARDWARE_QUALIFICATION'
    assert gate['actual_new_gem5_trials'] == 108 and gate['actual_global_cpu'] == 3469
    for item in gate['bindings']:
        assert sha(Path(item['path'])) == item['sha256'], ('BINDING_CHANGED', item['path'])
    driver = json.loads((BASE / 'runtime/reports/BATCH_DRIVER.json').read_text())
    assert driver['status'] == 'COMPLETE_ALL_PRIMARY_PHASES_CHECK_ACCEPTANCE_AND_ANALYZE'
    assert all(phase['exit_code'] == 0 for phase in driver['phases'])
    roots = [BASE, ROOT / 'cost_v10/next_lifetime_prepare']
    files = [path for root in roots for path in root.rglob('*') if allowed(path)]
    for relative in ['docs/00_LATEST_DECISIONS.ko.md',
                     'cost_v10/configs/NEXT_NATIVE_LIFETIME_BATCH.json',
                     'cost_v10/reports/NEXT_NATIVE_LIFETIME_PLAN.ko.md',
                     'cost_v10/reports/NEXT_NATIVE_LIFETIME_READINESS.json']:
        path = ROOT / relative
        assert allowed(path)
        files.append(path)
    files = sorted(set(files))
    before = disk_scope()
    # Admission forecast, not a theorem about compression or allocation. Include
    # member names/headers, the contents list, metadata and a further 1 MiB.
    names = [str(path.relative_to(ROOT)) for path in files]
    header_bytes = sum(98+2*len(name.encode('utf-8')) for name in names)+22
    contents_bytes = sum(67+len(name.encode('utf-8')) for name in names)
    reserve_mib = (sum(path.stat().st_size for path in files)*1.01+
                   header_bytes+contents_bytes+65536+1048576)/(1024**2)
    assert before['followup_mib']+reserve_mib < 384, 'ARCHIVE_FORECAST_FOLLOWUP_CAP'
    assert before['v9_v10_worktrees_gib']+reserve_mib/1024 < 8, 'ARCHIVE_FORECAST_WORKTREE_CAP'
    assert before['combined_gib']+reserve_mib/1024 < 34, 'ARCHIVE_FORECAST_COMBINED_CAP'
    assert before['free_gib']-reserve_mib/1024 >= 10, 'ARCHIVE_FORECAST_FREE_CAP'
    manifest = {str(path.relative_to(ROOT)): sha(path) for path in files}
    reports = BASE / 'reports'
    contents = reports / 'PRIVATE_BUNDLE_CONTENTS.sha256'
    with contents.open('x') as stream:
        stream.write(''.join(digest + '  ' + name + '\n' for name, digest in manifest.items()))
    metadata = reports / 'PRIVATE_BUNDLE.json'
    record = dict(status='PRIVATE_LOCAL_NATIVE_LIFETIME_ACTUAL108_RESULTS',
                  actual_new_gem5_trials=108, actual_global_cpu=3469,
                  unused_cpu_reserve=6, payload_files=len(files),
                  archive_scope='LOCAL_DELTA_REFERENCING_EXISTING_R2_BINARY_AND_PROGRAM_ASSETS_NOT_SELF_CONTAINED',
                  contents_sha256=sha(contents), final_gate_sha256=sha(gate_path),
                  hardware_qualified_candidates=0,
                  excludes=['PDK/library/LEF/QRC/models/DB', 'ELF/binaries',
                            'full papers/figure extracts', 'prior component ZIP'],
                  resources_before_packaging=gate['resources'],
                  allocated_disk_before_packaging=before,
                  archive_size_forecast_mib=reserve_mib,
                  forecast_scope='HEURISTIC_COMPRESSION_ALLOCATION_FORECAST_ACTUAL_DISK_RECHECKED_AFTER_PACKAGING')
    with metadata.open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    artifacts = BASE / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    archive = artifacts / 'BP_SEU_V10_NATIVE_LIFETIME_RESULTS.zip'
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in [*files, contents, metadata]:
            bundle.write(path, str(path.relative_to(ROOT)))
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert len(bundle.namelist()) == len(files) + 2
        assert len(set(bundle.namelist())) == len(bundle.namelist())
        assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in bundle.namelist())
        for name, digest in manifest.items():
            assert hashlib.sha256(bundle.read(name)).hexdigest() == digest, name
        assert hashlib.sha256(bundle.read(str(contents.relative_to(ROOT)))).hexdigest() == record['contents_sha256']
        assert json.loads(bundle.read(str(metadata.relative_to(ROOT)))) == record
    result = dict(status='PASS_CRC_ALL_PAYLOAD_SHA256', archive=str(archive),
                  archive_sha256=sha(archive), archive_bytes=archive.stat().st_size,
                  payload_files=len(files), archive_entries=len(files) + 2,
                  allocated_disk_after_packaging=disk_scope())
    with (reports / 'POST_PACKAGE_VERIFICATION.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
