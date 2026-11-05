"""Immutable B4 handoff. Closed raw only; every archived byte is hashed."""
import sys, pathlib, json, zipfile, hashlib, argparse, re, io
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b4'

def package(label):
    assert re.fullmatch('[A-Za-z0-9_]+', label)
    out = ROOT / 'runtime/artifacts'
    out.mkdir(exist_ok=True)
    dest = out / ('BP_SEU_Finite_Protection_B4_' + label + '.zip')
    assert not dest.exists()
    r.snapshot()
    paths, raw, omitted = {}, [], []
    def add(path, name=None):
        path = pathlib.Path(path)
        if path.is_file() and '__pycache__' not in path.parts:
            paths[name or str(path.relative_to(ROOT))] = path
    def tree(path):
        for p in pathlib.Path(path).rglob('*'):
            add(p)
    for name in ('docs', 'src', 'tests', 'tools', 'gem5_overlay', 'producer_source', 'sources', 'reports', 'continuation_b3', 'continuation_b4'):
        tree(ROOT / name)
    for name in ('START_HERE.ko.md', 'CODEX_PROMPT.ko.txt'):
        add(ROOT / name)
    add(ROOT.parent / 'AGENTS.md', 'AGENTS.md')
    for name in ('frozen', 'producers', 'configs', 'initialization_A1', 'initialization_B1', 'initialization_B2', 'initialization_B3', 'initialization_B4', 'inputs', 'run_starts'):
        tree(ROOT / 'runtime' / name)
    for namespace in (ROOT / 'runtime/continuation_b3', K):
        for name in ('reports', 'runtime/configs'):
            tree(namespace / name)
    for parent in (ROOT / 'runtime/cpu_trials', ROOT / 'runtime/continuation_b3/runtime/cpu_trials', K / 'runtime/cpu_trials'):
        if not parent.exists():
            continue
        for d in sorted(parent.iterdir()):
            if not d.is_dir():
                continue
            record = d / 'EXECUTION.json'
            if not record.exists():
                omitted.append(str(d))
                continue
            row = r.load(record)
            for name, digest in row.get('hashes', {}).items():
                assert r.sha(d / name) == digest, ('RAW_CHANGED', str(d / name))
            tree(d)
            raw.append({'label': d.name, 'status': row['status'], 'execution': r.ref(record)})
    # Diagnostic/build logs are closed, separately timed tasks, not new CPU trials.
    for p in (ROOT / 'runtime').glob('*/*'):
        if p.is_file() and p.name in ('stdout', 'stderr', 'job.time', 'EXECUTION.json'):
            add(p)
    for p in (ROOT / 'runtime').glob('gem5_build_*/*.d'):
        add(p)
    add(ROOT / 'runtime/gem5_build_B4_C1/gem5.protection_v18.opt')
    blobs = {name: path.read_bytes() for name, path in sorted(paths.items())}
    inventory = {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in blobs.items()}
    header = {'status': 'ACTUAL_B4_EVIDENCE_SNAPSHOT_NOT_NEW_FABRICATED_RESULTS',
              'label': label, 'closed_cpu_raw': len(raw), 'raw': raw, 'active_raw_excluded': omitted,
              'B4_producer': r.ref(ROOT / 'reports/PRODUCER_B4.lock.json'),
              'B4_gate': r.ref(ROOT / 'reports/B4_CORRECTNESS_ACCEPTANCE.json'),
              'B2_failure_not_hidden': r.ref(ROOT / 'reports/B3_REPEATED_FAULT_GATE_FAILURE.json'),
              'matrix_complete': (K / 'reports/FINITE_MATRIX_COMPLETED.json').exists(),
              'resources_at_snapshot': r.snapshot(),
              'scope': 'Local research C++/gem5 evidence only. No PDK, library, license, or proprietary benchmark distribution. Referenced external toolchain/public dependencies remain original-host SHA locks; this is not an installed portable environment.'}
    # Compress to memory first so disk admission uses measured archive bytes,
    # rather than a fixed reserve that can reject a fitting handoff.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('HANDOFF_STATUS.json', json.dumps(header, indent=2) + '\n')
        z.writestr('ARCHIVE_SHA256.json', json.dumps(inventory, indent=2) + '\n')
        for name, data in blobs.items():
            z.writestr(name, data)
    payload = buffer.getvalue()
    try:
        r.snapshot(extra_MiB=len(payload) / (1024 * 1024) + 1)
    except AssertionError as exc:
        r.put(K / 'reports' / ('ARCHIVE_ADMISSION_BLOCKED_' + label + '.json'), {
            'status': 'ACTUAL_ZIP_BYTES_REQUIRE_BUDGET_REVIEW_NO_DISK_BYPASS',
            'compressed_bytes_measured_in_memory': len(payload), 'error': repr(exc),
            'CPU_trials_started': 0, 'archive_written': False})
        raise
    with dest.open('xb') as stream:
        stream.write(payload)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for name, item in inventory.items():
            assert hashlib.sha256(z.read(name)).hexdigest() == item['sha256'], ('ZIP_MEMBER_SHA', name)
    report = {'status': 'PASS_ZIP_CRC_AND_EVERY_MEMBER_SHA256', 'archive': r.ref(dest),
              'archive_bytes': dest.stat().st_size, 'members': len(blobs) + 2,
              'closed_cpu_raw': len(raw), 'excluded_active_raw': len(omitted),
              'resources': r.snapshot()}
    r.put(K / 'reports' / ('PACKAGE_' + label + '.json'), report)
    print(json.dumps(report), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    package(parser.parse_args().label)
