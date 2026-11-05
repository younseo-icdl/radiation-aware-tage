#!/usr/bin/env python3
"""Extract private, exact CBP instruction-indexed design/holdout control streams.

Binary format E1CBP001 + repeated <IIQBB: PC,target,original 1-based instruction
record index,taken,conditional. No C++ object representation is serialized.
Original archive is read only; no predictor metric is calculated for holdout.
"""
import gzip
import hashlib
import io
import json
import struct
import tarfile
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DTYPE = np.dtype([('pc', '<u4'), ('target', '<u4'), ('op', 'u1'), ('taken', 'u1')])
OUT_DTYPE = np.dtype([('pc', '<u4'), ('target', '<u4'), ('record', '<u8'), ('taken', 'u1'), ('conditional', 'u1')])


def main():
    config_path = ROOT / 'configs/e1.design.lock.json'
    config = json.loads(config_path.read_text())
    archive = ROOT / config['archive']
    with archive.open('rb') as f:
        archive_hash = hashlib.file_digest(f, 'sha256').hexdigest()
    assert archive_hash == json.loads((ROOT / 'reports/workload_windows.json').read_text())['archive_sha256']
    design_end = config['design_anchor_conditional_ordinal'] + config['injection_prefix_conditional_branches'] + config['post_event_horizon_conditional_branches']
    holdout_start = config['holdout_anchor_conditional_ordinal'] - config['holdout_warmup_conditional_branches']
    holdout_end = config['holdout_anchor_conditional_ordinal'] + config['injection_prefix_conditional_branches'] + config['post_event_horizon_conditional_branches']
    assert design_end < holdout_start
    outdir = ROOT / 'workloads/derived/e1'
    outdir.mkdir(parents=True, exist_ok=True)
    reports = []
    with tarfile.open(archive) as tar:
        for name in config['workloads']:
            member = f'Fall26_HW1/traces/{name}.cbp4.gz'
            compressed = tar.extractfile(member).read()
            files = {split: outdir / f'{name}.{split}.bin' for split in ['design', 'holdout']}
            handles = {split: path.open('wb') for split, path in files.items()}
            for f in handles.values(): f.write(b'E1CBP001')
            count = {split: 0 for split in files}
            conditionals = {split: 0 for split in files}
            ranges = {split: [None, None] for split in files}
            records = conditional = 0
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as g:
                    while conditional < holdout_end:
                        raw = g.read(100000 * 10)
                        if not raw or len(raw) % 10:
                            raise ValueError(f'insufficient/truncated real input: {name}, conditional={conditional}')
                        a = np.frombuffer(raw, DTYPE)
                        if np.any(a['op'] >= 8) or np.any(a['taken'] > 1): raise ValueError('invalid CBP record')
                        flags = a['op'] == 6
                        after = conditional + np.cumsum(flags, dtype=np.uint64)
                        before = after - flags
                        record_ids = np.arange(records + 1, records + 1 + len(a), dtype=np.uint64)
                        valid = a['op'] >= 3
                        for split, mask in [('design', valid & (before < design_end)),
                                            ('holdout', valid & (before >= holdout_start) & (before < holdout_end))]:
                            selected = a[mask]
                            if not len(selected): continue
                            out = np.empty(len(selected), OUT_DTYPE)
                            out['pc'] = selected['pc']; out['target'] = selected['target']
                            out['record'] = record_ids[mask]; out['taken'] = selected['taken']
                            out['conditional'] = selected['op'] == 6
                            handles[split].write(out.tobytes())
                            count[split] += len(selected)
                            conditionals[split] += int(np.count_nonzero(out['conditional']))
                            if ranges[split][0] is None: ranges[split][0] = int(out['record'][0])
                            ranges[split][1] = int(out['record'][-1])
                        if after[-1] >= holdout_end:
                            stop = int(np.searchsorted(after, holdout_end)) + 1
                            records += stop; conditional = holdout_end
                        else:
                            records += len(a); conditional = int(after[-1])
            finally:
                for f in handles.values(): f.close()
            assert conditionals['design'] == design_end
            assert conditionals['holdout'] == holdout_end - holdout_start
            report = {'workload': name, 'member': member, 'compressed_bytes': len(compressed),
                      'compressed_sha256': hashlib.sha256(compressed).hexdigest(),
                      'validated_original_prefix_records': records, 'validated_prefix_conditionals': conditional,
                      'split_files': {split: {'path': str(path.relative_to(ROOT)),
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                          'control_branches': count[split], 'conditional_branches': conditionals[split],
                          'first_last_inclusive_original_record': ranges[split],
                          'original_conditional_base': 0 if split == 'design' else holdout_start}
                          for split, path in files.items()}}
            reports.append(report)
            print(json.dumps({'workload': name, 'design_controls': count['design'], 'holdout_controls': count['holdout']}), flush=True)
    result = {'status': 'PASS_COMPLETE_DISJOINT_REAL_WINDOWS', 'archive': config['archive'],
              'archive_sha256': archive_hash, 'config_sha256': hashlib.sha256(config_path.read_bytes()).hexdigest(),
              'record_format': 'E1CBP001 + <IIQBB (18 bytes/record)', 'workloads': reports,
              'holdout_performance_evaluated': False,
              'source_boundary': 'actual course trace intervals; not repeated/synthetic; no original SPEC application binary included',
              'qualification': 'all records in extracted/needed original prefix validated; compressed member SHA256, not a full decompressed trace audit'}
    (ROOT / 'reports/E1_WORKLOAD_WINDOWS.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__': main()
