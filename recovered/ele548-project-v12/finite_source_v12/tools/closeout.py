#!/usr/bin/env python3
"""Audit this source-component round; no CPU/EDA, no old workspace writes."""
from pathlib import Path
import csv,datetime,hashlib,importlib.util,json,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent;REPORT=BASE/'reports'
s=importlib.util.spec_from_file_location('bounded',BASE/'tools/gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def load(p):return json.loads(Path(p).read_text())
def verify(v):assert m.sha(v['path'])==v['sha256'],('CHANGED_CURRENT_BINDING',v['path'])
def main():
 service=REPORT/'SERVICE_GATE_D1.json';tage=REPORT/'TAGE_GATE_D1.json';bench=REPORT/'PIPELINE_BENCH.json';jump=REPORT/'INVERSE_JUMP_GATE.json'
 gate=load(service);assert gate['status']=='PASS_FINITE_SOURCE_COMPONENT_NOT_CPU_QUALIFICATION'
 verify(gate['source_lock']);sl=load(gate['source_lock']['path'])
 for item in sl['new_sources']:verify(item)
 for name in ['DEPENDENCIES_D1.json','TAGE_DEPENDENCIES_D1.json']:
  for item in load(REPORT/name)['files']:verify(item)
 for path in [tage,bench,jump]:
  value=load(path);verify(value['plan'])
  for item in load(value['plan']['path']).get('sources',load(value['plan']['path']).get('source_files',[])):verify(item)
  for name in ['build','run']:
   record=value[name];assert record['exit_code']==0
   for key in ['stdout','stderr','time']:verify(record[key])
 assert load(tage)['result']['normal_synthetic_controls']==60000 and load(tage)['result']['normal_real_trace_controls']==36000
 assert load(tage)['result']['speculative_controls']==48000 and load(tage)['result']['explicit_undos']==46500
 rows=list(csv.DictReader(Path(load(bench)['rows']['path']).open()));assert len(rows)==66
 verify(load(bench)['rows']);index={(r['mode'],int(r['update_L']),int(r['lookup_L']),r['ports'],r['pattern']):r for r in rows}
 summaries=[]
 for mode in ['RECURRENT','DIRECT','OVERWRITE']:
  for L in [1,2]:
   independent=index[mode,1,L,'SPLIT_2','READ_ONLY_INDEPENDENT'];single=index[mode,1,L,'SPLIT_2','READ_ONLY_SINGLE_PENDING']
   summaries.append({'mode':mode,'ready_L':L,'II':1,'requests':128,'multiple_pending_cycles':int(independent['model_cycles']),
                     'single_pending_cycles':int(single['model_cycles']),'source':'Same component/config/L/ports; sender admission bound only'})
 manifest=load(gate['manifest']['path']);verify(gate['manifest'])
 sizes=[{'mode':v['mode'],'update_L':v['update_L'],'lookup_L':v['lookup_L'],'implemented_component_bits':v['total_bits']} for v in manifest['models']]
 old=m.V11/'overwrite_v11/reports/PRESERVATION.json'
 for item in load(old)['preserved']:verify(item)
 oldzip=m.V11/'overwrite_v11/artifacts/BP_SEU_V11_OVERWRITE_RESULTS.zip'
 assert m.sha(oldzip)=='695b7975d0c3c8d02383c6734f3debca35684755ab7b46da7a6aa10a9044b3de'
 assert len(list((m.V9/'rate_state_v9').glob('**/reports/run_starts/*.json')))==352
 assert len(list((m.V10/'native_lifetime_next/runtime/reports/run_starts').glob('*.json')))==108
 assert len(list((m.V11/'overwrite_v11/runtime/cpu_regression/run_starts').glob('*.json')))==6
 assert len(list((m.V11/'overwrite_v11/runtime/cpu_fault_next/run_starts').glob('*.json')))==12
 executions=list((BASE/'runtime').glob('*/EXECUTION.json'))
 assert all(load(p)['exit_code']==0 for p in executions),'FAILED_EXECUTION_RETAINED_NOT_FINAL_PASS'
 resources=m.budget()
 out={'status':'PASS_FINITE_SOURCE_D1_NATIVE_FUNCTIONAL_AND_COMPONENT_PIPELINE_NOT_GEM5_OR_HARDWARE_QUALIFICATION',
      'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'prior_turn':'PROGRESS_ACTUAL12_CPU_AND_AUDIT',
      'service_gate':m.ref(service),'native_functional_gate':m.ref(tage),'component_bench':m.ref(bench),'inverse_jump_proof':m.ref(jump),
      'actual_global_CPU':3487,'CPU_cap':3487,'new_CPU':0,'new_EDA':0,'hardware_qualified_candidates':0,
      'actual_component_cases_current_revision':66,'historical_queued_sampling_cases':60,
      'historical_timing_scope':'C2 L is arithmetic stage count plus one sampling cycle; D1 ready queries sample at accept and have actual L1/L2. Old cases preserved, never relabelled.',
      'single_pending_control':summaries,'component_storage':sizes,'resources':resources,
      'command_logs':[m.ref(p) for p in executions],
      'preserved_v11_zip':m.ref(oldzip),
      'not_done':['Production gem5 fetch/BPU integration','Bounded/coalesced squash undo packet service beyond n2',
                  'Parity/ECC/TMR protection controller staging on this common source',
                  'Real CPU next-PC/history-dependent throughput and cycles/IPC',
                  'Fresh paired fault CPU/WHOLE/independent owners','Hardware timing/PPA/safety'],
      'full_research_goal':'ACTIVE_NOT_COMPLETE','closeout_tool':m.ref(Path(__file__))}
 m.put(REPORT/'FINAL_GATES.json',out)
 table='\n'.join(f"|{v['mode']}|{v['ready_L']}|{v['multiple_pending_cycles']}|{v['single_pending_cycles']}|" for v in summaries)
 storage='\n'.join(f"|{['recurrent','direct','overwrite'][v['mode']]}|{v['update_L']}/{v['lookup_L']}|{v['implemented_component_bits']:,}|" for v in sizes)
 text=f'''# V12 공통 finite source와 실제 fold-query pipeline

## DONE — 현재 D1 producer

**IMPLEMENTED/TESTED RESULT:** 별도 `codex/v12-finite-source` worktree에서 recurrent/direct/overwrite에 같은1130bit raw ring(130active+1000retention)과 path16, 실제 source head/credit/control, 유한 FIFO/stage를 구현했다. 기존 v9/v10/v11 source/config/binary/raw/ZIP은 보존했다. 이전 goal turn은 actual12 CPU 완료라는 progress였으며 이번에도 authoritative source와 실제 실행 증거를 추가했다. 전체 목표는 여전히 active다.

- Source/update command4칸, fold-query4칸, query response4칸, source ACK4칸이다. 주 모델은 source/query 각1 ingress·sampling·egress 포트와 별도1/cycle retirement control이다. 공유 포트는 동일 저장소의 직렬 service 민감도 대조다. Commit을 불필요하게 fold RMW 뒤에 세우지 않았다.
- 준비된 query는 accept에서 actual operand를 latch하고 실제 다음 stage에서 계산한다. L1은 c→c+1, L2는 c→c+1의 부분 계산→c+2의 나머지 계산/공개다. Queue-full, 필요한 source version/fold freshness, correction hold는 별도 대기다. 작업 완료 뒤 debt만 청구하지 않는다.
- Source RMW는 실제 한 service edge에서 append/undo/head/path를 변경하고 reduction 입력을 latch한다. 업데이트와 query의 L을 분리했다. Recurrent L2는 실제 low-word partial forwarding과 predecessor 확인 후 high-word sampling으로 정상 append II1을 지원한다. Free U0나 모든 callback 직렬화만으로 결론을 내리지 않는다.
- Read-before-write, RAW version, stalled old read 보존, FIFO-full·response-full, squash/stale discard, epoch wrap+receiver ACK, metadata 정정 중 squash latch·추가 SEU를 검증했다. Accepted source operand는 squash로 버리지 않는다.
- Pinned source 대조18,000건, metadata4,492개 실제 bit의 SBU 정정/한 cycle hold, 데이터 latch SEU, source rollback 재진입, credit1000 경계, 모든 manifest bit XOR, fold200 SBU/HOLD gate가 통과했다. 두 copy 모두 DUE인 fixture는 fail-closed exception으로 유지하며 무영향/프로그램 성공으로 분류하지 않는다.

## 전체 TAGE 기능 대조

**IMPLEMENTED/TESTED RESULT:** 동일 pinned TAGE의 prediction/index/tag/provider·훈련·logical state/GHR·RNG를 C++ harness에서 비교했다. Synthetic 정상60,000 + 기존 실제 HW1 design trace36,000 + speculative48,000 control, 명시적 undo46,500건이 통과했다. Signed counter bit·source snapshot/deep-copy도 확인했다. Trace는 독립 holdout이나 SPEC CPU 바이너리 실행이 아니다.

Harness는 native API 검증을 위해 actual source를 host helper에 복사한다. 이 observer는 controller의 detector/repair operand가 아니고 무료 hardware port로 모델링한 것도 아니다. Harness는 serial functional scoreboard이며 O3 frontend/CPU timing backend가 아니다. BPU PC/table/provider·실제 next-PC feedback과 보호 controller는 아직 연결하지 않았다.

## 실험으로 구분한 것

아래는 독립 fold-query128개의 **부품 model cycles**다. 같은 ready-query L/II=1/포트에서 sender의 single-pending 제한만 바꿨다.

|representation|ready L|multiple pending|single pending|
|---|---:|---:|---:|
{table}

**NEW DERIVATION:** 이 구성의 독립 요청에서는 L1→L2의 fill 변화가1cycle인 반면, L2의 single-pending 제한은129→256cycles를 만들었다. L1에서는 consume/issue 동시 경계 때문에 single-pending 손실이 없었다. 이 결과를 기존 v6/gem5 CPU의 지연 민감도나 pipeline 순위로 일반화하지 않는다.

L1 mixed Read/Append256개는 공유포트257→별도포트129cycles였다. L2·별도포트의 source-version 일치 stream에서는 stored-fold 두 방식에 fold publication 대기가 남았다. 실제 이전 reply를 받아 다음 source operand를 만드는 의존성 fixture100개는500cycles였다. 이 fixture도 실제 프로그램의 next-PC stream은 아니다.

D1의66개 현재 case는 같은 logical command 순서를 pinned source와 대조했다. C2의 이전60개는 operand sampling이 한 cycle 더 걸리는 다른 producer의 원시 결과로 보존했다. 지연 정의를 바꿔 옛 결과에 새 이름을 붙이지 않았다. 직접 방식의 사용하지 않는 update-L 축은 중복 실행하지 않았다.

CPU 수준에서는 아직 읽기 latency/single-pending/next-PC 의존성의 기여를 분리하지 못했다. 실제 cycles·IPC·프로그램별 순위나 새 A/B/C/D는 없다.

## 비용과 exposure 경계

|representation|설정 update/query L|구현된 source/control/stage bits|
|---|---:|---:|
{storage}

이 수는 실제 논리 저장소를 열거한 값이며 최소 필요 bit, 면적, 에너지 또는 SEU cross-section이 아니다. `runtime/manifest_D1.json`에 raw 전체retention·path·fold·모든 FIFO/latch/ID/epoch/control/실제 SECDED 두 copy를 넣었다. Direct에는 persistent fold200이 없다. 현재 queue/codeword 구조는 최적화하지 않은 공통 reference다.

Raw는 register-array/tap interface로 모델링하며 old/current query window130과 update 후 window·outgoing taps 및 최대2bit 쓰기/forwarding이 필요하다. SRAM의1개 read port로 이 동작이 무료라고 가정하지 않는다. 모든 codeword의 parallel decode/encode가 정상 stage에 들어간다는 가정과 repair의 trusted absolute-time helper는 물리 검증 전이다. 기존 table65024bits·BTB/RAS/CPU instruction/PC context는 이 **source 부품** manifest의 범위 밖이다. Full WHOLE population이나 full TAGE safety로 확대하지 않는다.

## 공정한 recurrent baseline을 위한 수학 gate

**NEW DERIVATION / IMPLEMENTED UNIT PROOF:** raw buffer가 바뀌지 않는 fold-opaque atomic undo 구간에서는

`F_after = ROR(F_before XOR Phi(source_before), n) XOR Phi(source_after)`

가 pinned inverse recurrence와 같다. Actual source 두 window와 actual folded word만 쓴다. Arbitrary source/fold63,063 대조와 모든 folded SBU×undo0..1000의200,200 대조가 통과했다. 원래 folded discrepancy가 회전해 남으므로 overwrite recovery로 바꾼 baseline이 아니다.

이것은 `inverse_jump.hpp`의 순수 함수/증명 gate이며 아직 source controller의 큰 undo packet stage로 구현하지 않았다. 두 Phi reducer·rotation·입력 latch 비용도 무료가 아니다. 중간 source SEU나 check/training/read가 끼는 구간을 같은 atomic jump로 바꾸었다고 주장하지 않는다. Source queue4개가 실제 BPU의 긴 squash callback을 받을 수 있도록 bounded packet/예약을 구현할 때 사용할 정확성 근거다.

## NOT DONE / BLOCKERS / NEXT

기존 S*=346bits P0/P_ED/P_ECC/P_TMR·frequent/periodic/direct 비교를 보존했다. 새 공통 source 위에 parity/ECC/TMR check/update/repair와 그 유한 timing은 아직 연결하지 않았다. 이를 제외하고 최종 승자를 고르지 않는다. 새 후보가 좋을 것을 전제하지 않는다.

다음 구현은 긴 squash의 source operand를 잃지 않는 bounded undo packet/credit 및 PC/context/freshness를 가진 gem5 BPU 연결이다. 그 다음 controller/protection operation gate와 native checksum/정상 CPU gate 후 기존 event 계약의 paired 평가로 간다. 현재 CPU상한3487/3487이라 새CPU0이며, 이 코드를 gem5 통과로 부르지 않는다. 새 CPU 수/시간 요청은 실제 producer와 gate를 준비한 뒤 구체화한다. 현재 반복 승인을 요청하지 않는다.

부품 LLVM/compile block이나 license/path blocker는 없다. 최신 SOURCE_D1.lock과 실제 dependency SHA, runtime 명령/로그/GNUtime을 검증했다. 새 recorded {resources['new_recorded_coreh']:.6f}/0.25coreh, v11+v12 {resources['v11_v12_recorded_coreh']:.6f}/2.5coreh, 네 worktree {resources['all4_worktrees_GiB']:.6f}/8GiB였다. V11+v12합산192MiB·기존과금34GiB/free10GiB와 합산16/global108coreh도 유지했다. Stage별 실제 실패 exit는0건이며 A/C/D의 다른 가정·코드는 보존했다. RTL/Cadence/SPICE/TCAD 실행0, hardware-qualified후보0이다.
'''
 with (REPORT/'FINAL_REPORT.ko.md').open('x') as f:f.write(text)
 m.put(REPORT/'software.lock.json',{'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'compiler':{'path':str(m.CC),'version':subprocess.check_output([str(m.CC),'--version'],text=True).splitlines()[0]},'python':{'path':sys.executable,'version':sys.version.split()[0]},'TAGE_pin':'c8222cc67a399bfc01e8658dd14b30d5bfd634f9','source_lock':m.ref(REPORT/'SOURCE_D1.lock.json'),'actual_includes':m.ref(REPORT/'TAGE_DEPENDENCIES_D1.json'),'new_installations':0,'new_CPU':0,'new_EDA':0})
 print(json.dumps({'status':out['status'],'resources':resources,'CPU_global':3487,'current_component_cases':66}))
if __name__=='__main__':main()
