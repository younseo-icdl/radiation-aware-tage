"""Private local review bundle with hashes and CRC, after actual report closure."""
import json,zipfile,subprocess
from v3_common import *
audit=json.loads((OUT/'reports/G7_AUDIT.json').read_text());assert audit['status']=='PASS'
paths=list(OUT.rglob('*'))
for folder in ['src/costaware_v3','src/costaware_v3_roundb','gem5_costaware_v3_ext','gem5_costaware_v3_b_ext','gem5_costaware_v3_c_ext','src/predictor','src/protection','src/standalone']:
 paths+=list((ROOT/folder).rglob('*'))
paths+=list((ROOT/'scripts').glob('v3_*.py'))+list((ROOT/'setup').glob('build_costaware_v3*.sh'))+list((ROOT/'gem5').glob('o3_costaware_v3*.py'))
paths += [ROOT/'scripts/rng_namespace.py',ROOT/'scripts/continuation_statistics.py',ROOT/'scripts/run_o3_public_baseline.py',ROOT/'sources/protection_scope.lock.json',ROOT/'reports/e3_integration/gem5_transport.patch',ROOT/'data/manifests/cern_files.json']
paths=[p for p in sorted(set(paths)) if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.tmp','.zip'] and not p.name.startswith('PACKAGE_')]
entries={str(p.relative_to(ROOT)):sha(p) for p in paths}
archive=ROOT/'reports/BP_SEU_CostAware_v3_Completed_20261013.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for p in paths:z.write(p,p.relative_to(ROOT))
 z.writestr('REVIEW_BUNDLE_MANIFEST.json',json.dumps(dict(status='ACTUAL_AUDITED_PRIVATE_REVIEW',entries=entries,source_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',distribution='private same-user workspace; no public paper redistribution'),indent=2))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for p,h in entries.items():
  import hashlib
  assert hashlib.sha256(z.read(p)).hexdigest()==h
write(OUT/'reports/PACKAGE_AUDIT.json',dict(status='PASS',zip=str(archive.relative_to(ROOT)),sha256=sha(archive),files=len(entries),bytes=archive.stat().st_size,CRC_verified=True,embedded_hashes_verified=True,producer_binaries='hash-locked local worktrees; not bundled large gem5 binaries',failed_C_binary='build/gem5_v3_C_FAILED_V1.opt preserved locally with hash'))
print('Private review bundle',archive,'files',len(entries),'MiB',round(archive.stat().st_size/2**20,2))
