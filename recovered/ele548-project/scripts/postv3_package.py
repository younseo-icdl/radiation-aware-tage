"""Private same-workspace review archive, validated against audited evidence."""
import hashlib
import json
import subprocess
import zipfile
from postv3_common import *
audit=json.loads((OUT/'reports/FINAL_AUDIT.json').read_text());assert audit['status']=='PASS'
patch=subprocess.check_output(['git','-C',ROOT/'third_party/gem5-postv3','diff','--binary'])
(OUT/'reports/producer_transport.patch').write_bytes(patch)
paths=list(OUT.rglob('*'))+list((ROOT/'postv3/handoff').rglob('*'))
for name in ['src/postv3','gem5_postv3_ext','src/predictor','src/protection','src/standalone']:
    paths+=list((ROOT/name).rglob('*'))
paths+=list((ROOT/'scripts').glob('postv3_*.py'))
paths+=[ROOT/n for n in ['setup/build_postv3.sh','setup/run_postv3_cpp.sh','gem5/o3_postv3.py',
    'scripts/v3_common.py','scripts/v3_cpu_common.py','scripts/run_o3_public_baseline.py',
    'scripts/rng_namespace.py','scripts/continuation_statistics.py','sources/protection_scope.lock.json',
    'continuation_v3/runtime/RESOURCE_AND_HARDWARE_CONTRACT.md','continuation_v3/runtime/NOVELTY_MATRIX.md',
    'continuation_v3/runtime/configs/design_inputs.lock.json','build/checksum_freestanding',
    'continuation_v3/runtime/inputs/checksum/ignored.dat','continuation_v3/runtime/inputs/checksum/native.stdout']]
paths+=list((ROOT/'continuation_v3/runtime/inputs/design').glob('*'))
for item in json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']:
    p=ROOT/item['binary'];assert p.is_file() and sha(p)==item['binary_sha256'];paths.append(p)
paths=sorted({p for p in paths if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.tmp' and not p.name.startswith('PACKAGE_')})
entries={str(p.relative_to(ROOT)):sha(p) for p in paths}
archive=ROOT/'reports/BP_SEU_PostV3_Completed_20261014.zip';assert not archive.exists()
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in paths:z.write(p,p.relative_to(ROOT))
    z.writestr('REVIEW_BUNDLE_MANIFEST.json',json.dumps(dict(status='AUDITED_ACTUAL_PRIVATE_REVIEW',entries=entries,
        reconstruction='Overlay/review for the existing workspace; pinned gem5 source and producer binary are hash-locked local dependencies, not bundled900MB builds',
        distribution='Private local same-user review; no external upload or public redistribution'),indent=2))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,h in entries.items():assert hashlib.sha256(z.read(name)).hexdigest()==h
write(OUT/'reports/PACKAGE_AUDIT.json',dict(status='PASS',zip=str(archive.relative_to(ROOT)),sha256=sha(archive),
    bytes=archive.stat().st_size,files=len(entries),CRC_verified=True,all_embedded_hashes_verified=True))
print('Private review bundle',archive,'MiB',round(archive.stat().st_size/2**20,2),'files',len(entries))
