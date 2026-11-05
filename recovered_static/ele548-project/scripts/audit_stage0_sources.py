#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,subprocess
root=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected=json.loads((root/'sources/source_manifest.json').read_text())
verified=[]
for item in expected:
 p=root/item['path'];actual=sha(p)
 verified.append({'source_id':item['id'],'path':item['path'],'expected_sha256':item['sha256'],'actual_sha256':actual,'status':'PASS' if actual==item['sha256'] else 'FAIL'})
extra=[]
for pattern in ['scripts/render_software_integration.py']:
 for p in sorted(root.glob(pattern)):
  if p.is_file():extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'source/model/recovery/CPU integration; missing CPU phases stay pending, actual PPA deferred'})
for pattern in ['scripts/audit_software_completion.py']:
 for p in sorted(root.glob(pattern)):
  if p.is_file():extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'requirement-level raw evidence audit; pending CPU campaigns cannot be marked complete'})
for pattern in ['scripts/rng_namespace.py','tests/test_rng_namespace.py']:
 for p in sorted(root.glob(pattern)):
  if p.is_file():extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'namespace v2 separates trial/role/entity streams; fixes additive seed aliases without changing S* or model/sample plan'})
for pattern in ['scripts/export_e4_software_contract.py','sources/e4_software_interface_contract.json']:
 for p in sorted(root.glob(pattern)):
  if p.is_file():extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'E4 functional/assumed-timing operation handoff; audited CPU logical activity proxies, NOT RTL switching or PPA'})
for pattern in ['scripts/summarize_e3_cpu.py','scripts/render_e3_cpu_report.py','scripts/finish_e3_analysis.py','tests/test_e3_analysis.py','scripts/qualify_cern_footprints.py','scripts/run_cern_footprints.py','scripts/summarize_cern_footprints.py','tests/test_cern_footprints.py','sources/cern_methods.lock.json','sources/cern_hypothetical_mapping_manifest.json','data/curated/cern_footprint_model_card.json']:
 for p in sorted(root.glob(pattern)):
  if p.is_file():extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'O3 matched-trial analysis or primary-author-reviewed conditional CERN footprint stress; no calibrated physical rate/layout claim'})
for pattern in ['gem5_ext/*','gem5/o3_seu.py','src/tests/spec_history_e3.cpp','scripts/prepare_gem5_e3.py','scripts/test_gem5_e3.py','scripts/run_e3_cpu.py','scripts/run_flying_timing.py','scripts/summarize_flying_timing.py','setup/build_gem5_e3.sh','sources/gem5_e3_source.lock.json','configs/e3.cpu.lock.json','configs/flying_timing.lock.json']:
 for p in sorted(root.glob(pattern)):
  if p.is_file():extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'E3 logical CPU injection/response protocol or detector-time stress; explicit assumptions and exclusions in stage reports'})
for pattern in ['src/tests/protection_e2.cpp','tests/test_e2_manifest.py','scripts/run_e2.py','scripts/summarize_e2.py','setup/build_e2.sh','sources/e2_protection_logical_manifest.json','sources/public_workload_sources.lock.json','setup/prepare_public_workloads.py','setup/build_user_musl.sh','setup/build_public_workloads.py','scripts/run_o3_public_baseline.py','scripts/check_o3_opt_equivalence.py','gem5/o3_public.py']:
 for p in sorted(root.glob(pattern)):
  extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'E2 recovery/holdout or primary-source public-program E3 setup; see individual source/config/validation contracts'})
for pattern in ['src/**/*.hpp','src/standalone/**/*.hh','src/tests/predictor_e0.cpp','src/tests/adapter_memory.cpp','src/tests/multiplicity_smoke.cpp','src/tests/event_stream.cpp','src/tests/e1_correctness.cpp','src/replay/*.cpp','scripts/prepare_e1_windows.py','scripts/run_e1.py','scripts/run_e1_warmup_sensitivity.py','scripts/summarize_e1.py','setup/build_e1.sh','tests/test_e1_windows.py','sources/protection_scope.lock.json','src/standalone/params/TAGEBase.hh','scripts/prepare_tage_standalone.py','scripts/prepare_trace_windows.py','scripts/summarize_stage0_pilot.py','scripts/audit_stage0_sources.py','scripts/qualify_logical_manifests.py','scripts/run_charm_pilot.py','scripts/parse_cern_clusters.py','scripts/run_repeated_pilot.py','scripts/check_repeated_regression.py','scripts/qualify_current_datasets.py','setup/run_repeated_pilot.sh','setup/run_cpp_stage0.sh','setup/build_gem5.sh','setup/lock_software.py','setup/build_gem5_stage0.sh','setup/run_gem5_checksum.sh','gem5/o3_checksum.py','workloads/checksum_freestanding.c','configs/*.lock.json','data/raw/cern/*.txt','sources/predictor_logical_state_manifest.json','sources/gshare_logical_state_manifest.json','sources/tage_fault_sites.jsonl']:
 for p in sorted(root.glob(pattern)):
  extra.append({'path':str(p.relative_to(root)),'sha256':sha(p),'provenance':'Stage0/follow-on local research code/config or verified public CERN file; see individual source binding and acquisition logs'})
result={'schema_version':1,'original_sources_status':'PASS' if all(x['status']=='PASS' for x in verified) else 'FAIL','original_sources':verified,'stage0_files':extra,'gem5_binding':json.loads((root/'reports/tage_source_binding.json').read_text()),'original_archive_verification':json.loads((root/'reports/original_archive_verification.json').read_text()),'workload_windows':json.loads((root/'reports/workload_windows.json').read_text()),'logical_manifest':'sources/predictor_logical_state_manifest.json','TCAD':'excluded/unavailable','distribution':'private user workspace; raw traces, papers and course materials not approved for public redistribution'}
(root/'sources/manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['original_sources_status'],'original_source_files':len(verified),'stage0_files':len(extra)},indent=2))
raise SystemExit(0 if result['original_sources_status']=='PASS' else 1)
