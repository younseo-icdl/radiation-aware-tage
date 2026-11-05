#!/usr/bin/env python3
"""Bounded CBP4 extraction: 10-byte little-endian records, actual archived inputs.
No change to homework; only private derived research windows, never public traces.
"""
import gzip,tarfile,struct,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[1];archive=root/'hw1/ele548_Fall26_HW1.tar.gz'
reports=[]
with tarfile.open(archive) as tar:
 for name in ['SHORT-INT-1','SHORT-FP-1']:
  member='Fall26_HW1/traces/'+name+'.cbp4.gz';data=tar.extractfile(member).read()
  dst=root/'workloads/derived'/f'{name}.branches';dst.parent.mkdir(parents=True,exist_ok=True)
  records=conditional=controls=0;lines=[]
  with gzip.GzipFile(fileobj=__import__('io').BytesIO(data)) as g:
   while conditional<30000:
    raw=g.read(10)
    if len(raw)!=10:raise ValueError('truncated/insufficient trace')
    pc,target,op,taken=struct.unpack('<IIBB',raw);records+=1
    if op>=8 or taken>1:raise ValueError('invalid CBP record')
    if op>=3:
     conditional+=op==6;controls+=1;lines.append(f'{pc} {target} {taken} {int(op==6)}\n')
  dst.write_text(''.join(lines))
  reports.append({'name':name,'archive_member':member,'compressed_sha256':hashlib.sha256(data).hexdigest(),'compressed_bytes':len(data),'record_start':0,'record_end_exclusive':records,'conditional_branches':conditional,'control_branches':controls,'window_file':str(dst.relative_to(root)),'window_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'policy':'first 20k conditional branches warmup, next 10k conditional branches observation; unconditional controls retained for TAGE history; real archived trace slice, not repeated','licensing':'user-provided course archive, private workspace only; redistribution not established'})
(root/'reports/workload_windows.json').write_text(json.dumps({'archive':str(archive.relative_to(root)),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'workloads':reports},indent=2)+'\n')
print(json.dumps(reports,indent=2))
