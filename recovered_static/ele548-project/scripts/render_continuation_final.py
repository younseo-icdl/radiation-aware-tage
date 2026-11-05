"""G6 final report from audited actual cycles; no PPA fabrication."""
import json,csv,statistics,math
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
text=['# G6 소프트웨어 결과와 하드웨어 측정 후보\n','G0→G5 실제 실행 증거를 기준으로 후보를 동결했다. RTL/Cadence/SPICE/TCAD는 실행하지 않았다. 보호된 source로 fold를 재구성할 수 있다는 사실만으로 낮은 CPU 비용을 보장하지 않는다. Source shadow·검증·복구·자원 처리량을 함께 계산했다.\n','|조건|방법|정상 overhead 평균|오류 총 slowdown 평균|순이득 pp 및95%CI|\n|---|---|---:|---:|---|']
for s in primary['summary']:
 if s['scenario']!='CHARM_6T':continue
 m=s['metrics'];ci=m['net_pp']['CI95'];text.append(f"|fresh3inputs,CHARM6T1e-6/cycle|{s['variant']}|{m['clean_overhead_pct']['mean']:.4f}%|{m['total_slowdown_pct']['mean']:.4f}%|{m['net_pp']['mean']:+.4f} [{ci[0]:+.4f},{ci[1]:+.4f}]|")
text+=['\nA/B/C/D는 무보호 정상/오류와 해당 보호법 정상/오류의 실제cycles이다. 순이득은B−D이며 한 owner의100kbranches를 독립samples로 세지 않는다. 각 fixed input/program 내부의 paired owner를 resample하고 program평균을 동일가중했다. 새 program 모집단의CI나WCET보장이 아니다.','\n하드웨어 **측정 후보**: '+(', '.join(recommend) if recommend else '현재 조건에서 승격할 후보 없음')+'. P_ECC는 even/clustered 오류에 대비한 대비 후보이며 모든 조건의winner라고 추천하지 않는다. 후보별개별 program/model 수치와 CI는CPU_HOLDOUT_SUMMARY.json에 있다.','\n초기 tokenQ16은4/14clean실행에서 실패했다. Source/binary/log를 보존했고12bitbounded4095cycle work descriptor로 수정했다. Synthetic24gate 뒤 실제program gate를 통과했다. 모든 요청 work와 latency는 유지했다. Scalar maintenance는 issue-atomic update/response-wait abstraction이며 physicalserializedRMW의FI위치/중간timing과 같다고 주장하지 않는다.','\nCERN의recordedK≥2spatial catalog와Flying2129/2055duplicate정책·관측/셔플/조건부Poisson시간replay는 별도288C++실험이다. Time/footprint joint distribution과targetphysicalrate/layout은 미측정이다. Whole-per-bit와addedbit CPUstress는 별도결과이며 주 실험의S*조건부평균과 섞지 않는다.','\n실패·noevent·helpful·zero·latentφ mismatch와detectorcensoring을 모두 원시자료/summary에 보존했다. SECDed3+mis-correction,evenparity,TMRcommonmode,controlcursor손상은 보장밖이며프로그램 정답 검사만으로예측상태가정확하다고 결론내리지 않는다.','\n추가bits와연산량은costproxy이고actualarea/energy가아니다. Same-stageU0와C1/R4는가정이다. NormalmaintenanceU1으로이득이바뀌는지design수치에서평가했다. Hardware후속단계에서동일PDK조건의actualdelay/II/ports/energy를확인하고CPU에다시반영해야한다.','\n참신성은simplehybrid/parity/periodic의최초성으로주장하지않는다. CLEAR및TAGEhistorycohesion선행연구와구분하고,역할·지속피해·speculativerecovery·비용으로유효조건을설명한다.','\n재현/원시증거: G0_AUDIT/G0_DATASET_AUDIT,CAUSAL_CLAIMS,G3_CPP_SCREEN_FINAL,G4_CPU_GATE_V2,G4_CPU_DESIGN_V2,G5_CPU_HOLDOUT_V2,G5_SOURCE_ROBUSTNESS,G5_CPU_EXPOSURE_ROBUSTNESS. Source/config/event/input/binaryhash는각run과lock에있다.']
(OUT/'reports/G6_HARDWARE_CANDIDATE_SHORTLIST.ko.md').write_text('\n'.join(text)+'\n')
figdir=OUT/'reports/figures';figdir.mkdir(exist_ok=True);fig,axes=plt.subplots(1,2,figsize=(10,3.8));labels=variants;xx=np.arange(len(labels));repeat={s['variant']:s for s in primary['summary'] if s['scenario']=='CHARM_6T'}
for offset,metric,label in [(-.18,'clean_overhead_pct','Clean overhead'),(.18,'total_slowdown_pct','Fault total slowdown')]:
 vals=[repeat[v]['metrics'][metric]['mean'] for v in labels];axes[0].bar(xx+offset,vals,width=.36,label=label)
axes[0].set_xticks(xx,labels,rotation=25);axes[0].set_ylabel('Measured O3 cycles vs P0 clean (%)');axes[0].legend(fontsize=8);axes[0].axhline(0,color='black',linewidth=.7)
vals=[repeat[v]['metrics']['net_pp']['mean'] for v in labels];cis=[repeat[v]['metrics']['net_pp']['CI95'] for v in labels];axes[1].errorbar(xx,vals,yerr=np.array([[v-ci[0] for v,ci in zip(vals,cis)],[ci[1]-v for v,ci in zip(vals,cis)]]),fmt='o',capsize=4);axes[1].set_xticks(xx,labels,rotation=25);axes[1].set_ylabel('(B-D)/A: percentage points');axes[1].axhline(0,color='black',linewidth=.7);fig.suptitle('Fresh fixed3inputs;10pairedowners/input; CHAR M6T declaredstress rate');fig.tight_layout();fig.savefig(figdir/'heldout_cpu.png',dpi=180);fig.savefig(figdir/'heldout_cpu.pdf');plt.close(fig)
print('G6 rendered candidates',recommend)
