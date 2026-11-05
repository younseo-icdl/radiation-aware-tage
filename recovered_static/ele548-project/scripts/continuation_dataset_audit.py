import json,hashlib
from continuation_common import *
from audit_flying_laptop import audit
from parse_cern_clusters import parse
source=ROOT/'data/raw/flying_laptop/DetectedSEUTimeTags_with_TLE_Data.csv'
flying=audit(source,OUT/'reports/flying_reaudit')
assert flying['raw_rows']==2129 and flying['unique_complete_rows']==flying['unique_timestamps']==2055 and flying['exact_duplicate_extra_rows']==74
assert flying['source_sha256']=='94ca982785ec072d36a1c4bdab9c91d220ab6dd9a1ba252b148da91dbb347a46'
card=json.loads((ROOT/'data/curated/cern_footprint_model_card.json').read_text());rows=[]
for f in card['files']:
 p=ROOT/'data/raw/cern'/f['file'];assert sha(p)==f['raw_sha256'];data=p.read_bytes();parsed=parse(data.decode());rows.append(dict(file=f['file'],sha256=sha(p),md5=hashlib.md5(data).hexdigest(),whole_file_records=len(parsed),conditional_K_ge_2=sum(r['multiplicity_from_unique_coordinates']>=2 for r in parsed)))
write(OUT/'reports/G0_DATASET_AUDIT.json',dict(status='PASS_RAW_HASH_AND_WHOLE_FILE_REAUDIT',flying=flying,cern=rows,duplicate_rows_are_MCU=False,source_per_bit_target_rate_identifiable=False,frozen_cern_model_card_sha256=sha(ROOT/'data/curated/cern_footprint_model_card.json')))
print('PASS Flying2129/2055/74 and whole3CERN files/hash/MD5')
