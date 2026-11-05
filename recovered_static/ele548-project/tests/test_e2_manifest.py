import json
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

class E2StorageContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'sources/e2_protection_logical_manifest.json').read_text())
        cls.scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())

    def test_payload_scope_is_frozen(self):
        self.assertEqual(self.manifest['payload_words'],self.scope['payload_words'])
        ids=[b for w in self.manifest['payload_words'] for b in w['site_ids']]
        self.assertEqual(len(ids),346)
        self.assertEqual(len(set(ids)),346)
        self.assertEqual(set(ids),set(range(65024,65370)))

    def test_actual_codewords_and_replica_coverage(self):
        words=self.manifest['payload_words']
        for scheme in ['P_ED','P_ECC','P_TMR']:
            rows=self.manifest['additional_sites'][scheme]
            self.assertEqual([int(r['site_id']) for r in rows],list(range(65370,self.manifest['total_bits'][scheme])))
            for word in words:
                n=word['payload_bits'];r=0
                while (1<<r)<n+r+1:r+=1
                expected=1 if scheme=='P_ED' else r+1 if scheme=='P_ECC' else n
                for replica in ([1,2] if scheme=='P_TMR' else [0]):
                    matching=[x for x in rows if x['word_id']==word['word_id'] and int(x['replica'])==replica]
                    self.assertEqual([int(x['bit']) for x in matching],list(range(expected)))
                    self.assertTrue(all(int(x['width'])==expected for x in matching))
            if scheme!='P_TMR':
                for name,n in [('refill_remaining',8),('history_epoch',32)]:
                    self.assertEqual([int(x['bit']) for x in rows if x['structure']==name],list(range(n)))

    def test_unavailable_physical_mapping_not_fabricated(self):
        self.assertIsNone(self.manifest['physical_mapping'])
        self.assertFalse(self.manifest['statistics_and_simulator_slack_exposed'])

if __name__=='__main__':unittest.main()
