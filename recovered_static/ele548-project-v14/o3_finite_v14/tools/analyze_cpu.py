#!/usr/bin/env python3
"""Offline audit of the frozen CPU24 cohort; dispatches no simulations."""
from pathlib import Path
import argparse, importlib.util, json, sys

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cpu_runner', BASE / 'tools/run_cpu.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
if (BASE / 'reports/INTERNAL_CPU_ALLOCATION_R1.lock.json').exists():
    runner.r = runner.mod('allocated_resources', BASE / 'tools/resources_followon.py')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    target = BASE / 'reports' / ('CPU_ANALYSIS_' + args.attempt + '.json')
    markdown = target.with_suffix('.ko.md')
    assert not target.exists() and not markdown.exists(), 'PRESERVE_OLD_ANALYSIS'
    load, ref = runner.load, runner.m.ref
    plan_path = BASE / 'reports/CPU24_PLAN.lock.json'
    plan = load(plan_path)
    for key in ['proposal', 'authorization', 'binary', 'config', 'runner', 'shared_slot_validator']:
        runner.checked(plan[key])
    build = load(BASE / 'reports/MEASURED_BINARY_B1.json')
    for dependency in build['actual_dependencies']:
        runner.checked(dependency)
    preservation = load(BASE / 'reports/PRESERVATION.lock.json')
    for item in preservation['preserved']:
        runner.checked(item)
    cases = {t['label']: t for t in plan['tasks']}
    rows, failed = [], []
    for path in sorted(runner.OUT.glob('*/EXECUTION.json')):
        row = load(path)
        for name, digest in row['hashes'].items():
            assert runner.m.sha(path.parent / name) == digest, ('RAW_CHANGED', path, name)
        if not row['status'].startswith('PASS_'):
            failed.append({'label': row['label'], 'execution': ref(path), 'failure': row.get('failure')})
            continue
        actual = runner.validate(cases[row['label']], path.parent, row['exit_code'])
        assert actual['cycles'] == row['cycles'] and actual['seu'] == row['seu']
        manifest_path = path.parent / 'logical_manifest.json'
        manifest = load(manifest_path)
        cursor = 0
        for region in manifest['regions']:
            assert region['start'] == cursor and region['bits'] > 0
            cursor += region['bits']
        assert cursor == manifest['total_logical_bits']
        source = row['seu']
        rows.append({
            'label': row['label'], 'program': row['program'], 'representation': row['representation'],
            'source_L': row['source_L'], 'cycles': row['cycles'], 'IPC': row['IPC'],
            'source_cycles': source['source_cycles'], 'committed_identity': source['committed_identity'],
            'committed_controls': source['committed_controls'], 'committed_ops': source['committed_ops'],
            'committed_controls_per_source_cycle': source['committed_controls'] / source['source_cycles'],
            'max_lookup_pending': source['max_lookup_pending'], 'max_source_pending': source['max_source_pending'],
            'lookup_consumed_per_source_cycle': source['lookup_consumed'] / source['source_cycles'],
            'host_cpu_seconds': row['host_cpu_seconds'],
            'stall_observations': {k: v for k, v in source.items() if 'stall' in k or 'wait' in k or 'hold' in k},
            'logical_bits': cursor, 'manifest': ref(manifest_path), 'execution': ref(path),
        })
    pending = sorted(set(cases) - {r['label'] for r in rows} - {r['label'] for r in failed})
    comparisons = []
    for program in ['checksum', 'qsort_small', 'dijkstra_small', 'sha1']:
        group = [r for r in rows if r['program'] == program]
        if len(group) != 6:
            continue
        identity = len({r['committed_identity'] for r in group}) == 1
        for L in [1, 2]:
            baseline = next(r for r in group if r['representation'] == 'recurrent' and r['source_L'] == L)
            for row in [r for r in group if r['source_L'] == L]:
                comparisons.append({'program': program, 'source_L': L, 'representation': row['representation'],
                    'cycles': row['cycles'], 'IPC': row['IPC'], 'same_architectural_identity': identity,
                    'delta_cycles_vs_same_L_recurrent_percent': 100 * (row['cycles'] / baseline['cycles'] - 1),
                    'note': 'Direct source update is one cycle; REC/OW source update uses L. This is the declared resource model, not a pure lookup-only contrast.'})
    complete = not pending and not failed and len(rows) == 24
    same_identity = all(c['same_architectural_identity'] for c in comparisons)
    report = {'status': 'PASS_24_AUDITED_CLEAN_CPU_NOT_PROTECTION_RANKING' if complete and same_identity else 'INCOMPLETE_OR_FAILED_VISIBLE',
        'plan': ref(plan_path), 'binary': build['binary'], 'preserved_bindings_checked': len(preservation['preserved']),
        'rows': rows, 'failed': failed, 'pending': pending, 'comparisons': comparisons,
        'resources': runner.r.snapshot(),
        'limits': ['existing exposed R1 inputs and seed548; no independent holdout',
            'P0 source ownership/resource cohort; no new fault schedules or ABCD/B-D confidence interval',
            'lookup pending limited by actual Fetch/next-PC stream despite independent component II1',
            'global recovery stage hold and recovery-ACK retirement barrier are conservative model choices',
            'read/source latency, recovery and changed speculation are not a causal CPI decomposition',
            'stage-fit/codec timing assumed; no physical hardware qualification',
            'new protection-controller staging and CPU fault-schedule binding remain unimplemented'],
        'analysis_tool': ref(Path(__file__))}
    runner.m.put(target, report)
    lines = ['# v14 실제 O3 정상 비교', '', report['status'], '',
        'SOURCE FACT: 고정된 CPU24 계획·바이너리·입력·원시 로그 SHA와 기존 producer 보존을 검산했다. '
        '각 프로그램 출력, 프로토콜 보존식, 실제 source clock과 논리 bit manifest를 재검증했다.', '',
        '| 프로그램 | source L | 방식 | cycles | IPC | 같은 L REC 대비 cycles | lookup 최대 진행 수 | 완료/source cycle |',
        '|---|---:|---|---:|---:|---:|---:|---:|']
    for c in comparisons:
        row = next(r for r in rows if r['program'] == c['program'] and r['source_L'] == c['source_L'] and r['representation'] == c['representation'])
        lines.append(f"| {c['program']} | {c['source_L']} | {c['representation']} | {c['cycles']:,} | {c['IPC']:.6f} | {c['delta_cycles_vs_same_L_recurrent_percent']:+.4f}% | {row['max_lookup_pending']} | {row['lookup_consumed_per_source_cycle']:.6f} |")
    lines += ['', f'실패 {len(failed)}, 완료 미확인 {len(pending)}(실행 중 포함). 실패/미완료에 cycles를 부여하지 않는다.', '',
        'IMPLEMENTED/TESTED RESULT의 범위는 위 실행뿐이다. L은 source query 지연이며 provider에 실제 한 단계가 더 있다. '
        'Direct의 source update는 1 cycle, REC/OW는 L cycle이다. L2−L1은 source read/update와 speculation 변화가 섞인 민감도다.', '',
        '새 오류 실행이 없으므로 A/B/C/D·B−D·paired CI와 보호법 우위를 계산하지 않는다. '
        '기존 노출 R1 입력의 정상 회귀이며 독립 평가가 아니다. Stall/wait 호출은 겹칠 수 있어 합계를 CPI 원인 분해로 읽지 않는다.', '',
        'NOT DONE: 실제 frontend의 요청 중첩 확대와 next-PC 의존성 분리, parity/ECC/TMR의 동일 source controller staging, '
        '새 CPU fault schedule 연결과 독립 owner 평가, 물리 지연 검증. 기존 S*=346 bit 기준선은 보존한다.', '',
        '원시 결과/자원/실패 목록은 같은 이름 JSON에 연결했다. 이 도구는 CPU 실행을 추가하지 않는다.', '']
    markdown.write_text('\n'.join(lines))
    print(report['status'], 'PASS', len(rows), 'FAIL', len(failed), 'PENDING', len(pending))


if __name__ == '__main__':
    main()
