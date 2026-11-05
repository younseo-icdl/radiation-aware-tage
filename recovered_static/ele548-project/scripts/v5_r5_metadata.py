"""Directed adverse encodings; failures are measured, never masked successes.

This audits the frozen prototype, not an additional candidate or optimization.
"""
from v5_r5_common import *
item=dict(name='checksum',binary='build/checksum_freestanding',input='continuation_v3/runtime/inputs/checksum/ignored.dat',binary_sha256=sha(ROOT/'build/checksum_freestanding'),input_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/ignored.dat'),native_stdout_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/native.stdout'))
ref=next(r for r in clean_rows() if r['id']=='BATCH_DIRECT')
manifest=json.loads((ROOT/ref['output']/'logical_manifest.json').read_text())
extra=manifest['additional_sites']
def site(structure,bit):return next(s['id'] for s in extra if s['structure']==structure and s['bit']==bit)
jobs=[]
for ident in ['BATCH_DIRECT','BATCH_STRAT16']:
 for name,tick,sites in [
  ('HEAD_HIGH_EARLY',400000,[site('journal_head',9)]),
  ('HEAD_HIGH_LATE',900000,[site('journal_head',10)]),
  ('PENDING_ACTIVE_IDLE',1,[site('pending_lookup_record',67)]),
  ('PENDING_READ_IDLE',1,[site('pending_lookup_record',66)]),
  ('FIFO_HEADER_DUE',1,[site('journal_queue',0),site('journal_queue',1)]),
  ('FIFO_PAYLOAD_PAIR',400000,[site('journal_queue',49),site('journal_queue',50)])]:
  jobs.append(make(item,ident,'METADATA',name,'R5_ADVERSE',str(tick)+' '+';'.join(map(str,sites))+'\n'))
rows=execute(jobs,'METADATA',workers=2,allowed_fault_failures=(
 'FAIL_PROTOCOL invalid bounded history pointer','Pending response PC/type changed without cancellation',
 'gem5 has encountered a segmentation fault','queue SECDED DUE','illegal queue control encoding',
 'Prediction consumed before ready'))
write(OUT/'reports/METADATA_DECISION.json',dict(status='AUDITED_NOT_HARDWARE_QUALIFIED',
 successes=sum(r['status']=='PASS' for r in rows),failures=sum(r['status']!='PASS' for r in rows),
 decision='No fully qualified hardware candidate from this frozen prototype. Source-only performance remains conditional on valid metadata. Adverse simulator failures are never counted as correct/masked or assigned cycle speedup.',
 boundary='Existing CPU BranchInfo and ownership are explicitly excluded in all variants. Pending flags declared owned by direct model are exposed here. Invalid encodings need a total hardware transition/fallback contract before HDL.',
 next='Complete independent rate/source/persistent/evaluation work; preserve raw failure rates and population scope. No extra parameter or implementation refinement in this round.'))
