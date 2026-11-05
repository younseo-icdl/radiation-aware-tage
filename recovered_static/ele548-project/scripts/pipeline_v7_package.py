"""Private v6 overlay with actual evidence; never build or run a simulator."""
from pathlib import Path
import datetime
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'rate_state_v5_pipeline_v7/runtime'
RESULTS = ROOT / 'rate_state_v5_pipeline_v7/results'
DEST = ROOT / 'reports/BP_SEU_Pipeline_v6_Completed_20261015.zip'


def require(condition, message):
    if not condition:
        raise RuntimeError('PIPELINE_PACKAGE: ' + str(message))


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def allowed(path):
    if not path.is_file() or path.suffix in ('.o', '.opt', '.a', '.so', '.pyc', '.zip'):
        return False
    if '__pycache__' in path.parts:
        return False
    # Standalone test executables and build objects can have no suffix.
    with path.open('rb') as stream:
        return stream.read(4) != b'\x7fELF'


def main():
    audit_path, software_path = RESULTS / 'EXECUTION_AUDIT.json', RESULTS / 'software.lock.json'
    audit = json.loads(audit_path.read_text())
    software = json.loads(software_path.read_text())
    require(audit.get('status') == 'PASS_PIPELINE_V6_EVIDENCE_INTEGRITY_NOT_HARDWARE_SAFETY' and
            audit.get('fully_qualified_hardware_candidates') == 0, 'FINAL_AUDIT_NOT_PASS_OR_METADATA_QUALIFIED')
    require(software.get('execution_audit_sha256') == sha(audit_path), 'SOFTWARE_AUDIT_BINDING_CHANGED')
    analysis_path = RESULTS / 'ANALYSIS.lock.json'
    require(audit['analysis_lock_sha256'] == sha(analysis_path), 'FINAL_ANALYSIS_CHANGED')
    analysis = json.loads(analysis_path.read_text())
    require(analysis.get('fully_qualified_hardware_candidates') == 0, 'UNSUPPORTED_HARDWARE_PROMOTION')
    for name, digest in analysis['outputs'].items():
        require(sha(RESULTS / name) == digest, ('ANALYSIS_OUTPUT_CHANGED', name))
    for phase in audit['phase_provenance']:
        for kind in ('report', 'task_lock'):
            ref = phase[kind]
            require(sha(ROOT / ref['path']) == ref['sha256'], ('TERMINAL_PHASE_CHANGED', phase['phase'], kind))
    require(not DEST.exists(), 'ARCHIVE_ALREADY_EXISTS')
    bundle_path, manifest_path = RESULTS / 'BUNDLE.json', RESULTS / 'BUNDLE_CONTENTS.sha256'
    require(not bundle_path.exists() and not manifest_path.exists(), 'BUNDLE_OUTPUT_ALREADY_EXISTS')
    paths = set()

    def add(path):
        require(path.is_file(), ('MISSING_REQUIRED_FILE', str(path)))
        require(path.resolve().is_relative_to(ROOT.resolve()), ('OUTSIDE_WORKSPACE', str(path)))
        require(allowed(path), ('EXCLUDED_BINARY_OR_ARCHIVE', str(path)))
        paths.add(path)

    def tree(folder, predicate=lambda path: True):
        require(folder.is_dir(), ('MISSING_REQUIRED_DIRECTORY', str(folder)))
        for path in folder.rglob('*'):
            if allowed(path) and predicate(path):
                add(path)

    tree(RESULTS, lambda path: path.name not in ('BUNDLE.json', 'BUNDLE_CONTENTS.sha256') and path.suffix != '.tmp')
    for path in (ROOT / 'rate_state_v5_pipeline_v7').glob('*'):
        if path.is_file() and path.suffix in ('.md', '.txt', '.json'):
            add(path)
    tree(ROOT / 'src/rate_pipeline_v7')
    tree(ROOT / 'gem5_rate_pipeline_v7_ext')
    add(ROOT / 'diagnostics/pipeline_v7_epoch_wrap_repro.cpp')
    tree(OUT / 'diagnostics')
    for path in (ROOT / 'scripts').glob('pipeline_v7_*.py'):
        add(path)
    for name in ('gem5/o3_pipeline_v7.py', 'setup/build_pipeline_v7.sh', 'AGENTS.md',
                 'docs/00_LATEST_DECISIONS.ko.md', 'scripts/v5_common.py', 'scripts/v3_common.py',
                 'scripts/v3_cpu_common.py', 'scripts/rng_namespace.py', 'scripts/run_o3_public_baseline.py',
                 'sources/protection_scope.lock.json', 'sources/public_workload_sources.lock.json',
                 'reports/predictor_logical_state_manifest.jsonl'):
        add(ROOT / name)
    # An overlay uses the existing locked workspace. Include its precise lock
    # references, not old raw campaigns, full gem5 trees or large archives.
    for name in ('rate_state_v5/runtime_r5/configs/PRODUCER.lock.json',
                 'rate_state_v5/runtime_r5/configs/source.lock.json',
                 'rate_state_v5/results/EXECUTION_AUDIT.json', 'rate_state_v5/results/software.lock.json',
                 'rate_state_v5/runtime_r5/reports/METADATA.json',
                 'rate_state_v5/runtime_r5/reports/METADATA_DECISION.json'):
        add(ROOT / name)
    for sub in ('configs', 'sources', 'inputs'):
        tree(OUT / sub)
    # Require all six actual transport snapshots rather than silently relying
    # on the unarchived new worktree or a diff against an unspecified baseline.
    for name in ('cpu/pred/conditional.hh', 'cpu/pred/bpred_unit.hh', 'cpu/pred/bpred_unit.cc',
                 'cpu/o3/bac.hh', 'cpu/o3/fetch.hh', 'cpu/o3/fetch.cc'):
        add(OUT / 'sources/TRANSPORT' / name)
    raw_names = {'gem5.log', 'gem5.log.time', 'schedule.ticks', 'seu.json', 'logical_manifest.json',
                 'program.stdout', 'program.stderr', 'events.csv', 'stats.txt', 'config.ini', 'config.json',
                 'citations.bib', 'pipeline.csv', 'events.csv.phases.csv', 'events.csv.repairs.csv',
                 'events.csv.rebuild.csv', 'events.csv.resource.csv'}
    tree(OUT / 'reports', lambda path: path.name in raw_names or path.suffix in ('.json', '.log', '.time', '.plan'))
    for path in OUT.glob('*'):
        if path.is_file() and path.suffix in ('.md', '.json', '.jsonl', '.log', '.time'):
            add(path)
    manifest = {str(path.relative_to(ROOT)): sha(path) for path in sorted(paths)}
    manifest_path.write_text(''.join(f'{digest}  {name}\n' for name, digest in manifest.items()))
    paths.add(manifest_path)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(DEST, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(paths):
            archive.write(path, str(path.relative_to(ROOT)))
    with zipfile.ZipFile(DEST) as archive:
        require(archive.testzip() is None, 'ZIP_CRC_FAILURE')
        require(len(archive.namelist()) == len(paths) == len(set(archive.namelist())), 'ZIP_DUPLICATE_OR_MISSING_MEMBER')
        for name, digest in manifest.items():
            check = hashlib.sha256()
            with archive.open(name) as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    check.update(chunk)
            require(check.hexdigest() == digest, ('ARCHIVED_HASH_MISMATCH', name))
        require(archive.read(str(manifest_path.relative_to(ROOT))) == manifest_path.read_bytes(), 'ARCHIVED_CONTENTS_MANIFEST_CHANGED')
    bundle = {'status': 'PASS_ZIP_CRC_AND_ALL_FILE_SHA256',
              'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'path': str(DEST.relative_to(ROOT)), 'sha256': sha(DEST), 'bytes': DEST.stat().st_size,
              'files': len(paths), 'content_manifest_sha256': sha(manifest_path),
              'execution_audit_sha256': sha(audit_path), 'fully_qualified_hardware_candidates': 0,
              'excluded': 'Build ELF/objects/full gem5 worktrees/PDK and old raw archives are excluded. Verbose cost/read and committed-audit CSVs remain local with raw-success hashes. BUNDLE.json is an external sidecar to avoid a self-hash cycle.',
              'reproduction': 'Private overlay for existing locked workspace. Actual source/input/producer/transport locks, six transport snapshots, generated standalone source and raw new CPU evidence are included. Pre-existing dependencies and build executables are local references, not fabricated new results.',
              'public_upload_or_push': False}
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + '\n')
    print('PASS private pipeline overlay CRC and file hashes:', DEST.name,
          len(paths), 'files;', round(DEST.stat().st_size / 1024 ** 2, 2), 'MiB')


if __name__ == '__main__':
    main()
