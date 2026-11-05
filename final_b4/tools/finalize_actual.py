"""Quiescent result audit and Korean report, using actual files only."""
import sys,pathlib,collections,json,statistics,subprocess,datetime
sys.dont_write_bytecode=True
import resources as r
B=r.BASE

def audit():
 records=[];active=[];raw_files=0
 for marker in sorted((B/'runtime/run_starts').glob('*.json')):
  t=r.load(marker);p=pathlib.Path(t['output'])/'EXECUTION.json'
  if not p.exists():active.append(t);continue
  x=r.load(p)
  for name,digest in x.get('hashes',{}).items():assert r.sha(p.parent/name)==digest,('RAW_HASH_CHANGED',str(p.parent/name));raw_files+=1
  records.append({'label':t['label'],'phase':t['phase'],'status':x['status'],'failure':x.get('failure'),'execution':r.ref(p)})
 assert not active,('ACTIVE_RECORDS_NOT_FINAL',len(active))
 producer=r.load(B/'reports/PRODUCER_B2.lock.json')
 for z in [producer['binary'],producer['config'],producer['observer']]+producer['actual_dependencies']:assert r.sha(z['path'])==z['sha256'],('PRODUCER_SOURCE_DRIFT',z['path'])
 for z in r.load(producer['source_lock']['path'])['files']:assert r.sha(z['path'])==z['sha256']
 old=r.load(B/'reports/PRESERVED_BASELINE.lock.json');assert r.sha(old['current_binary']['path'])==old['current_binary']['sha256']
 inputs=r.load(B/'reports/COHORT_INPUTS.lock.json')
 for cohort in ('DEV','EVAL'):
  for item in inputs[cohort]:
   for key in ('input','program_binary','expected_stdout','payload'):
    if key in item:assert r.sha(item[key]['path'])==item[key]['sha256'],('INPUT_DRIFT',cohort,item['program'],key)
 try:resources=r.snapshot()
 except AssertionError as exc:resources={'resource_guard_failure':repr(exc),'actual_new_CPU':len(records)}
 complete=(B/'reports/FINITE_MATRIX_COMPLETED.json').exists() and (B/'reports/NATIVE_REFERENCE6.json').exists() and r.load(B/'reports/NATIVE_REFERENCE6.json')['status']=='PASS'
 if complete:
  for name,count in (('DEV_CLEAN',18),('DEV_SERIAL',18),('DEV_L2',6),('DEV_FAULT',102),('EVAL_CLEAN',18),('EVAL_FAULT',408)):
   x=r.load(B/'reports'/(name+'_COMPLETED.json'));assert x['status']=='PASS' and x['actual_runs']==count
  evaluation=r.load(B/'reports/EVAL_ANALYSIS.json');assert evaluation['attempted_faults']==408
 report={'status':'PASS_COMPLETED_ACTUAL_MATRIX_AUDIT_NOT_HARDWARE_QUALIFICATION' if complete else 'INCOMPLETE_OR_STOPPED_ACTUAL_EVIDENCE_AUDITED','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'CPU_records':len(records),'records':records,'raw_hashes_checked':raw_files,'resources':resources,'compiled_source_and_original_ELF_preserved':True,'actual_model_only_no_RTL_PPA':True}
 r.put(B/'reports/ACTUAL_TERMINAL_AUDIT.json',report)
 lines=['# v18 실제 실행 보고서','',f"상태: {report['status']}",'',f"DONE: 실제 CPU {len(records)}회와 raw SHA {raw_files}개, B2 compiled dependencies/source/config/ELF, 기존 ELF·고정 program/input/answer SHA를 검증했다. 초기 실패4와 진단1을 원본으로 보존한다.",'']
 if complete:
  lines += ['개발102/독립408 fault 실행과 정상·직렬/L2·native reference가 종료됐다. 프로그램별 결과는 아래 표와 DEV_ANALYSIS/EVAL_ANALYSIS의 실제 owner별 A/B/C/D를 본다.','', '| 프로그램 | 방법 | clean cycles | IPC | 실제 consume/source cycle | 최대 lookup |','|---|---|---:|---:|---:|---:|']
  for x in evaluation['clean']:lines.append(f"| {x['program']} | {x['method']} | {x['cycles']} | {x['IPC']:.6f} | {x['consumed_per_source_cycle']:.6f} | {x['max_lookup_pending']} |")
  lines += ['','| 프로그램 | 조건 | 방법 | valid/observed owners | mean B−D cycles | bootstrap95% cycles | 순이득 %A |','|---|---|---|---:|---:|---|---:|']
  for x in evaluation['paired_summaries']:
   if x['method']=='P0':continue
   ci=x['bootstrap95_cycles'];value=x['mean_B_minus_D'];pct=x['mean_net_pct_A'];fmt='미산출' if ci is None else f'[{ci[0]:.1f}, {ci[1]:.1f}]';lines.append(f"| {x['program']} | {x['scenario']} | {x['method']} | {x['valid_pairs']}/{x['observed_owners']} | {value if value is not None else 'null'} | {fmt} | {pct if pct is not None else 'null'} |")
  lines += ['','Inference: 표본 단위는 program/scenario별 독립owner8이며, 보호법반복·재사용A/C를추가표본으로세지않는다. CI는n8 exploratory paired bootstrap이다. 개별음수/0/helpful fault·exact sign/Holm·완전pair ownerID·전체실패분모를JSON에남겼다. 프로그램을pooling해불리한결과를숨기지않는다.']
 else:
  stops=[r.ref(p) for p in (B/'reports').glob('ROUND_STOP_*.json')];lines += ['NOT DONE: 전체 matrix가 완료되지 않았다. 최신 STOP/개별 EXECUTION과 고정 plan에서 아직 시작하지 않은 조건을 확인한다. 실행하지 않은 조건의 cycles/CI를 생성하지 않았다.','', '실제 STOP 기록: '+json.dumps(stops,ensure_ascii=False)]
 lines += ['','VERIFIED ASSUMPTIONS: 공통L/II/ports·vector23lane check1/encode1/provider1과metadata stage-fit은모델가정이다. SameL serial은같은source/RMW자원에서early unconditional response를기다리는frontend대조다. L2는source query의추가실제stage민감도이며모든방법의L2직렬대조는아니다. NativeL0는별도reference다.','', '분리 범위: sameL serial/early 비교는nextPC가이미알려진unconditional의실제중첩과singlepending대기의영향을분리한다. Conditional next-PC/history와source ordering의대기는여전히남는다. L1/L2와고정II/ports 비교는SOURCE history/fold readstage의CPU민감도를측정한다. Provider/table-LUT readlatency는1로고정했으므로LUT latency 자체의1→2효과는미확정이다. 모든내부stall합계를정확한CPI인과분해로바꾸지않는다.','', '보호 비용 해석: P0/Direct도같은check/encode slot을통과한다. C−A가작다고실제ECC/TMR hardware비용이0이라는뜻이아니다. SOURCE는고정raw130조건부공격, WHOLE은추가storage까지포함한모델stress이며서로pooling하지않는다. S*밖retention재진입·uncodedpayload·CPU-owned BI제외와protectionepoch의component/fullCPU검증범위를manifest/modelcard에서구분한다.','', '비교기준의한계: A/B/C/D primary는같은finite/check/encode resource의P0를A/B로쓴다. 원래native는정상reference6만새로측정했으므로matched-native fault B−D의절대이득은이번matrix에서측정하지않았다. NATIVE_BREAK_EVEN_THRESHOLDS는실측native A와finite D로계산한필요조건이며실측native fault benefit이아니다.', '', 'BLOCKERS/NEXT: 현재완료상태와stop원인에따라미시작동결조건을이어서실행하거나실제결과를검토한다. RTL/Cadence/SPICE/TCAD·PDK timing/PPA는수행하지않았으며hardware winner/qualification을선언하지않는다.']
 (B/'reports/ACTUAL_TERMINAL_REPORT.ko.md').write_text('\n'.join(lines)+'\n')
 print(report['status'],len(records),raw_files,flush=True)
if __name__=='__main__':audit()
