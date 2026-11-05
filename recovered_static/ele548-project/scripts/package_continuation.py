"""Local review packet; no external upload and no PDK/license material."""
import json,zipfile
from continuation_common import *
audit=json.loads((OUT/'reports/G6_FINAL_AUDIT.json').read_text());assert audit['status'].startswith('PASS_G0_TO_G6')
packet=ROOT/'reports/BP_SEU_Continuation_G6_20261013.zip';paths=[]
for base in [ROOT/'src/continuation',ROOT/'gem5_continuation_ext',OUT/'configs',OUT/'inputs',OUT/'reports']:
 paths.extend(p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.tmp'] and not p.name.startswith('G6_PACKAGE'))
paths += [OUT/'literature/REVIEW_ADDENDUM.ko.md', OUT/'literature/LOCAL_PAPERS.json']
paths += list((ROOT/'data/curated').glob('*.json'))+[ROOT/'data/curated/charm_tableII.csv']
paths += [ROOT/'sources/protection_scope.lock.json', ROOT/'sources/manifest.json', ROOT/'reports/software.lock.json']
paths += [ROOT/'gem5/o3_continuation.py',ROOT/'setup/build_gem5_continuation.sh',ROOT/'docs/00_LATEST_DECISIONS.ko.md',ROOT/'reports/CONTINUATION_G6_REPORT.ko.md']
paths += list((ROOT/'scripts').glob('*continuation*.py'))+[ROOT/'scripts/continue_after_design.py',ROOT/'scripts/continue_extra.py',ROOT/'tests/test_continuation_statistics.py']
for item in json.loads((OUT/'configs/holdout_inputs.lock.json').read_text())['programs']:paths.append(ROOT/item['binary'])
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
assert not any(p.suffix in ['.lib','.lef','.gds','.lic','.db'] for p in paths)
with zipfile.ZipFile(packet,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(set(paths)):z.write(p,p.relative_to(ROOT))
 z.writestr('PROMOTION_PACKET/README.ko.md','G6 소프트웨어 후보 동결. 먼저 continuation/runtime/reports/G6_HARDWARE_CANDIDATE_SHORTLIST.ko.md와G6_HARDWARE_CONTRACT.json을 읽으세요. 원본gem5pin과historicalHW1trace/oldbaseline은사용자workspace에서 재사용합니다. 이패킷은PDK/license자료와gem5buildcache를포함하지않습니다. RawCPU/config/event/input/sourcehash및초기실패도포함합니다. ActualPPA와targetphysicalrate는없습니다.\n')
 z.writestr('PROMOTION_PACKET/MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
write(OUT/'PROMOTION_PACKET.json',dict(status='CREATED_LOCAL_REVIEW_ZIP',path=str(packet),sha256=sha(packet),bytes=packet.stat().st_size,files=len(manifest),hardware_authorized=False))
print(packet,packet.stat().st_size,sha(packet))
