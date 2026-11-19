import json
from pathlib import Path
import tempfile
import unittest

from simulation.analysis.protection_evidence import applied_trace


class ProtectionEvidenceTests(unittest.TestCase):
    def test_simultaneous_records_preserve_individual_multiplicity_and_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)
            raw = dict(name='raw_path:0', word=21, width=130, site_ids=list(range(130)))
            copies = [dict(id=replica*130+bit, structure='replica', word=21, replica=replica, bit=bit)
                      for replica in (1,2) for bit in range(130)]
            (run / 'logical_manifest.json').write_text(json.dumps(dict(words=[raw], protection_sites=copies)))
            header = ('event_ordinal,requested_tick,applied_tick,multiplicity,logical_site_ids,'
                      'raw_physical_indices,bit_values_before,bit_values_after\n')
            log = run / 'events.csv'
            log.write_text(header + '1,500,500,1,130,,0,1\n2,500,500,2,260;261,,1;0,0;1\n')
            events, kinds, replicas = applied_trace(run, 'tmr', 600)
            self.assertEqual(events, [(500,(0,)), (500,(0,1))])
            self.assertEqual(kinds, {'K1':1, 'K2':1})
            self.assertEqual(replicas, {'replica_1':1, 'replica_2':1})
            log.write_text(header + '1,500,500,2,130;261,,1;0,0;1\n')
            with self.assertRaisesRegex(ValueError, 'invalid event delivery'):
                applied_trace(run, 'tmr', 600)
