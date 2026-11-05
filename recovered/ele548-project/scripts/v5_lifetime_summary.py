"""Retained versus reset causal evidence; no lifetime extrapolation past censoring."""
from v5_common import ROOT,write
import csv,json,statistics,collections
F=ROOT/'rate_state_v5/results';F.mkdir(exist_ok=True);R=ROOT/'rate_state_v5/runtime'
allrows=[]
for phase in ['CPP_PERSISTENT','CPP_PERSISTENT_COLD']:
    report=json.loads((R/'reports'/(phase+'.json')).read_text());assert report['status']=='PASS'
    for task in report['tasks']:
        for row in csv.DictReader((ROOT/task['result']).open()):
            allrows.append(dict(phase=phase,trace=task['name'],**{k:int(v) if k!='mode' else v for k,v in row.items()}))
keys=list(allrows[0])
with (F/'PERSISTENT_CPP_RAW.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(allrows)
# A case emits one row per task. Collapse correlated task rows BEFORE summarizing.
groups=collections.defaultdict(list)
for r in allrows:groups[tuple(r[k] for k in ['phase','trace','mode','owner','reset_each_task','repetitions'])].append(r)
cases=[]
for key,rs in groups.items():
    last=max(rs,key=lambda r:r['task']);assert len(rs)==key[-1]
    cases.append(dict(zip(['phase','trace','mode','owner','reset_each_task','repetitions'],key),
      total_net=sum(r['net'] for r in rs),final_task_net=last['net'],
      final_hash_mismatch=last['hash_terminal_mismatch'],final_table_mismatch=last['table_terminal_mismatch']))
with (F/'PERSISTENT_CPP_CASES.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(cases[0]));w.writeheader();w.writerows(cases)
summary=[]
for phase in ['CPP_PERSISTENT','CPP_PERSISTENT_COLD']:
 for mode in ['recurrent','direct']:
  for reset in [0,1]:
   for repetitions in [2,8,32]:
    rs=[r for r in cases if r['phase']==phase and r['mode']==mode and r['reset_each_task']==reset and r['repetitions']==repetitions]
    summary.append(dict(phase=phase,mode=mode,reset_each_task=reset,R=repetitions,cases=len(rs),
      mean_total_net=statistics.mean(r['total_net'] for r in rs),mean_final_task_net=statistics.mean(r['final_task_net'] for r in rs),
      final_hash_mismatch_fraction=statistics.mean(bool(r['final_hash_mismatch']) for r in rs),
      final_table_mismatch_entries=statistics.mean(r['final_table_mismatch'] for r in rs)))
with (F/'PERSISTENT_CPP_SUMMARY.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
base=(R/'STATE_LIFETIME_ANALYSIS.ko.md').read_text().replace('CPP_PERSISTENT.csv','reports/CPP_PERSISTENT/*.csv')
extra='\n\n## 반복 상태의 실제 trace 진단\n\n'
extra+='IMPLEMENTED/TESTED RESULT: warm-snapshot reset576사례와 별도 canonical cold predictor reset576사례를 구분했다. 각 사례의2/8/32 task 행을 먼저 합산했으며 반복 task를 독립 표본 수로 세지 않았다. trace6개×owner8개는 같은 R 간 상관을 유지한다. 아래는6trace 동일가중 요약이며 CPU 성능은 PERSISTENT_CPU_DAMAGE.csv를 별도로 읽는다.\n\n'
extra+='|reset 종류|표현|task마다 reset|R|평균 누적 추가 오예측|마지막 task 추가 오예측|마지막 hash 차이 비율|\n|---|---|---:|---:|---:|---:|---:|\n'
for r in summary:
 if r['R']!=32:continue
 extra+=f"|{r['phase']}|{r['mode']}|{r['reset_each_task']}|32|{r['mean_total_net']:.3f}|{r['mean_final_task_net']:.3f}|{r['final_hash_mismatch_fraction']:.3f}|\n"
extra+='\nASSUMPTION/LIMIT: 같은 실제 기록 구간을 반복한 인과 진단이다. 새로운 장기 workload나 임무를 관측한 결과가 아니다. warm snapshot은 golden diagnostic이며 production 복구에 사용하지 않는다. cold reset은 source뿐 아니라 table도 초기화한다. CPU의 cold 비교는 R1 실행을 합한 파생값이라 CPU/cache/allocator도 reset한다. reset 비용 없는 구현 성과로 발표하지 않는다.\n'
extra+='\n추가 구분: hashes()는21개의 direction-history fold를 비교한다. PC/path 혼합을 포함한 전체 index/tag 동일성이나 전체 predictor 상태 회복과 동일하지 않다. Path 오류의 이 열을 전체 hash 회복으로 해석하면 안 된다. short32는min2/max32의 기존 geometric lengths를 새로 만들므로 원래5/130 history 비율 보존 대조가 아니다. 동일 table/provider/training 대조이다.\n'
(F/'STATE_LIFETIME_ANALYSIS.ko.md').write_text(base+extra)
print('PASS task rows grouped into',len(cases),'correlated cases;',len(summary),'descriptive strata')
