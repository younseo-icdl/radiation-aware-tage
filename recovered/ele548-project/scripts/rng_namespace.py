"""Disjoint experiment/trial/role/entity seeds; intentionally reuse only matched owners."""
import numpy as np

ROLE = {'time': 1, 'K': 2, 'location': 3, 'catalog': 2, 'geometry': 3, 'dispersed': 4}


def entropy(master, role, group=0, occurrence=0):
    if not 0 <= master < 2**64 or role not in ROLE or not 0 <= group < 2**32 or not 0 <= occurrence < 2**32:
        raise ValueError('invalid RNG namespace')
    return [0x42505345, 2, master & 0xffffffff, master >> 32, ROLE[role], group, occurrence]


def rng(master, role, group=0, occurrence=0):
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy(master, role, group, occurrence))))


def descriptor(master, role, group=0, occurrence=0):
    return {'engine': 'NumPy PCG64', 'namespace_version': 2,
            'SeedSequence_entropy': entropy(master, role, group, occurrence)}
