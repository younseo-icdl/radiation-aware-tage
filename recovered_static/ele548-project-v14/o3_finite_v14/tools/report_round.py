#!/usr/bin/env python3
"""Write the round report from already audited CPU results, never dispatch."""
from pathlib import Path
import json, sys
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
import run_cpu as m
BASE=m.BASE
def load(p):return json.loads(Path(p).read_text())
def main():
    data=load(BASE/'reports/CPU_ANALYSIS_FINAL.json')
    assert data['status']=='PASS_24_AUDITED_CLEAN_CPU_NOT_PROTECTION_RANKING'
    rows=data['rows'];assert len(rows)==24 and not data['failed'] and not data['pending']
    guard=m.mod('final_resources',BASE/'tools/resources_followon.py');resources=guard.snapshot()
    proposal=load(BASE/'reports/CPU_EXECUTION_PROPOSAL_B1.lock.json')
    by={(r['program'],r['source_L'],r['representation']):r for r in rows}
    lines=['# v14 finite-source 실제 O3 결과', '',
        'DONE: 새 producer에서 checksum6 + 기존 R1 프로그램18 = 24/24가 정상 종료, 정확한 출력과 프로토콜 보존식, 원시 SHA/manifest 검사를 통과했다. '
        '기존 producer·결과·실패·holdout은 보존했다. 이 단계는 P0 정상 source/pipeline 통합 검증이다.', '',
        '| 프로그램 | query L | REC cycles | Direct cycles | OW cycles | Direct vs REC | Direct IPC |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for program in ['qsort_small','dijkstra_small','sha1']:
        for L in [1,2]:
            a,b,c=[by[program,L,rep] for rep in ['recurrent','direct','overwrite']]
            lines.append(f"| {program} | {L} | {a['cycles']:,} | {b['cycles']:,} | {c['cycles']:,} | {100*(b['cycles']/a['cycles']-1):+.4f}% | {b['IPC']:.6f} |")
    lines += ['', '모든 프로그램의 여섯 조건에서 committed architectural identity도 일치했다. '
        '기존 노출 R1 입력·seed548의 deterministic clean 회귀이므로 새 독립 holdout 또는 SEU paired-owner 평가가 아니다.', '',
        '## 비용과 처리량 해석', '',
        'L은 source query의 실제 stage 수이며 provider에 추가1 stage가 있다. REC/OW의 source update L도 함께 바뀌고 Direct update는1이다. '
        'Operand가 준비되고 경합이 없을 때만 nominal ready L+1이며, 실제 end-to-end 요청에는 source version/ordering/FIFO 대기가 더해진다. '
        '따라서 위 차이를 순수 lookup latency 또는 lookup 중첩 효과 하나로 해석하지 않는다.', '',
        '| 프로그램 | L | 방식 | 완료/source cycle | lookup 최대 pending | source 최대 pending | source dependency 관측 | recovery ACK retire 대기 관측 |',
        '|---|---:|---|---:|---:|---:|---:|---:|']
    for program in ['qsort_small','dijkstra_small','sha1']:
        for L in [1,2]:
            for rep in ['recurrent','direct','overwrite']:
                r=by[program,L,rep];s=r['stall_observations']
                lines.append(f"| {program} | {L} | {rep} | {r['lookup_consumed_per_source_cycle']:.6f} | {r['max_lookup_pending']} | {r['max_source_pending']} | {s['source_dependency_stalls']:,} | {s['retire_recovery_wait_calls']:,} |")
    max_lookup=max(r['max_lookup_pending'] for r in rows)
    holds=sum(r['stall_observations']['recovery_core_hold_cycles'] for r in rows)
    peak=max(float((m.OUT/r['label']/'gem5.time').read_text().splitlines()[-1].split()[2]) for r in rows)
    lines += ['', f'IMPLEMENTED/TESTED RESULT: 실제 CPU lookup 최대 pending={max_lookup}, 전체 core recovery hold 관측 합={holds:,} cycles였다. '
        '각 counter는 원시 관측이며, 겹칠 수 있는 wait/stall 호출을 더해 CPI를 인과 분해하지 않는다. '
        '완료 요청 처리량에는 잘못된 경로의 speculative lookup도 포함하며 architectural IPC와 구분한다. '
        'JSON에는 committed controls/source cycle도 별도로 보존한다. '
        '여기서 recovery는 정상 branch-mispredict recovery이고 SEU 이후 회복 실행은 없다.', '',
        '현재 measured source의 독립128요청 gate는 multi pending129/130 대 single pending256/384 component cycles였다. '
        '독립 input의 latency/II와 single-pending 비용은 분리했지만 실제 next-PC/history 의존성과 Fetch 한-token 제한은 서로 분리하지 못했다. '
        'CPU에선 source 작업 중첩과 lookup 요청 중첩을 구별해야 한다. SOURCE_INTERFACE.ko.md에 sampling/visibility/ports/freshness/hold를 명시했다.', '',
        '## 기존 C0 정상 재현 참고점', '',
        '| 프로그램 | 기존 v11 C0 cycles | REC L1 증가 | Direct L1 증가 |',
        '|---|---:|---:|---:|']
    for program in ['qsort_small','dijkstra_small','sha1']:
        native=next(t['reference_CPU_cycles'] for t in proposal['tasks'] if t['program']==program)
        a,b=by[program,1,'recurrent'],by[program,1,'direct']
        lines.append(f"| {program} | {native:,} | {100*(a['cycles']/native-1):+.4f}% | {100*(b['cycles']/native-1):+.4f}% |")
    lines += ['', '위 참고값은 이전 v11 OVERWRITE의 native 모드/C0 정상 재현이다. 당시 기존 native reference와 정상 동일성 gate를 통과한 값이며, 이번에 native를 다시 실행하지 않았다. 새로운 source 소유권/port/stage/retirement 조건이 함께 바뀌어 '
        'native 대비 증가를 read latency 하나의 효과나 물리 회로의 피할 수 없는 비용이라고 부르지 않는다.', '',
        '## 실패·보존·가정', '',
        'C++ 초기 A1은 `undo outside reserved source`로 실패했다. recovery source ACK 이전의 조기 credit 반환을 실제 recovery-tag/counter/ACK fence로 수정했다. '
        'A1 source/binary/log는 보존했고 A2/B1 equality23052 controls·nested squash720, 추가 ingress metadata430 SBU, '
        '전체 metadata6158 SBU·mid-repair1·기대 DUE1과 작은 epoch wrap gate가 통과했다. '
        '이 gate는 SECDED3+·correlated copies/MCU의 보편 안전성 증명이 아니다.', '',
        'B1 계측은 observation을 제거한 알고리즘 본문이 A1 CPU producer와 같음을 확인했다. 기존 archive와 원래 gem5 binary SHA도 검산했다. '
        '단, 사용하지 않은 최초 CPU_EXECUTION_PROPOSAL.lock.json이 가리키는 runner 한 버전의 원본 bytes는 없다. '
        '실제 승인·실행한 B1 runner/config/binary/dependencies는 일치한다. FINAL_BINDINGS.json에 이 초안 한정 누락을 숨기지 않는다. '
        'PILOT6의 pending은 실행 중을 포함한 미완료 건수였으며, 그 Markdown의 `미실행` 표현은 부정확했다. 최종24건은 raw EXECUTION으로 재감사했다.', '',
        'VERIFIED ASSUMPTIONS: 선언한 L과 provider1, 두-copy SECDED 정상 encode/decode stage-fit은 timing 가정이다. '
        'FIFO/latch/ID/epoch/control 저장소는 manifest에 포함한다. CPU-owned BI/원래 architectural state, allocator/RNG, 절대 simulator helpers와 관측 counter는 명시적으로 제외했다. '
        '유한 source는 raw1130(활성130+undo retention1000)/path16을 사용한다. 논리 bit 수는 합성 면적 또는 SEU 단면적이 아니다. '
        'RTL/Cadence/SPICE/TCAD 실행은0이다.', '',
        '## 자원과 실행 경계', '',
        f"Actual global CPU {resources['CPU_global']}/{resources['CPU_cap']}, 새24, 실패 회귀 reserve2는 사용하지 않았다. "
        f"CPU phase {resources['CPU_phase_recorded_coreh']:.6f} recorded coreh, v11 이후 {resources['recent_recorded_coreh']:.6f}/5, "
        f"v9 이후 {resources['v9_onward_recorded_coreh']:.6f}/16, global {resources['global_recorded_coreh']:.6f}/108이다.", '',
        f"Disk recent {resources['recent_MiB']:.3f}/320 MiB, 여섯 worktree {resources['all6_GiB']:.6f}/8 GiB. "
        f"단일 trial 최대 GNU-time RSS {peak/1024:.3f} MiB. shared32 lease와 core affinity를 사용했다. "
        '첫2 → checksum4 → 프로그램9를 검증한 뒤, 원래 runner의 budget-only stop도 보존했다. '
        '다음 승인 묶음 예약이 초기 내부 CPU3.5를 약75초 넘겨 agent가3.55로 내부 배분했다. '
        '사용자 총5/16/108coreh·CPU3513·disk/slots는 유지하고 별도 dispatcher/guard가 원래 동결 trial 함수를 재사용했다. '
        '입력·seed·timeout·simulated schedule은 변경하지 않았다. INTERNAL_CPU_ALLOCATION_R1.lock.json은 새 human 승인이 아니다.', '',
        '## NOT DONE / BLOCKERS / NEXT', '',
        'NOT DONE: 같은 resource의 frequent/periodic P_ED·ECC·TMR controller staging, 새 CPU fault schedule binding, '
        'SOURCE/WHOLE 별도 A/B/C/D·B−D·paired CI와 독립 owner/input 평가. 실제 next-PC/Fetch 제한 분리와 pure query-only latency 대조도 아직 없다. '
        '따라서 보호법 최종 우위와 hardware-qualified 후보는 미확정이다. 기존 S*=346 필수 기준선은 보존했다.', '',
        'BLOCKERS: 새 CPU 후보/사건에 전용으로 배정된 trial은 없다. 잔여2회는 failed-stage 회귀 전용이다. '
        '현재24회 실행에 사용자 설치/파일/라이선스 조치는 필요 없다. USER_ACTIONS_REQUIRED.md에 재현 명령과 필요한 다음 범위를 기록했다.', '',
        'NEXT: NEXT_COST_CONTROLS.ko.md의 pure-query 대조와 unconditional의 필요한 state만 기다리는 경로를 먼저 검토한다. '
        '원래 target miss/fallthrough/RAS·source freshness·speculation 정책을 보존하며, 실제 준비되지 않은 PC/history를 무료로 제공하지 않는다. '
        '새 후보 gate/plan을 동결한 뒤 정확한 추가 CPU/time 예산을 제시한다. 이번 정상 회귀로 연구 전체 goal을 complete 처리하지 않는다.', '']
    target=BASE/'reports/FINAL_REPORT.ko.md'
    with target.open('x') as f:f.write('\n'.join(lines))
    m.m.put(BASE/'reports/FINAL_GATES.json',{'status':'PASS_24_CLEAN_O3_RESOURCE_GATE_NOT_FULL_PROTECTION_OR_HARDWARE_QUALIFICATION',
        'analysis':m.m.ref(BASE/'reports/CPU_ANALYSIS_FINAL.json'),'report':m.m.ref(target),
        'gates':[m.m.ref(BASE/'reports'/name) for name in ['CONTROLLER_GATE_B1.json','recovery_A1.json','throughput_B1.json','INITIALIZATION_B1.json','MEASURED_BINARY_B1.json']],
        'CPU_trials':24,'CPU_failures':0,'new_fault_trials':0,'EDA_runs':0,'goal':'ACTIVE','resources':resources})
    actions=BASE/'reports/USER_ACTIONS_REQUIRED.md'
    with actions.open('x') as f:
        f.write('''# USER_ACTIONS_REQUIRED — v14

현재 실행에 필요한 사용자 조치: 없음. 승인된 CPU24는 실제 종료와 원시 출력/hash 검증을 마쳤다. 공개 도구 설치·새 dataset·SPEC 배포본·license/PDK 경로 요청은 없다. 새 CPU 프로그램은 기존 R1 qsort_small/dijkstra_small/sha1이며 SPEC trace 결과와 구분한다.

DONE / 이전 실패: `/home/youns/workspace/ele548-project-v10/.venv/bin/python -B o3_finite_v14/tools/prepare.py --attempt A1`의 C++ 실행이 `undo outside reserved source`로 실패했다. 명령은 v14 worktree에서 실행됐다. 조기 source retirement를 실제 recovery-tag/ACK fence로 수정한 concrete fix1회 뒤 A2/B1이 통과했다. `runtime/run_A1/{stdout,stderr,job.time,EXECUTION.json}`과 A1 source/binary를 보존했다. 이 실패를 CPU 성공이나 masked SEU로 분류하지 않는다. 이전 경로로 명령을 재실행하면 고정 결과 보존 guard가 거절한다.

자원 단계의 정지: 원래 `tools/run_cpu.py --run`은15 PASS 후 다음 묶음의 보수적 timeout 예약 때문에 종료했다. `reports/CPU_STOP_BUDGET.json`은 보존한다. 사용자 총5/16/108coreh 안에서 초기 내부 CPU allocation만3.50→3.55로 조정했고, 별도 `tools/resume_approved_cpu.py --attempt R1 --run`이 원래 frozen trial 함수로 남은 승인9건을 실행했다. 새 human approval 또는 aggregate cap 증액이라고 기록하지 않았다. 새 guard/dispatcher 외 predictor source/config/binary/timeout/input/seed/simulated schedule은 바뀌지 않았다.

검증 명령(읽기 전용):

```bash
cd /home/youns/workspace/ele548-project-v14
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B o3_finite_v14/tools/resources_followon.py
git status --short
```

결과는 `reports/FINAL_REPORT.ko.md`, `CPU_ANALYSIS_FINAL.json`, `FINAL_GATES.json`, `FINAL_BINDINGS.json`, `POST_EXPORT_VERIFICATION.json`으로 확인한다. Raw `runtime/cpu_trials/*/EXECUTION.json`에는 실제 명령·exit·출력 SHA·cycles/IPC가 있다. 동일 run prefix에 CPU 명령을 다시 발행하지 않는다.

NOT DONE / NEXT: 같은 resource의 보호 controller staging과 새 CPU fault schedule binding, 독립 paired-owner 평가가 남았다. 현재 남은2회는 실패 회귀 전용이므로 새 query-only 또는 unconditional 후보 실험에 사용하지 않는다. `NEXT_COST_CONTROLS.ko.md`의 최소 query-only 후보는 checksum1+프로그램3=추가4회지만 아직 config/후보 gate/실행 producer가 준비되지 않았다. 우선 그 준비를 하고, 실제 host/disk 산정과 고정 입력/명령이 갖춰지면 다음 CPU 범위의 배분을 제시한다. 현재 단계에서 미완성 후보의 승인을 요청하지 않는다. Cadence/SPICE/TCAD는 필요하지 않다.
''')
    print('WROTE_FINAL_REPORT_FROM_ACTUAL24')
if __name__=='__main__':main()
