"""G6 final report from audited actual cycles; no PPA fabrication."""
import json,csv,statistics,math
import numpy as np
from continuation_common import *
from continuation_statistics import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
primary=json.loads((OUT/'reports/CPU_HOLDOUT_SUMMARY.json').read_text());assert primary['status']=='PASS_FIXED_SCOPE_PAIRED_ANALYSIS'
source=json.loads((OUT/'reports/G5_SOURCE_ROBUSTNESS.json').read_text());assert source['status']=='PASS'
extra=json.loads((OUT/'reports/G5_CPU_EXPOSURE_ROBUSTNESS.json').read_text());assert extra['status']=='PASS'
freeze=json.loads((OUT/'configs/cpu_policy_freeze.lock.json').read_text());pairs=json.loads((OUT/'reports/CPU_HOLDOUT_PAIRS.json').read_text())['pairs']
clean=primary['clean_rows'];programs=sorted({r['program'] for r in clean});variants=[v['id'] for v in freeze['variants']];baseline={r['program']:r for r in clean if r['variant']=='P0'}
source_means=[]
for scenario in sorted({r['scenario'] for r in source['tasks']}):
 for variant in ['P0','P_ED','P_ECC','P_TMR','N1','H1']:
  rr=[r for r in source['tasks'] if r['scenario']==scenario and r['id']==variant]
  source_means.append(dict(scenario=scenario,variant=variant,n=len(rr),mean_net_misses=statistics.mean(int(r['metrics']['net']) for r in rr),mean_delta_MPKI=statistics.mean(float(r['metrics']['delta_MPKI']) for r in rr),mean_checks=statistics.mean(int(r['metrics']['checks']) for r in rr),mean_rebuild_steps=statistics.mean(int(r['metrics']['rebuild_steps']) for r in rr)))
write(OUT/'reports/G5_SOURCE_SUMMARY.json',dict(status='PASS_SOURCE_POINTS_NOT_POPULATION_CI',rows=source_means,input_note='historical traces with fresh owner and different fault observation window; CPUinputsarefresh',two_seed_per_input_condition=True))
extra_summary=[]
for scenario in sorted({r['scenario'] for r in extra['tasks']}):
 for variant in sorted({r['id'] for r in extra['tasks'] if r['scenario']==scenario}):
  rr=[r for r in extra['tasks'] if r['scenario']==scenario and r['id']==variant];values=[]
  for r in rr:
   C=next(x for x in clean if x['program']==r['program'] and x['variant']==variant);A=baseline[r['program']]['cycles']
   values.append(dict(program=r['program'],owner=r['owner'],extra_task_cycles=r['cycles']-C['cycles'],total_slowdown_pct=100*(r['cycles']-A)/A,applied_events=r['seu']['applied_events'],phi_mismatch=r['seu']['fold_phi_mismatch_words'],end_state_diff=r['seu']['canonical_base_state_hash']!=next(t for t in json.loads((OUT/'reports/G5_CPU_HOLDOUT_V2.json').read_text())['tasks'] if t['program']==r['program'] and t['scenario']=='zero' and t['id']==variant)['seu']['canonical_base_state_hash']))
  extra_summary.append(dict(scenario=scenario,variant=variant,n=len(rr),values=values,point_mean_slowdown_pct=statistics.mean(v['total_slowdown_pct'] for v in values),rate_calibrated=False))
write(OUT/'reports/G5_EXTRA_SUMMARY.json',dict(status='PASS_DIRECTED_AND_PER_BIT_STRESS',summary=extra_summary,not_primary_recovery_CI=True,fault_population='enumerated predictor/controller cells; excludesexistingBI/CPUqueues/arch/aging/RNG'))
whole_pairs=[]
whole=[r for r in extra['tasks'] if r['scenario']=='FULL_EQUAL_PER_BIT_SBU']
for row in whole:
 b=next(r for r in whole if r['program']==row['program'] and r['owner']==row['owner'] and r['id']=='P0')
 assert b['input_sha256']==row['input_sha256']
 c=next(r for r in clean if r['program']==row['program'] and r['variant']==row['id'])
 a=baseline[row['program']]
 whole_pairs.append(dict(program=row['program'],variant=row['id'],owner=row['owner'],
  **abcd(a['cycles'],b['cycles'],c['cycles'],row['cycles']),
  events_B=b['seu']['applied_events'],events_D=row['seu']['applied_events'],
  schedule_coupling='shared max-population Poisson marks; variant schedules differ only at absent sites',
  status='EXPLORATORY_THREE_OWNERS_PER_FIXED_INPUT'))
write(OUT/'reports/G5_WHOLE_PAIRED_POINTS.json',dict(status='EXPLORATORY_WHOLE_LOGICAL_STORAGE_PAIRING',pairs=whole_pairs,
 baseline_total_rate_per_cycle=1e-6,per_bit_rate_per_cycle=1e-6/65370,
 target_rate_calibrated=False,additional_gamma_penalty=False))

# Point-vector Pareto. No incomparable units are collapsed into a score.
front=[]
for variant in variants:
 cc=[r for r in clean if r['variant']==variant];ss=[s for s in primary['summary'] if s['variant']==variant]
 front.append(dict(id=variant,extra_bits=max(r['bits'] for r in cc)-65370,worst_clean_pct=max(100*(r['cycles']/baseline[r['program']]['cycles']-1) for r in cc),worst_group_residual_loss_pp=max(m['residual_loss_pp']['mean'] for s in ss for m in s['per_program'].values()),repeat_net_pp=next(s['metrics']['net_pp']['mean'] for s in ss if s['scenario']=='CHARM_6T'),repeat_net_CI95=next(s['metrics']['net_pp']['CI95'] for s in ss if s['scenario']=='CHARM_6T')))
for r in front:
 r['point_dominated_by']=[s['id'] for s in front if s['id']!=r['id'] and all(s[k]<=r[k] for k in ['extra_bits','worst_clean_pct','worst_group_residual_loss_pp']) and any(s[k]<r[k] for k in ['extra_bits','worst_clean_pct','worst_group_residual_loss_pp'])]
budgets=[]
for c in [.25,.5,1,2]:
 for f in [.5,1,2,5]:budgets.append(dict(clean_ceiling=c,residual_ceiling=f,feasible=[r['id'] for r in front if r['worst_clean_pct']<=c and r['worst_group_residual_loss_pp']<=f]))
write(OUT/'reports/G6_PARETO.json',dict(status='POINT_VECTOR_NOT_PHYSICAL_OPTIMUM',designs=front,budget_feasibility=budgets,operation_counts_scope='separate actual source/check/encode/vote/scan/writeactivity vectors in rawseu.json; never convertthese intoareaenergy',deployment_weights_not_assumed=True))
recommend=[]
for r in front:
 if r['id']=='N1' and r['worst_clean_pct']<=2 and r['repeat_net_CI95'] and r['repeat_net_CI95'][0]>0:recommend.append('N1')
# Mandatory ECC is retained as a contrasting coding candidate for even/clustered patterns;
# it is a measurement candidate, not a universal CPU winner.
if 'N1' in recommend:recommend.append('P_ECC')
recommend=recommend[:2]
contracts=dict(status='SOFTWARE_CANDIDATE_HANDOFF_NO_HARDWARE_IMPLEMENTATION',recommended_hardware_measurement_candidates=recommend,no_qualified_candidate=not recommend,all_baselines_retained=True,Sstar346_frozen=True,PDK_PPA_measured=False,source_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',baseline_scope_exclusions=['existingBI/checkpoints/CPUqueues/BTB/RAS/architecturalstate/aging/RNG','absolute simulator timingtags; issueatomic maintenancework model is not physicalserializedRMW'],protocol={'N1':{'k':int(next(v for v in freeze['variants'] if v['id']=='N1')['k']) if 'N1' in variants else None,'source':'parity','fold':'parity','recovery':'global130actualcontrolrefill plus epoch/actualCPUqueuedrain','forward_delta':'foldp ^= incoming XOR outgoing at each banklength; inverse/correctedcallbacks explicitly tested','normal_maintenance':'U0 same-stage hypothesis; U1 finite service sensitivity measured separately','required_taps':'7bankoutgoing rawbits plus raw130boundary and path16boundary;21foldparities/2sourceparities; use portcounts fromcallbackactivity','checker':'historical serialC1,Q1; no implementedbackgroundII1pipeline','extra_bits':72},'P_ECC':{'source_and_fold':'23natural shortenedSECDED codewords;source130+16,f200;checkbits121 pluscontrol41','recovery':'correct+writeback;DUEglobalrefill','extra_bits':162,'timing_assumption':'sameC1/R4 baseline; physical codeword delay notmeasured'},'H1_rejected_development':freeze['rejected_development'].get('H1')},field_data_and_operation_vectors='configs/manifest*.json, actualCPUlogical_manifest.json, rawseu.json andevents/repair/rebuildlogs',future_required=['Verify normalpathclock/ports/RMW/checker/rollbackcontract andmissingsharedmetadata beforeRTLpromotion.','SamePDKlibraryPVTclockloadfunction actualPPA afteruserauthorizeshardware.','MeasuredlatencyIIenergy feedactualO3reruns; noTCAD.'])
contracts['normal_port_feasibility'] = dict(status='UNVERIFIED_PHYSICAL_CONTRACT',
 N1_outgoing_source_taps=7, source_boundary_taps=['raw age130 boundary','path16 boundary'],
 fold_parity_words=21, source_parity_words=2,
 inspection_scope='23 natural words; codeword-parallel checking is an assumption in historical C1 checker model',
 peak_cycle_port_demand='not cycle-instrumented; actual maximum maintenance backlog and total callback operations are retained',
 U0='No additional service cycle; incremental network must fit existing clock stage. This is a feasibility hypothesis.',
 U1='One reserved cycle per history-write callback, bounded burst descriptor, issue-atomic functional updates.',
 shared_metadata='Existing prediction checkpoints/BI/queues are excluded; physical interface cost must include ownership/boundary reconciliation.')
contracts['rebuild_contract'] = dict(source_scan_bits_per_step=16, fold_XOR_accumulators=21,
 accumulator_bits=200, accumulator_parity_bits=21, protected_commit_shadow_bits=161,
 publish_words_per_step=1, total_steps_after_actual_drain=32,
 restart_bound=2, oracle_source=False,
 control_coverage='Injected legal cursor/FSM corruption can yield undetected self-consistent state; property tests bound liveness, not universal recovery.')
write(OUT/'reports/G6_HARDWARE_CONTRACT.json',contracts)
# Explain source-conditioned pattern results separately from O3 cycles.
source_text = ['# G5 오류 패턴 민감도', '',
 '288회 C++ 실행의 추가 오예측(net=harm−help)을 비교했다. 각 cell은 고정된 역사적 입력 2개 × 새로운 owner 2개의 평균이다. CPU cycles나 물리적 SEU rate를 추정한 표가 아니며, 행 간 사건 수·시간 모양이 달라 직접 평균해 deployment 순위를 만들지 않는다.', '',
 '|조건|P0|P_ED|P_ECC|P_TMR|N1 k64|H1 k32|', '|---|---:|---:|---:|---:|---:|---:|']
for scenario in sorted({r['scenario'] for r in source_means}):
 values = [next(r['mean_net_misses'] for r in source_means if r['scenario']==scenario and r['variant']==v) for v in ['P0','P_ED','P_ECC','P_TMR','N1','H1']]
 source_text.append('|'+scenario+'|'+'|'.join(f'{v:.2f}' for v in values)+'|')
source_text += ['',
 'CERN p29의 contiguous→interleaved mapping에서 P_ED의 잔여 net misses는 2207.25→1892.00, ECC는 521.00→495.50이었다. Ar catalog에서는 H1의 잔여 피해가 parity/ECC보다 작았지만 실제 개발 CPU에서 정상 비용이 2% 기준을 넘었으므로 최종 후보로 승격하지 않았다.', '',
 'Flying collapse의 관측 시간과 fixed-N conditional Poisson에서 ECC net misses는 659.00과 48.25였다. 사건 수를 유지해도 몰린 시간 간격과 연속 복구 중 오류가 결과를 바꿀 수 있다. 이는 시간 압축·분기 단위 quantization·가상 위치 mark를 포함한 replay 조건의 결과이며 실제 위성 도착률이나 연속 사건의 독립성을 입증하지 않는다.', '',
 '이 표의 event targets는 같은 S* payload이다. P_TMR의 0은 payload plane 한 곳의 오류를 복구한 이 조건의 결과이며 여러 replica를 동시에 손상시키는 physical common-mode MCU를 평가한 값이 아니다. Added storage stress는 별도 CPU 결과에 있다.', '',
 'CERN은 원본 K≥2 recorded coordinate catalog를 사용한다. Source event arrival는 별도의 가정이며 K를 독립 입자 사건 수로 해석하지 않는다. 16×22 가상 grid에 footprint를 fitting/translation하고 346개 유효 site로 mapping했다. Target physical coordinates를 실측하지 않았다. Flying의 중복 보존은 기록 정책 민감도이며 중복 개수를 MCU K로 변환하지 않는다.', '',
 '모든 event schedule과 원본 hash, K 의미, mapping/time 정책은 source_robustness.lock.json과 model_robustness 원시 자료에 있다. Full-particle time×footprint joint distribution, 28nm calibration, 강한 tail 신뢰구간은 미측정이다.']
(OUT/'reports/G5_MODEL_SENSITIVITY.ko.md').write_text('\n'.join(source_text)+'\n')

# Aggregate operation vectors without converting them to silicon area/energy.
raw_primary = json.loads((OUT / 'reports/G5_CPU_HOLDOUT_V2.json').read_text())
activity_keys = ['prediction_reads', 'checks', 'word_reads', 'word_writes',
 'sidecar_reads', 'sidecar_writes', 'encode_words', 'voted_words',
 'fold_delta_xor_inputs', 'raw_delta_xor_inputs', 'path_delta_xor_inputs',
 'source_decodes', 'shadow_decodes', 'update_jobs', 'rebuild_steps',
 'rebuild_source_bits', 'rebuild_writes', 'response_hold_cycles',
 'drain_hold_cycles', 'maintenance_hold_cycles']
activity = []
for variant in variants:
 for scenario in ['zero', 'CHARM_6T']:
  rr = [r for r in raw_primary['tasks'] if r['id'] == variant and r['scenario'] == scenario]
  activity.append(dict(variant=variant, scenario=scenario, runs=len(rr),
   mean_counts={key:statistics.mean(r['seu'].get(key,0) for r in rr) for key in activity_keys},
   peak_backlog=max(r['seu'].get('max_maintenance_backlog_cycles',0) for r in rr),
   modeled_activity_not_physical_switching=True))
write(OUT/'reports/G6_ACTIVITY_VECTORS.json', dict(status='ACTUAL_MODEL_COUNTS_COST_PROXY', rows=activity,
 scope='Per-task counts for three fixed inputs, equal owner counts; each operation type kept separate. No conversion to mW/mm2.'))

def interval(metric):
 ci=metric['CI95']
 return f"{metric['mean']:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]"

text = ['# G6 결과와 하드웨어 측정 후보', '',
 'G0→G6의 소프트웨어 실행과 분석을 완료했다. 기존 corrected v2 기준선과 S*=346 bits/23 words를 유지했다. 이번 평가는 MiBench qsort·dijkstra·sha1의 새 입력을 사용한 실제 gem5 O3 실행이며, SPEC CPU 점수나 실측 CPU 성능이 아니다.', '',
 '최종 검토 대상은 **'+(', '.join(recommend) if recommend else '승격 후보 없음')+'**이다. 이는 하드웨어 비용을 측정할 후보 선정이다. RTL·Cadence·SPICE·TCAD 및 실제 PPA 측정은 수행하지 않았다.', '',
 '|CHARM 6T 반복 주입|정상 overhead|오류 포함 총 slowdown|순이득 pp [95% CI]|',
 '|---|---:|---:|---:|']
for s in primary['summary']:
 if s['scenario'] != 'CHARM_6T': continue
 m=s['metrics']
 text.append(f"|{s['variant']}|{m['clean_overhead_pct']['mean']:.4f}%|{m['total_slowdown_pct']['mean']:.4f}%|{interval(m['net_pp'])}|")
text += ['', '각 입력·조건마다 독립 owner 10개를 사용했다. 사건율 10⁻⁶ events/cycle은 선언한 stress 가정이다. CHARM의 K1:K2=205:9를 사용하지만 대상 회로의 물리적 SEU rate로 보정한 값은 아니다. 프로그램 세 개를 동일 가중했다.', '',
 '**통계 정의:** A/B/C/D는 무보호 정상/오류, 해당 보호법 정상/오류의 cycles이다. 순이득은 B−D, 표의 pp는 100(B−D)/A이다. 정상 비용과 잔여 오류 손실을 함께 차감한다. 각 고정 입력 내부의 matched owner를 resample한 bootstrap CI이며, 새로운 workload 모집단에 대한 CI가 아니다.', '',
 '|단일 SBU|오류 포함 총 slowdown|순이득 pp [95% CI]|',
 '|---|---:|---:|']
for s in primary['summary']:
 if s['scenario']=='SBU_SINGLE':
  text.append(f"|{s['variant']}|{s['metrics']['total_slowdown_pct']['mean']:.4f}%|{interval(s['metrics']['net_pp'])}|")
text += ['', '|조건|방법|owner pairs|Φ mismatch 실행|helpful/zero|task 추가 cycles p95|검출 지연 p95 cycles / censor|', '|---|---|---:|---:|---:|---:|---|']
for row in primary['summary']:
 delay=row['detector_delay_p95']
 delay_text=f"{delay:.3f} / {row['detector_censored']}" if delay is not None else f"미추정 / {row['detector_censored']}"
 text.append(f"|{row['scenario']}|{row['variant']}|{row['valid_pairs']}|{row['phi_mismatch_runs']}|{row['helpful_task_faults']}/{row['zero_task_loss']}|{row['task_extra_cycles_p95']:.1f}|{delay_text}|")
text += ['', 'Task 추가 cycles는 D−C이며 음수도 유지했다. 반복 주입의 검출 지연은 사건별 attribution을 수행하지 않아 미추정으로 표시했다. P0는 detector가 없으므로 SBU 30개가 미관측이다. 새 CPU 평가의 독립 fault-owner cluster는 60개(3 inputs × 2 scenarios × 10)이며, 같은 owner의 여러 보호법 실행을 독립 표본으로 합치지 않았다. 정상 baseline 15회는 결정적 참조이다.']

text += ['', '|새 입력|방법|정상 cycles|정상 IPC|정상 overhead|', '|---|---|---:|---:|---:|']
for r in raw_primary['tasks']:
 if r['scenario']=='zero':
  overhead=100*(r['cycles']/baseline[r['program']]['cycles']-1)
  text.append(f"|{r['program']}|{r['id']}|{r['cycles']:,}|{r['IPC']:.6f}|{overhead:.4f}%|")
text += ['', '|전체 논리 비트 노출: 동일 per-bit 가정|순이득 pp 평균|owner pairs|', '|---|---:|---:|']
for variant in variants:
 rr=[r for r in whole_pairs if r['variant']==variant]
 text.append(f"|{variant}|{statistics.mean(r['net_pp'] for r in rr):+.4f}|{len(rr)}|")
text += ['', '전체 논리 비트 시험은 입력별 3 owners의 탐색용 결과다. 사건율은 기준선 전체 10⁻⁶/cycle에 대응하는 per-bit 가정이고 S* 346 bits에 집중 주입한 주 실험과 분포가 다르다. 위 순이득이 음수라면 그 노출 조건에서 정상 비용을 상쇄하지 못했다는 뜻이다. Added storage의 directed 시험과 합산하지 않았다.']
text += ['', '**개발에서 탈락한 조건:** H1(source SECDED + fold parity/rebuild)의 정상 overhead는 qsort 18.6364%, dijkstra 5.0203%였다. 보호된 실제 commit shadow 161 bits와 scan/FSM, 갱신 비용을 포함한 결과다. N1에 매 갱신 1-cycle service를 추가한 U1 조건도 각각 5.4403%, 2.0934%로 사전 2% 기준을 넘었다. 이 두 조건은 새 입력을 보고 재조정하지 않았다.', '',
 '**N1의 핵심 조건:** k=64 history 갱신마다 다음 예측 경계에서 검사하고, parity는 forward/inverse/corrected 갱신의 incoming/outgoing bit로 유지한다. 검출 시 epoch/drain과 130개 실제 control update의 relearn을 수행한다. 현재 이득은 정상 유지 연산이 기존 갱신 단계 안에 들어가는 U0 가정에 의존한다. 실제 clock·port·routing 검증이 실패하면 이 이득을 그대로 주장할 수 없다.', '',
 '**P_ECC를 남긴 이유:** even parity 오류와 군집 오류에 대한 대비를 실제 회로 비용으로 비교할 가치가 있다. 모든 조건에서 CPU 성능이 우월하거나 정상 2% 기준을 통과했다고 추천하는 것은 아니다. 네 기준선은 모두 유지한다.', '',
 '|후보/기준선|추가 logical bits|최대 정상 overhead|최대 조건 평균 잔여손실 pp|Pareto 지배 방법|',
 '|---|---:|---:|---:|---|']
for r in front:
 text.append(f"|{r['id']}|{r['extra_bits']}|{r['worst_clean_pct']:.4f}%|{r['worst_group_residual_loss_pp']:.4f}|{', '.join(r['point_dominated_by']) or '없음'}|")
text += ['', '위 Pareto는 측정한 소프트웨어 point vector이다. 활동량은 G6_ACTIVITY_VECTORS.json에 read/write/check/encode/vote/XOR/scan 별로 보존했다. Logical bits와 연산 횟수는 실제 면적·에너지가 아니다. G6_PARETO.json의 budget별 feasible 집합은 관측한 조건 평균 기준이며, 물리적 최적성이나 tail 보장이 아니다.', '',
 '**실행 증거와 실패:**', '',
 '- G1: main causal replay 1,632회와 pilot 800회; oracle 복구는 별도 진단으로만 사용했다. Raw history 복구 후에도 소량의 table 피해가 남았지만, learning freeze가 피해를 늘린 사례가 있으므로 learning이 항상 손상을 증폭한다고 결론내리지 않았다.',
 '- G3: correctness 1,089개 및 추가 fault/property 419개를 통과했다. 최종 C++ 개발 screen 418회와 same-k ablation 38회를 실행했다. Ablation의 관측 38개에서 incremental parity와 full-word delta의 보호 결과는 동일했다. 구현 비용의 실측 우위를 뜻하지 않는다.',
 '- G4: 수정된 timing/resource gate 24개와 개발 CPU 42회가 통과했다. 초기 token queue 모델의 정상 실행 4개 실패도 source/binary/log와 함께 보존했다.',
 f"- G5: 새 입력 CPU {raw_primary['completed']}회, source-pattern C++ {source['completed']}회, 전체·추가 비트 CPU stress {extra['completed']}회를 실행했다. 프로그램 출력은 native 결과와 검증했다.", '',
 'G4의 자원 수정은 12-bit bounded work descriptor(최대 4,095 service cycles)이다. 모든 요청 갱신 work를 비용에 반영하고 응답을 기다리게 했다. 다만 기능 상태 갱신은 issue-atomic이며 scalar debt로 응답을 지연하는 모델이다. 물리적 직렬 RMW 중간 상태와 FI 시각이 정확히 같다는 보장은 아직 없다. Checker도 historical C1 serial 응답 모델이며, II=1 background pipeline 구현으로 부르지 않는다.', '',
 '**오류 모델과 제한:** CERN의 K≥2 recorded footprint는 contiguous/interleaved 가상 mapping 두 가지로 평가했다. Flying Laptop은 2,129 raw rows/2,055 distinct/74 duplicate extras를 재확인하고, 중복 유지/제거와 관측/순열/조건부 Poisson 시간 replay를 분리했다. 중복을 MCU로 취급하지 않았다. Source별 2 owners/input의 C++ 결과는 sensitivity point이고 CPU cycles 결과와 섞지 않았다.', '',
 '전체 논리 저장소 stress는 같은 per-bit rate 가정으로 추가 bit 수와 실제 실행 시간의 노출을 반영했다. 최대 population의 사건을 공통 mark로 생성하고 각 방법에 존재하는 site만 유지했다. 추가 저장소만 겨냥한 단일 오류는 취약성 진단이며 전체 평균이나 주 성능 CI에 합치지 않았다. 고정 total incident rate의 별도 whole-population 비교는 이번 새 CPU 캠페인에 포함하지 않았다.', '',
 '무영향·helpful·no-event·최종 Φ mismatch·state divergence·검출 censoring을 보존했다. 10 owners/input으로 p99/WCET를 보장하지 않는다. 단일 사건의 검사 지연 분위수와 반복 주입의 task 피해 분위수는 각각 표본 요약이며, 반복 주입에서 사건별 피해를 분리해 인과적으로 추정한 것은 아니다. 최종 프로그램 정답이 맞아도 predictor 상태가 완전히 복구됐다고 단정하지 않는다. SECDED 3+ miscorrection, even parity, TMR common mode, controller corruption에는 coverage 한계가 있다.', '',
 '기존 BI/checkpoint/CPU queue/BTB/RAS/architectural state/aging/RNG 및 simulator absolute timing tag는 노출 범위에서 제외했다. CPU 전체나 실제 실리콘의 radiation robustness, mission FIT, 28nm 보정 rate는 주장하지 않는다.', '',
 '**후속 하드웨어 계약:** N1의 outgoing-history taps와 parity 유지 경로, rollback burst, check/read/write ports, clock budget을 우선 검증한다. ECC는 23개 shortened codeword와 source 130/16-bit encode/decode를 같은 인터페이스·PDK·library·PVT·clock·load에서 비교해야 한다. H1의 재구성을 다시 검토한다면 실제 commit shadow, 16-bit scan/step, 21 fold accumulators, 1 fold write/step 및 drain을 모두 포함한다. 실제 delay/II/energy를 얻은 뒤 O3 모델에 다시 반영한다.', '',
 'CLEAR의 cross-layer physical cost 연구와 기존 TAGE history cohesion 연구가 있으므로 hybrid/parity/주기 검사 자체의 최초성을 주장하지 않는다. 이번 근거는 상태 역할·지속 피해·speculative 복구와 비용이 유효 보호 조건을 바꾸는지에 있다. 원문 검토 범위는 literature/REVIEW_ADDENDUM.ko.md에 기록했다.', '',
 '재현 자료: 각 gate JSON, 실행 명령·원시 log·schedule·stats·출력 hash, source/config/input/binary lock, G6_HARDWARE_CONTRACT.json과 review ZIP. 기존 증거 보존과 마지막 hash/budget 감사는 G6_FINAL_AUDIT.json에 기록한다.']
(OUT/'reports/G6_HARDWARE_CANDIDATE_SHORTLIST.ko.md').write_text('\n'.join(text)+'\n')

figdir=OUT/'reports/figures';figdir.mkdir(exist_ok=True);fig,axes=plt.subplots(1,2,figsize=(10,3.8));labels=variants;xx=np.arange(len(labels));repeat={s['variant']:s for s in primary['summary'] if s['scenario']=='CHARM_6T'}
for offset,metric,label in [(-.18,'clean_overhead_pct','Clean overhead'),(.18,'total_slowdown_pct','Fault total slowdown')]:
 vals=[repeat[v]['metrics'][metric]['mean'] for v in labels];axes[0].bar(xx+offset,vals,width=.36,label=label)
axes[0].set_xticks(xx,labels,rotation=25);axes[0].set_ylabel('Measured O3 cycles vs P0 clean (%)');axes[0].legend(fontsize=8);axes[0].axhline(0,color='black',linewidth=.7)
vals=[repeat[v]['metrics']['net_pp']['mean'] for v in labels];cis=[repeat[v]['metrics']['net_pp']['CI95'] for v in labels];axes[1].errorbar(xx,vals,yerr=np.array([[v-ci[0] for v,ci in zip(vals,cis)],[ci[1]-v for v,ci in zip(vals,cis)]]),fmt='o',capsize=4);axes[1].set_xticks(xx,labels,rotation=25);axes[1].set_ylabel('(B-D)/A: percentage points');axes[1].axhline(0,color='black',linewidth=.7);fig.suptitle('Three fresh fixed inputs; 10 paired owners/input; CHARM 6T stress');fig.tight_layout();fig.savefig(figdir/'heldout_cpu.png',dpi=180);fig.savefig(figdir/'heldout_cpu.pdf');plt.close(fig)
print('G6 rendered candidates',recommend)
