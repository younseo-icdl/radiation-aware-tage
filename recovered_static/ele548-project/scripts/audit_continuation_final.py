import json,subprocess,csv,zipfile,hashlib
from continuation_common import *
required=['G0_AUDIT.json','G0_DATASET_AUDIT.json','G1_MAIN.json','G1_SHAM_VALIDATION.json','G3_CPP_SCREEN_FINAL.json','G3_MAINTENANCE_ABLATION.json','G4_CPU_GATE_V2.json','G4_CPU_DESIGN_V2.json','G5_SOURCE_ROBUSTNESS.json','G5_CPU_HOLDOUT_V2.json','G5_CPU_EXPOSURE_ROBUSTNESS.json','CPU_HOLDOUT_SUMMARY.json','G6_HARDWARE_CONTRACT.json','G6_PARETO.json','G6_ACTIVITY_VECTORS.json']
for name in required:
 x=json.loads((OUT/'reports'/name).read_text());assert x['status'].startswith('PASS') or x['status']=={
   'G6_HARDWARE_CONTRACT.json':'SOFTWARE_CANDIDATE_HANDOFF_NO_HARDWARE_IMPLEMENTATION',
   'G6_PARETO.json':'POINT_VECTOR_NOT_PHYSICAL_OPTIMUM',
   'G6_ACTIVITY_VECTORS.json':'ACTUAL_MODEL_COUNTS_COST_PROXY'}.get(name),name
snap=json.loads((OUT/'reports/G0_SNAPSHOT.json').read_text());mismatches=[]
for rel,h in snap['files'].items():
 if sha(ROOT/rel)!=h:mismatches.append(rel)
assert not mismatches,('old_evidence_changed',mismatches)
source=json.loads((OUT/'configs/gem5_source.lock.json').read_text())
for rel,h in source['sources'].items():assert sha(ROOT/rel)==h,rel
tree=ROOT/'third_party/gem5-continuation'
assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip()==source['pin']
upstream_hashes={}
for name in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:
 rel='src/cpu/pred/'+name
 expected=hashlib.sha256(subprocess.check_output(['git','-C',str(ROOT/'third_party/gem5'),'show',source['pin']+':'+rel])).hexdigest()
 assert sha(tree/rel)==expected,rel
 upstream_hashes[rel]=expected
for name in ['BPContinuation.py','research_continuation_tage.hh','research_continuation_tage.cc']:
 assert sha(tree/'src/cpu/pred'/name)==sha(ROOT/'gem5_continuation_ext'/name),name
for rel in ['src/cpu/o3/bac.hh','src/cpu/o3/fetch.cc','src/cpu/o3/fetch.hh','src/cpu/pred/bpred_unit.hh','src/cpu/pred/conditional.hh']:
 assert sha(tree/rel)==sha(ROOT/'third_party/gem5-e3'/rel),rel
binary=ROOT/'third_party/gem5-continuation/build/X86_STAGE0/gem5.opt'
for n in ['G4_CPU_GATE_V2.json','G4_CPU_DESIGN_V2.json','G5_CPU_HOLDOUT_V2.json','G5_CPU_EXPOSURE_ROBUSTNESS.json']:
 x=json.loads((OUT/'reports'/n).read_text());assert x['binary_sha256']==sha(binary),n
 for r in x.get('tasks',[]):
  assert r['status']=='PASS'
  for f,h in r.get('hashes',{}).items():assert sha(ROOT/r['output']/f)==h,(r['label'],f)
for name in ['G1_MAIN.json','G3_CPP_SCREEN_FINAL.json','G5_SOURCE_ROBUSTNESS.json']:
 x=json.loads((OUT/'reports'/name).read_text())
 for r in x['tasks']:
  assert r['exit_code']==0,(name,r['output'])
  csv_path=ROOT/r['output']
  if csv_path.suffix!='.csv':csv_path=Path(str(csv_path)+'.csv')
  assert sha(csv_path)==r['CSV_sha256'],(name,r['output'])
for r in json.loads((OUT/'reports/G4_CPU_GATE_V2.json').read_text())['cases']:
 assert r['status']=='PASS'
 for key,filename in [('stats_sha256','stats.txt'),('seu_sha256','seu.json'),('manifest_sha256','logical_manifest.json'),('rebuild_log_sha256','events.csv.rebuild.csv')]:
  assert sha(ROOT/r['output']/filename)==r[key],(r['case'],filename)
oldfailed=json.loads((OUT/'reports/G4_CPU_DESIGN_V1.json').read_text());assert sum(r['status']!='PASS' for r in oldfailed['tasks'])==4
contract=json.loads((OUT/'reports/G6_HARDWARE_CONTRACT.json').read_text());assert contract['PDK_PPA_measured'] is False
assert budget_charge_seconds()<=32*3600
record=dict(status='PASS_G0_TO_G6_SOFTWARE_REVIEW_HARDWARE_NOT_AUTHORIZED',baseline_commit=snap['commit'],old_snapshot_preserved=True,upstream_TAGE_hashes=upstream_hashes,transport_matches_existing_producer=True,initial_resource_failures_retained=4,required_hashes={name:sha(OUT/'reports'/name) for name in required},producer_source_lock_sha256=sha(OUT/'configs/gem5_source.lock.json'),producer_binary_sha256=sha(binary),scope_sha256=sha(ROOT/'sources/protection_scope.lock.json'),budget_charged_core_hours=budget_charge_seconds()/3600,budget_cap_core_hours=32,recommended_candidates=contract['recommended_hardware_measurement_candidates'],calibrated_radiation_rate=False,RTL_PPA_measured=False,exclusions=contract['baseline_scope_exclusions'])
write(OUT/'reports/G6_FINAL_AUDIT.json',record)
write(OUT/'reports/STATUS.json',dict(stage='G6_COMPLETE_STOP_FOR_DISCUSSION',audit_sha256=sha(OUT/'reports/G6_FINAL_AUDIT.json'),new_background_research_jobs=[],hardware_authorized=False,remaining='Actual hardware latency/ports/PPA after subsequent user approval; incomplete physicalcycleequivalence and sharedmetadata scope are explicit in contract',budget_charged_core_hours=record['budget_charged_core_hours']))
(OUT/'reports/BLOCKERS.md').write_text('# Blockers\n\n현재 외부 사용자 조치가 필요한 dependency는 없다. 소프트웨어 continuationG6가 완료됐다. 초기4resource실패는 보존했고 검증한revision으로 재실행했다. Hardware단계는 요청 범위에서 보류하며 승인 전 실행하지 않는다.\n\n초기build timing의 정확CPU값은 재빌드 때 덮어써서 복구할 수 없었다. 첫wall span3배를 conservative budget charge로 사용했고 원시compiler log는 보존했다. Timing·source3+codecoverage·issueatomicRMW·기존sharedmetadataexposure 한계는G6contract에 기록했다.\n')
(OUT/'reports/NEXT_ACTIONS.md').write_text('# Next\n\nG6PROMOTION_PACKET의 후보/조건/실패원인/physicaltimingcontract를 사용자와 논의한다. RTL/PDK/Cadence/SPICE/TCAD는 현재 실행하지 않는다.\n')
print(record['status'],record['budget_charged_core_hours'])
