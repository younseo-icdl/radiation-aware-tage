#!/usr/bin/env python3
"""Export implemented operation/storage/timing and audited CPU activity proxies."""
import collections
import csv
import json
from pathlib import Path
from summarize_e3_cpu import sha

ROOT = Path(__file__).resolve().parents[1]
SCHEMES = ['P0', 'P_ED', 'P_ECC', 'P_TMR']
COUNTERS = ['prediction_reads', 'checks', 'word_reads', 'word_writes', 'sidecar_reads',
    'sidecar_writes', 'encode_words', 'voted_words', 'detected', 'corrected', 'DUE',
    'reset_refill', 'repair_words', 'replica_repairs', 'refill_updates', 'fallback_predictions',
    'speculative_writes', 'committed_refill_writes', 'response_hold_cycles', 'drain_hold_cycles',
    'repair_batches', 'stale_restores_suppressed', 'stale_training_suppressed']


def main():
    scope_path = ROOT/'sources/protection_scope.lock.json'
    scope = json.loads(scope_path.read_text())
    cpu = json.loads((ROOT/'configs/e3.cpu.lock.json').read_text())
    gate = json.loads((ROOT/'reports/E3_INTEGRATION_GATE.json').read_text())
    assert gate['status'] == 'PASS_REAL_O3_LOGICAL_INJECTION_SPECULATION_AND_RESPONSE_HOLD_GATE'
    storage = {}
    for scheme in SCHEMES:
        path = ROOT/f'reports/e3_integration/gate/clean_{scheme}/logical_manifest.json'
        manifest = json.loads(path.read_text())
        assert manifest['scheme'] == scheme and manifest['scope_id'] == scope['scope_id']
        counts = collections.Counter(s['structure'] for s in manifest['additional_sites'])
        assert manifest['base_bits'] == 65370
        assert manifest['total_bits'] == 65370+sum(counts.values())
        storage[scheme] = {'base_core_bits': 65370, 'S_star_payload_bits': 346,
            'added_bits_by_structure': dict(counts), 'total_exposed_bits': manifest['total_bits'],
            'manifest': str(path.relative_to(ROOT)), 'manifest_sha256': sha(path),
            'radiation_exclusions': manifest['excluded']}
    contract = {
        'status': 'IMPLEMENTED_SOFTWARE_OPERATION_AND_ASSUMED_TIMING_CONTRACT_NOT_RTL_SIGNOFF',
        'scope_id': scope['scope_id'], 'scope_sha256': sha(scope_path),
        'source_pin': 'gem5 v25.1.0.1 / c8222cc67a399bfc01e8658dd14b30d5bfd634f9',
        'payload_words': scope['payload_words'], 'storage': storage,
        'source_files': {p: sha(ROOT/p) for p in ['src/protection/history_controller.hpp',
            'src/protection/spec_history.hpp', 'gem5_ext/research_tage.cc', 'gem5_ext/research_tage.hh']},
        'operations': {
            'capture_read': 'check all 23 selected natural words before TAGE lookup; save epoch/fallback with BranchInfo',
            'consume': 'integrity check before delivering cached direction; retry if epoch/fallback changed',
            'speculative': 'check before upstream speculative history RMW; skip during fallback/stale generation',
            'commit': 'check before actual-branch training; preserve one upstream RNG draw per actual control. During fallback use actual history once and decrement refill; normal commit does not refill',
            'corrected': 'check then upstream squash/corrected outcome; suppress stale/fallback restoration',
            'discard': 'check then restore only current generation; do not encode on a mere read or unchanged discard',
            'reset_refill': 'reset dependent raw/path/folded scope, encode sidecars, increment epoch, set recovery_active and refill130; tagged prediction/allocation excluded while fallback; bimodal training/upstream aging continue',
            'drain': 'after130 actual committed controls, wait for BPU history queue empty before clearing recovery_active and enabling tags',
            'legitimate_write': 'synchronize parity/ECC or both replicas only after legitimate write/reset; protect logic never sees injector schedule/K/golden state'},
        'fault_laws': {'P_ED': 'even word parity, no guarantee for even-number corruption',
            'P_ECC': 'shortened extended-Hamming SECDED, correct1+writeback, DUE2 -> same fallback, >=3 no correction/detection guarantee',
            'P_TMR': 'bitwise majority plus feedback repair; two copies wrong at same bit can vote wrong, different-bit errors can remain correct'},
        'timing': {'cycle_ticks': 500, 'C': cpu['latency_sensitivity']['check_cycles'],
            'R': cpu['latency_sensitivity']['repair_cycles'], 'contract': cpu['latency_contract'],
            'repair_origin_order': ['read', 'consume', 'speculative', 'commit', 'corrected', 'discard'],
            'injection_priority': 49, 'CPU_tick_priority': 50,
            'repair_busy_law': 'busy_until=max(current_tick,busy_until)+R*500 per detection batch',
            'storage_writeback': 'begins at detection, pending response not delivered until busy ends; squash cancels pending response',
            'batch_parallelism': 'all corrected/reset words in one callback are one parallel batch; later batches serialize',
            'backend_lane': 'independent continues; clean integrity RMW assumes no additional cycles',
            'multiple_operations_at_one_Tick': 'software callbacks have ordered atomic semantics and may share a CPU tick. RTL needs enough ports/throughput or an explicit arbitration model; one operation per cycle is not established',
            'measured_RTL_latency': None, 'RTL_ports_or_clock_interface_frozen': False},
        'activity_counter_semantics': {
            'word_reads': 'reads for protection check only (ED/ECC 1, TMR3 per selected word per check); excludes underlying ordinary TAGE lookup reads. P0 zero is not zero storage read activity',
            'word_writes': 'declared selected-word slots after legitimate write/reset/correction; TMR counts all3 output slots even if some do not toggle',
            'sidecar_reads': 'one code sidecar per ED/ECC word/check, variable bit width retained in manifest',
            'sidecar_writes': 'code writes after legitimate update/reset and ECC correction; not a gate-toggle counter',
            'encode_words': 'counted legitimate ED/ECC encode/reset operations; initialization and complete combinational encoder activity are not included',
            'voted_words': 'TMR word vote invocations during integrity check',
            'detected_corrected_DUE': 'word outcomes, not particle/event counts; one injected cluster may cause several word outcomes',
            'reset_refill': 'fallback reset invocations per check; not automatically equal DUE-word count',
            'replica_repairs': 'number of copies differing from majority before repair; distinct from3 declared write slots',
            'response_hold_cycles': 'frontend hold observations for C/R response; pipeline overlap means not equal total extra CPU cycles',
            'repair_batches': 'one accounted batch per callback with any detection; batch is not necessarily an injected event'},
        'not_provided': ['per-bit value/toggle waveform for every transaction', 'actual RTL VCD/SAIF and clock tree activity',
            'measured cell/macro energy', 'physical layout/area/delay', 'full-system cost of excluded in-flight transport/generation state'],
        'next_RTL_gate': 'same functional capacity/operations/invalidation/refill policy; replay clean/FI/rollback/late-commit cases against C++ at agreed cycle protocol; add port/arbitration constraints before measured latency replaces C/R. Synthesis excludes injector/logging/stats',
    }
    destination = ROOT/'sources/e4_software_interface_contract.json'
    destination.write_text(json.dumps(contract, indent=2)+'\n')
    exports = []
    for phase in ['pilot', 'main', 'latency']:
        summary_path = ROOT/f'reports/E3_CPU_{phase.upper()}_SUMMARY.json'
        report_path = ROOT/f'reports/E3_CPU_{phase.upper()}.json'
        if not summary_path.exists():
            continue
        summary = json.loads(summary_path.read_text())
        assert summary['status'] in ['PASS_AUDITED_COMPLETE_CPU_PHASE', 'AUDITED_COMPLETE_CPU_PHASE_WITH_FAILURES']
        assert summary['campaign_sha256'] == sha(report_path)
        report = json.loads(report_path.read_text())
        assert report['status'] != 'RUNNING'
        path = ROOT/f'reports/e3_cpu/E4_activity_{phase}.csv'
        fields = ['phase', 'label', 'program', 'scheme', 'mode', 'status', 'cycles', 'committed_instructions', 'seu_sha256']+COUNTERS
        with path.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for t in sorted(report['tasks'], key=lambda t: t['label']):
                row = {key: t.get(key, '') for key in fields if key not in COUNTERS}
                row['phase'] = phase
                if t['status'] == 'PASS':
                    assert t['seu_sha256'] == sha(ROOT/t['output']/'seu.json')
                    row.update({key: t['seu'][key] for key in COUNTERS})
                writer.writerow(row)
        exports.append({'phase': phase, 'rows': len(report['tasks']), 'path': str(path.relative_to(ROOT)),
            'sha256': sha(path), 'campaign_sha256': sha(report_path), 'audit_summary_sha256': sha(summary_path)})
    record = {'status': 'PASS_AUDITED_COMPLETED_PHASE_ACTIVITY_PROXY_EXPORT', 'interface_contract_sha256': sha(destination),
        'exports': exports, 'actual_RTL_switching_or_power': False, 'running_phases_exported': False}
    (ROOT/'reports/E4_SOFTWARE_ACTIVITY_EXPORT.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'status': record['status'], 'completed_phases': [x['phase'] for x in exports]}))


if __name__ == '__main__':
    main()
