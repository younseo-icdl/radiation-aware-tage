"""Fail-closed clean identity alignment and SHAM scheduling intervention."""
import csv
from postv3_common import *

rows=json.loads((OUT/'reports/CLEAN.json').read_text())['tasks']
programs=['qsort_small','dijkstra_small','sha1']
summary=[];lines=['# Clean baseline audit','',
 '새 실행은 corrected C에서 분리한 producer다. SHAM_WAIT는 P0에 자체 update counter 기준 k64의 검사 응답 대기만 적용한 clean timing 진단이며, detector·복구·parity 유지가 없다. 보호 성과에 포함하지 않는다.', '',
 '|프로그램|P0_FINITE cycles|N1 cycles|P3 cycles|SHAM_WAIT cycles|N1 clean delta (%)|',
 '|---|---:|---:|---:|---:|---:|']
for program in programs:
    selected={t['id']:t for t in rows if t['program']==program};a=selected['P0']['cycles']
    lines.append(f"|{program}|{a}|{selected['N1']['cycles']}|{selected['P_3STAGE']['cycles']}|{selected['SHAM_WAIT']['cycles']}|{100*(selected['N1']['cycles']-a)/a:+.4f}|")
fields=['read_history','read_table','read_index','cond_pred','hit_bank','alt_bank','rng_at_read','rng_draws_at_read']
for program in programs:
    selected={t['id']:t for t in rows if t['program']==program}
    A=selected['P0']['cycles']
    for v in ['P_ALL130','P_3STAGE','P_2_EARLY','P_2_LATE']:
        assert selected[v]['cycles']==selected['N1']['cycles'],'GROUPED_CLEAN_TIMING_CHANGED'
    for v in ['P0','N1','P_3STAGE','SHAM_WAIT']:
        assert selected[v]['seu']['detected']==0,'CLEAN_DETECTOR_TRIGGERED'
        assert selected[v]['seu']['applied_events']==0
    logs={}
    for v in ['P0','N1','P_3STAGE','SHAM_WAIT']:
        logs[v]=list(csv.DictReader((ROOT/selected[v]['output']/'committed_audit.csv').open()))
        assert logs[v] and any(int(t['prediction_id']) for t in logs[v]),'NO_COMMITTED_PROVENANCE'
        assert selected[v]['seu']['audit_identity_hash']==selected['P0']['seu']['audit_identity_hash'],'COMMITTED_IDENTITY_CHANGED'
        assert selected[v]['seu']['audit_insts']==selected[v]['instructions']
    length=min(len(x) for x in logs.values())
    for n in range(length):
        for v in logs:
            for key in ['control_ordinal','op_ordinal','inst_ordinal','pc','micro_pc','identity_prefix']:
                assert logs[v][n][key]==logs['P0'][n][key],('DYNAMIC_ALIGNMENT_FAILED',program,n,key)
    first={}
    first_by_field={}
    training={v:{r['prediction_id']:r for r in csv.DictReader((ROOT/selected[v]['output']/'committed_audit.csv.training.csv').open())} for v in logs}
    training_first={}
    for v in ['N1','P_3STAGE','SHAM_WAIT']:
        first_by_field[v]={}
        for a,b in zip(logs['P0'],logs[v]):
            for field in fields:
                if field not in first_by_field[v] and a[field]!=b[field]:
                    first_by_field[v][field]=dict(control_ordinal=int(a['control_ordinal']),
                        inst_ordinal=int(a['inst_ordinal']),pc=int(a['pc']),P0=a[field],comparison=b[field],
                        P0_read_tick=int(a['read_tick']),comparison_read_tick=int(b['read_tick']))
        for a,b in zip(logs['P0'],logs[v]):
            changed=[f for f in fields if a[f]!=b[f]]
            if changed:
                first[v]=dict(control_ordinal=int(a['control_ordinal']),op_ordinal=int(a['op_ordinal']),
                    inst_ordinal=int(a['inst_ordinal']),pc=int(a['pc']),changed_fields=changed,P0=a,comparison=b)
                break
        for a,b in zip(logs['P0'],logs[v]):
            if a['prediction_id']=='0' or b['prediction_id']=='0':continue
            x=training['P0'].get(a['prediction_id']);y=training[v].get(b['prediction_id'])
            if not x or not y:continue
            changed=[f for f in ['nrand','rng_hash','history_before','history_after','fallback','epoch'] if x[f]!=y[f]]
            if changed:
                training_first[v]=dict(control_ordinal=int(a['control_ordinal']),pc=int(a['pc']),changed_fields=changed,P0=x,comparison=y)
                break
    sham=selected['SHAM_WAIT'];n1=selected['N1']
    assert n1['seu']['predictor_rng_hash']==selected['P0']['seu']['predictor_rng_hash']
    assert n1['seu']['predictor_rng_draws']==selected['P0']['seu']['predictor_rng_draws']
    exact=(sham['cycles']==n1['cycles'] and all(sham['seu'][k]==n1['seu'][k] for k in
        ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']))
    assert exact,'SHAM_DOES_NOT_EXPLAIN_N1_CLEAN_NEED_MORE_DIAGNOSTIC'
    for a,b in zip(logs['SHAM_WAIT'],logs['N1']):
        assert all(a[f]==b[f] for f in fields+['read_tick','tick']),('SHAM_LOGICAL_READ_DIFF',program)
    summary.append(dict(program=program,A=A,N1=n1['cycles'],P3=selected['P_3STAGE']['cycles'],SHAM=sham['cycles'],
        clean_delta_pct=100*(n1['cycles']-A)/A,SHAM_reproduces_N1=True,
        full_committed_identity_hash=selected['P0']['seu']['audit_identity_hash'],aligned_branch_prefix=length,
        first_aligned_divergence=first,first_by_field=first_by_field,first_aligned_training_divergence=training_first))
    if 'N1' in first:
        f=first['N1'];lines+=['',f"{program}: 동일 committed control ordinal {f['control_ordinal']}, instruction ordinal {f['inst_ordinal']}, PC {hex(f['pc'])}에서 처음 {', '.join(f['changed_fields'])}가 달라졌다. P0와 N1의 read tick은 각각 {f['P0']['read_tick']}/{f['comparison']['read_tick']}, raw hot queue snapshot은 {f['P0']['hot_at_read']}/{f['comparison']['hot_at_read']}다."]
    if 'N1' in training_first:
        f=training_first['N1'];lines+=['',f"정렬된 training의 최초 상태/RNG 차이는 control ordinal {f['control_ordinal']}, PC {hex(f['pc'])}의 {', '.join(f['changed_fields'])}다. lookup 시 저장한 observation ID로 training record를 연결했으며 speculative seqNum으로 대조하지 않았다."]
    lines+=['','|최초 차이 field|committed control ordinal|PC|','|---|---:|---|']
    for field,f in first_by_field['N1'].items():lines.append(f"|{field}|{f['control_ordinal']}|{hex(f['pc'])}|")
lines+=['','세 프로그램에서 SHAM_WAIT가 N1의 cycles·canonical predictor state·RNG 및 정렬된 lookup 결과를 재현했다. 이 통제에서 clean 차이는 주기적인 응답 대기가 speculative update/commit과 predictor read의 상대 시점을 바꾸는 것으로 설명된다. 오류 검출/복구 이득으로 집계하지 않는다. SHAM은 N1의 parity 갱신을 생략하므로 같은 물리 회로가 아니다. 자체 counter로 검사 예약을 하며 사전에 추출한 golden timing을 재생하지 않는다.',
    '', '최초 차이 표는 기록한 field의 최초 차이다. hit_bank/alt_bank는 lookup의 matching-bank 후보이며 전체 provider 선택 enum을 별도로 기록한 것은 아니다. read_table은 접근 후보 rows/bimodal prediction의 fingerprint이며 모든 전역 predictor metadata의 완전한 snapshot은 아니다. 이 한계를 포함해 SHAM의 전체 종료 state/hash·cycles 재현을 별도로 검증했다.',
    '', 'RNG_at_read의 차이는 그 lookup까지 완료된 commit/update 진행량의 관측값이다. TAGE lookup에서 새 random 값을 뽑았다는 뜻이 아니다. P0/N1의 전체 committed update random draw 수와 hash는 동일했다. RNG namespace 충돌이나 다른 seed를 clean 차이의 원인으로 돌리지 않는다. 동일 committed 명령이라도 wrong-path speculative sequence와 현재 공개된 history/training 상태는 달라질 수 있다.',
    '', 'P0_IMMEDIATE와의 비교는 별도 reference다. A/B/C/D 분모는 P0_FINITE로 유지한다. whole-storage의 이전 순이득과 clean 차이를 분리한 값은 reports/OLD_COUNTER_REAUDIT.json에 있다. Difference-of-differences도 정의된 비교 통계이며 실행 경로 상호작용을 제거한 순수 물리 인과량은 아니다.',
    '', '동적 identity는 실제 ROB retirement에서 PC·microPC·macro boundary/control flag를 순서대로 누적한 전체 hash와 branch별 prefix로 검증했다. 비교는 같은 committed ordinal이며, speculative seqNum이나 wall-clock tick을 동일 동적 명령으로 간주하지 않았다. ELF/input/native stdout/정상 종료와 instruction count도 별도 검증했다.']
write(OUT/'reports/G0_ACCEPTANCE.json',dict(status='PASS',programs=summary,
    clean_timing_diagnostic_excluded_from_protection=True,resource='SHARED2 L1 II1 hot64',
    caveat='latest-visible completion-publication history endpoint; not a physical optimality or universal positive effect'))
(OUT/'CLEAN_BASELINE_AUDIT.ko.md').write_text('\n'.join(lines)+'\n')
print('G0 PASS: aligned committed identity and SHAM clean timing explained')
