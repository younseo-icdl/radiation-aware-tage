import csv,json,statistics,collections
from continuation_common import *
x=json.loads((OUT/'reports/G1_MAIN.json').read_text());assert x['status']=='PASS'
rows=[]
for t in x['tasks']:
 assert sha(ROOT/t['output'])==t['CSV_sha256']
 rows+=list(csv.DictReader((ROOT/t['output']).open()))
summary=[]
for role in ['raw_direction','path','index_fold','tag_fold']:
 for l in [1,0]:
  for arm in ['NONE','H_ONLY','F_ONLY','HF','T_ONLY','HFT','HF_R','FULL']:
   for delay in [0,128]:
    v=[r for r in rows if r['stratum']==role and int(r['learning'])==l and r['arm']==arm and int(r['delay'])==delay]
    if not v:continue
    summary.append(dict(stratum=role,learning=bool(l),arm=arm,delay=delay,owners=len(v),mean_net=statistics.mean(int(r['net']) for r in v),mean_post_net=statistics.mean(int(r['post_net']) for r in v),mean_F_diff=statistics.mean(int(r['F_diff']) for r in v),mean_T_diff=statistics.mean(int(r['T_diff']) for r in v)))
assert all(r['R_diff']=='0' and r['draws_equal']=='1' for r in rows)
assert all(r['post_net']=='0' and all(r[k]=='0' for k in ['H_diff','P_diff','F_diff','T_diff','C_diff','R_diff']) for r in rows if r['arm']=='FULL')
report=dict(status='PASS_ORACLE_DIAGNOSTIC_CAUSAL_ONLY',main_sha256=sha(OUT/'reports/G1_MAIN.json'),rows=len(rows),owners=96,summary=summary,predictor_rng='Original offline adapter consumes one draw per control. All R states match; HF_R cannot explain fixed-stream damage.',limitations=['Golden interventions are not deployable protection.','96 equal-stratum events on2historical design inputs; not radiation-weighted sensitivity.','Partial arms interact; differences are not additive causal contribution percentages.','No learning freezes all conditional training/allocation/aging in both models, but retains RNG draws and history updates.','CPU speculation/cache timing causal interventions not performed.'])
write(OUT/'reports/CAUSAL_CLAIMS.json',report)
s=['# G1 원인 분해 — ORACLE_DIAGNOSTIC\n','32 base owners/800 replay/10k pilot와 96 owners/1632 replay/100k main을 실제 실행했다. 지연 단위는 모든 control-history transition이다. FULL 개입 뒤 predictor 상태와 예측은 정확히 일치했고 SHAM은 NONE와 같았다. 기존 TAGE 알고리즘은 변경하지 않았다.\n','|역할|자연회복 net|HF @128 이후 net|HFT @128 이후 net|학습동결 자연회복 net|\n|---|---:|---:|---:|---:|']
for role in ['raw_direction','path','index_fold','tag_fold']:
 def value(arm,delay,l):return next(v['mean_post_net'] if arm!='NONE' else v['mean_net'] for v in summary if v['stratum']==role and v['arm']==arm and v['delay']==delay and v['learning']==l)
 s.append(f"|{role}|{value('NONE',0,True):.3f}|{value('HF',128,True):.3f}|{value('HFT',128,True):.3f}|{value('NONE',0,False):.3f}|")
s+=['\nraw/path overwrite 자체는 fold 상태 복원을 보장하지 않는다. 실제 수치는 위 paired intervention이며, HF와 HFT 차이로 잔여 학습 피해를 관찰했다. lookup/hash 오류와 학습 증폭은 상호작용하므로 기여율을 합산하지 않는다. 이 결과를 근거로 incremental maintenance와 검증된 source 재구성을 비교 후보로 만든다.','\nRNG는 이 replay에서 control마다 정확히 한 번 호출된다. 모든 arm의 draw-count와 상태가 같다. gem5의 실행시간/다른 speculative 경로에서 생기는 RNG 차이와 혼동하지 않는다.','\n재현: `.venv/bin/python scripts/run_continuation_causal.py --phase pilot`, 이어서 `--phase main`; 원자료 `causal_main/*.csv`, checkpoint별 H/P/F/T/C/R 차이와 harm/help 모두 유지한다. CPU 인과 oracle 실험은 하지 않았다.']
(OUT/'reports/G1_CAUSAL_REPORT.ko.md').write_text('\n'.join(s)+'\n')
decision('G1','Source shift-out alone may leave fold-mediated long-lived damage.',['G1_CAUSAL_REPORT.ko.md','CAUSAL_CLAIMS.json'],'FULL/SHAM gates PASS; all fixed-stream RNG states equal.','G2 shortlist N1 incremental bounded ED and source-ECC checked rebuild; retain reverse allocation control.')
print('\n'.join(s[:8]))
