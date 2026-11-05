import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from rng_namespace import entropy, rng


class NamespaceContract(unittest.TestCase):
    def test_adjacent_trials_do_not_share_any_role_or_entity_namespace(self):
        seen = set()
        for master in range(105480000,105480100):
            for role in ['time','K','location','dispersed']:
                for group in [0,1,2054]:
                    for occurrence in [0,1,20]:
                        key=tuple(entropy(master,role,group,occurrence))
                        self.assertNotIn(key,seen)
                        seen.add(key)

    def test_reproducible_matching_and_different_owners(self):
        a=rng(105480000,'time').random(32)
        np.testing.assert_array_equal(a,rng(105480000,'time').random(32))
        self.assertFalse(np.array_equal(a,rng(105480001,'K').random(32)))
        self.assertFalse(np.array_equal(a,rng(105480000,'location').random(32)))

    def test_cpp_scalar_encoding_is_disjoint_including_anchor_xor(self):
        seen=set()
        for master in range(35480000,35480600):
            values=[(master<<8)|role for role in [1,2,3]]
            values.append(values[-1]^0x9e3779b97f4a7c15)
            for value in values:
                self.assertNotIn(value,seen)
                seen.add(value)


if __name__=='__main__':unittest.main()
