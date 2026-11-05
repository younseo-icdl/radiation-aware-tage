"""Measured replay data only; conditional owners stay grouped by input and trace."""
from v5_common import *
import csv,statistics
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

reports={phase:json.loads((OUT/f'reports/CPP_{phase}.json').read_text()) for phase in ['development','refinement','extended']}
summary=[];clean=[];lifetimes=[]
for phase,report in reports.items():
 for trial in report['tasks']:
  rows=list(csv.DictReader((ROOT/trial['result']).open()))
  if phase!='extended':clean.append(dict(trace=trial['name'],tap_budget=16 if phase=='refinement' else 8,**trial['clean']))
  for field in sorted(set(x['field'] for x in rows)):
   rs=[r for r in rows if r['field']==field];nets=np.array([int(r['net']) for r in rs]);rng=np.random.default_rng(315548888)
   means=np.mean(rng.choice(nets,size=(5000,len(nets)),replace=True),axis=1)
   summary.append(dict(phase=phase,trace=trial['name'],mode=trial['mode'],taps=16 if phase=='refinement' else 8,field=field,n=len(rs),
       mean_net=float(nets.mean()),CI_low=float(np.quantile(means,.025)),CI_high=float(np.quantile(means,.975)),
       max_net=int(nets.max()),helpful_fraction=float(np.mean(nets<0)),zero_fraction=float(np.mean(nets==0)),
       hash_terminal_mismatch_fraction=statistics.mean(int(r['hash_terminal_mismatch']) for r in rs),
       raw_terminal_mismatch_fraction=statistics.mean(int(r['raw_terminal_mismatch']) for r in rs),
       mean_table_residual_entries=statistics.mean(int(r['table_terminal_mismatch']) for r in rs),
       empirical_max_prediction_last_divergence=max(int(r['prediction_last_divergence']) for r in rs),horizon=int(rs[0]['horizon'])))
  lifetimes.extend(dict(trace=trial['name'],phase=phase,**r) for r in rows)
def csvwrite(name,rows):
 with (OUT/name).open('w') as f:
  keys=list(rows[0]);w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
csvwrite('CPP_CONDITIONAL_SUMMARY.csv',summary)
csvwrite('REPRESENTATION_TRACE_COMPARISON.csv',clean)
csvwrite('STATE_LIFETIME_RAW.csv',lifetimes)
raw=[r for r in summary if r['phase']=='development' and r['field']=='raw']
means={m:statistics.mean(x['mean_net'] for x in raw if x['mode']==m) for m in sorted(set(x['mode'] for x in raw))}
facts=dict(status='ACTUAL_CPP_RESULTS',raw_mean_net_equal_trace_weight=means,initial_replays=reports['development']['completed_replays'],
 refinement_replays=reports['refinement']['completed_replays'],extended_replays=reports['extended']['completed_replays'],
 direct_terminal_hash_mismatches=sum(int(r['hash_terminal_mismatch']) for r in lifetimes if r['phase']=='development' and r['mode']=='direct' and r['field']=='raw'),
 direct_cases=sum(r['phase']=='development' and r['mode']=='direct' and r['field']=='raw' for r in lifetimes),
 caution='Last observed divergence is not guaranteed recovery. Endpoints still mismatched are right censored. Conditional branch ordinal is not physical time. Source has aged out does not imply table/prediction recovery.')
write(OUT/'reports/CPP_ANALYSIS.json',facts)
text=f'''# 오류가 남는 시간: 현재 C++ 증거

TESTED RESULT: 6개 HW1 유래 실제 trace, 개발816회·16tap 단일 수정288회·관측창 연장336회. SPEC2006 유래 trace를 포함하지만 SPEC CPU 실행 점수가 아니다.

같은 raw age0..31의 조건부 SBU, 관측창100k conditional branch에서 trace 동일가중 순추가 오예측은 {means}였다. 직접 계산형은 정상 index/tag/provider/training/RNG 동일성을 통과했고, 이 raw48사례에서 종료시 hash 불일치는 {facts['direct_terminal_hash_mismatches']}건이다. 순환형 및 short-history의 종료시 잔류와300k 연장 결과는 CPP_CONDITIONAL_SUMMARY.csv에 있다.

NEW DERIVATION: 같은 branch stream, 후속 source가 정상이고 오염된 checkpoint가 재유입되지 않으면 raw bit는 최대130 history insert 뒤 창을 벗어난다. 직접 계산 hash는 그 시점 이후 같은 source에서 같은 값을 계산한다. CSV의 시간축은 conditional branch ordinal이며 unconditional insert 때문에130 history updates와 같지 않다.

이것은 전체 predictor/CPU 회복 보장이 아니다. table entry 차이와 늦은 prediction 불일치가 남을 수 있다. hash_last_divergence는 마지막 관측된 차이, hash_first_equal은 첫 재일치다. 512 이후에는128개 간격 및 지정 endpoint 표본이라 중간의 짧은 차이가 미관측일 수 있다. 종료시 차이가 있으면 horizon에서 회복했다고 쓰지 않는다. helpful/zero-impact 사건을 유지했다.

일부 history 직접조회형은 정상 정확도 비용이 있다. 8tap에서 INT trace의 손실이 컸고, 사전 허용한 수정1회로16tap을 시험했다. geometric/stratum 이외 새 tap family는 추가하지 않았다. 단순 short32 대조군은 table footprint/provider/update 규칙을 유지한다. MPKI와 회복 민감도를 별도로 읽는다.

반복 trace diagnostic은 CPP_PERSISTENT.csv 원자료에 연결된다. 과거 warm-snapshot 복귀가 포함된 진단은 비용 없는 실제 reset 설계가 아니다. native 반복 task의 CPU 성능/상태 유지는 별도 실험이다. 어떤 checkpoint restore도 무료 golden recovery로 발표하지 않는다.

PHYSICAL PENDING: raw read/fanout/XOR tree, metadata/ports/L/II의 비용과 FF 응답은 미측정이다. C++ host 실행속도는 하드웨어 지연이 아니다.
'''
(OUT/'STATE_LIFETIME_ANALYSIS.ko.md').write_text(text)
fig,ax=plt.subplots(figsize=(7,3.8));modes=['recurrent','direct','geometric','stratum','short32'];values=[means[m] for m in modes]
ax.bar(modes,values,color=['#586575','#167d8d','#829d49','#aa7f35','#928195']);ax.set_ylabel('Net additional mispredictions / event');ax.set_title('Conditional raw SBU, 100k conditional-branch window\n6 real traces, 8 owners per trace; signed losses retained');ax.axhline(0,color='black',linewidth=.5);fig.tight_layout();fig.savefig(OUT/'CPP_RAW_DAMAGE.png',dpi=180);plt.close(fig)
print(json.dumps(facts,indent=2))
