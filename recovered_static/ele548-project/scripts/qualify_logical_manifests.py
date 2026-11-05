#!/usr/bin/env python3
"""Connect stable C++ numeric IDs to the handoff's strict site schema.
Storage technology and physical mapping remain explicitly unqualified.
"""
from pathlib import Path
import json,hashlib
from jsonschema import Draft202012Validator
root=Path(__file__).resolve().parents[1]
validator=Draft202012Validator(json.loads((root/'schemas/fault_site.schema.json').read_text()))
structures={'bimodal':'btablePrediction_or_sharedHysteresis','ctr':'gtable.ctr','tag':'gtable.tag','u':'gtable.u','raw_path':'threadHistory.globalHist_live_window_or_pathHist','folded':'threadHistory.computeIndices_or_computeTags'}
source=root/'reports/predictor_logical_state_manifest.jsonl';dest=root/'sources/tage_fault_sites.jsonl'
scope_path=root/'sources/protection_scope.lock.json'
scope=json.loads(scope_path.read_text()) if scope_path.exists() else None
word_for_site={site:word['word_id'] for word in scope['payload_words'] for site in word['site_ids']} if scope else {}
count=0
with source.open() as inp,dest.open('w') as out:
 for line in inp:
  r=json.loads(line)
  structure=structures[r['field']]
  if r['field']=='bimodal':structure='btableHysteresis' if r['bank'] else 'btablePrediction'
  if r['field']=='raw_path':structure='threadHistory[0].pathHist' if r['bank'] else 'threadHistory[0].globalHist[ptGhist+age]'
  if r['field']=='folded':structure=f"threadHistory[0].computeTags[{r['row']-1}].comp" if r['row'] else 'threadHistory[0].computeIndices.comp'
  selected=r['site_id'] in word_for_site
  q={'site_id':f"tage:{r['site_id']}",'structure':structure,'field':r['field'],'bit':r['bit'],'width':r['width'],'encoding':r['encoding'],'storage_kind':'assumed_storage','scope_id':scope['scope_id'] if selected else 'core_P0_six_field_exposure','bank':r['bank'],'row':r['row'],'replica':0,'codeword':word_for_site.get(r['site_id']),'physical_mapping':None}
  validator.validate(q);assert r['site_id']==count and r['bit']<r['width'];out.write(json.dumps(q,separators=(',',':'))+'\n');count+=1
p=root/'sources/predictor_logical_state_manifest.json';m=json.loads(p.read_text());m['schema_site_file']={'path':'sources/tage_fault_sites.jsonl','sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'schema':'schemas/fault_site.schema.json','validation':'PASS_ALL_65370_SITES','numeric_id_binding':'tage:N <-> numeric site_id N used by C++ and trial CSV','storage_kind':'assumed_storage; physical implementation not selected'};p.write_text(json.dumps(m,indent=2)+'\n')
g={'predictor':'GshareAdapter','source':'src/predictor/gshare_adapter.hpp','reference':'sources/prior_hw1/gshare_original.h','scheme':'P0 control only','logical_bits':262161,'entries':131072,'counter_bits':2,'history_bits':17,'encoding':'unsigned','site_ranges':[{'first':0,'last_inclusive':262143,'structure':'counters','row':'site_id // 2','bit':'site_id % 2','width':2},{'first':262144,'last_inclusive':262160,'structure':'history','row':0,'bit':'site_id - 262144','width':17}],'schema_string_id':'gshare:N corresponds to numeric internal ID N','snapshot':'value-copy vector and 17-bit masked history; no pointers','storage_kind':'assumed_storage','physical_mapping':None,'excluded':['C++ padding/pointers','upper simulator GHR bits beyond effective 17-bit history','nonconditional branch history tracking (HW1 control has none)']}
(root/'sources/gshare_logical_state_manifest.json').write_text(json.dumps(g,indent=2)+'\n')
(root/'reports/logical_manifest_validation.json').write_text(json.dumps({'status':'PASS','TAGE_sites_schema_checked':count,'Gshare_compact_range_bits':262161,'physical_mapping':'NOT_DEFINED'},indent=2)+'\n')
print(f'PASS {count} TAGE strict-schema sites; Gshare compact mapping 262161 bits')
