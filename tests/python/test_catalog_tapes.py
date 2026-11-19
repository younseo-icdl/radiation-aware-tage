import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from simulation.analysis.catalog_tapes import coupled_events, generate, storage_sites


class CatalogTapeTests(unittest.TestCase):
    @staticmethod
    def manifest(offset, *, protection=(), age=0):
        return {'words':[dict(word=21,consumed=True,width=2,site_ids=[offset,offset+1])],
                'protection_sites':list(protection), 'lease_age_bits':age,
                'lease_age_sites_start':offset+2}

    def test_semantic_union_and_output_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            plain=self.manifest(8)
            ecc=self.manifest(80,protection=[
                dict(structure='secded_check',word=21,bit=0,replica=0,id=99)])
            marks={'plain':plain,'ecc':ecc,'rebuild':self.manifest(108,age=1)}
            names={}
            for arm, manifest in marks.items():
                names[arm]=root/(arm+'.json')
                names[arm].write_text(json.dumps(manifest))
            out=root/'tapes'
            info=generate(names,out,19,10**12,256)
            shared=(out/'semantic-union.events').read_bytes()
            self.assertEqual(info['union_tape_sha256'],hashlib.sha256(shared).hexdigest())
            self.assertEqual(info['arms']['plain']['events_per_second'],512)
            self.assertEqual(info['arms']['ecc']['events_per_second'],768)
            entries=shared.decode().splitlines()[1:]
            self.assertTrue(any(' C21:0' in line for line in entries))
            self.assertTrue(any(' L:AGE:0' in line for line in entries))
            for arm,manifest in marks.items():
                rows=(out/(arm+'.events')).read_text().splitlines()[1:]
                self.assertEqual(rows,[line for line in entries
                                       if line.split()[1] in storage_sites(manifest)])
            catalogs={arm:storage_sites(spec) for arm,spec in marks.items()}
            shorter=list(coupled_events(19,10**11,256,catalogs))
            self.assertEqual(shorter,[item for item in coupled_events(19,10**12,256,catalogs)
                                      if item[0]<=10**11])

    def test_duplicate_native_site_is_rejected(self):
        broken=self.manifest(8,protection=[
            dict(structure='replica',word=21,bit=0,replica=1,id=8)])
        with self.assertRaisesRegex(ValueError, 'alias'):
            storage_sites(broken)
