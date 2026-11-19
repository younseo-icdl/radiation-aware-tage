import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from simulation.analysis.native_completion import BPU, PROVIDERS, completion


class NativeCompletionTests(unittest.TestCase):
    def test_provider_counts_and_typed_stop(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            native = dict(tick=2000, faults_frozen=True, retired_instructions=10,
                          conditional_updates=4, schedule_exhausted_before_exit=False,
                          applied_events=1, applied_flips=2, declared_tape_horizon_tick=4000)
            term = dict(program_exit_tick=2000, post_exit_advance_ticks=0, cpu_cycle_ticks=500,
                        status='PASS', exit_code=0)
            stats = dict(finalTick=2000, simTicks=2000, simFreq=10**12, simInsts=10)
            stats['system.clk_domain.clock'] = 500
            stats[BPU+'committed_0::DirectCond'] = 4
            stats[BPU+'committed_0::IndirectCond'] = 0
            stats[BPU+'condIncorrect'] = 9
            for provider in PROVIDERS:
                base = BPU+'conditionalBranchPred.tage.'+provider+'Provider'
                stats[base+'Correct'] = 1 if provider != 'bimodal' else 0
                stats[base+'Wrong'] = 1 if provider == 'bimodal' else 0
            (run/'stats.txt').write_text('---------- Begin Simulation Statistics ----------\n' +
                                        ''.join(f'{k} {v}\n' for k,v in stats.items()) +
                                        '---------- End Simulation Statistics ----------\n')
            (run/'program.stdout').write_bytes(b'known output\n')
            golden = hashlib.sha256(b'known output\n').hexdigest()

            def summarize(expected):
                (run/'native.json').write_text(json.dumps(native))
                (run/'termination.json').write_text(json.dumps(term))
                return completion(run, expected)

            success = summarize(golden)
            self.assertEqual((success['status'], success['direction_wrong'], success['direction_mpki'],
                              success['completion_cycles']), ('correct', 1, 100, 4))
            self.assertEqual(summarize('f'*64)['status'], 'sdc')
            native.update(history_protection_halted=True, protection_due_words=1)
            term.update(status='DETECTED_STOP', history_protection='ecc_halt')
            stopped = summarize(golden)
            self.assertEqual(stopped['status'], 'detected_stop')
            self.assertIsNone(stopped['completion_cycles'])
            self.assertEqual(stopped['roi_end_tick'], 2000)
