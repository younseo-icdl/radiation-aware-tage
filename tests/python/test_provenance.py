"""Source-integrity audits must detect drift without certifying CPU behavior."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.audit_gem5 import audit, REGISTRATION


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.upstream, self.repo = self.root/'upstream', self.root/'repo'
        for root in (self.upstream, self.repo):
            root.mkdir()
            self.git(root, 'init', '-q')
        self.put(self.upstream, 'src/cpu/pred/SConscript', 'upstream\n')
        self.put(self.upstream, 'src/cpu/core.cc', 'original\n')
        self.commit(self.upstream)
        pin = self.git(self.upstream, 'rev-parse', 'HEAD').decode().strip()
        self.put(self.repo, 'simulation/gem5/VERSION', 'test-tag\n'+pin+'\n')
        self.put(self.repo, 'tage/backend/cpu/core.cc', 'overlay\n')
        self.put(self.repo, 'tage/include/tage/access.hpp', 'header\n')
        self.commit(self.repo)

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), '-c', 'user.name=Test',
            '-c', 'user.email=test@example.invalid', *args], stderr=subprocess.PIPE)

    def put(self, root, name, content):
        path = root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self, root):
        self.git(root, 'add', '.')
        self.git(root, 'commit', '-qm', 'fixture')

    def overlay(self):
        self.put(self.upstream, 'src/cpu/core.cc', 'overlay\n')
        self.put(self.upstream, 'src/tage/access.hpp', 'header\n')
        path = self.upstream/'src/cpu/pred/SConscript'
        path.write_bytes(path.read_bytes()+REGISTRATION)

    def test_pristine_source_does_not_certify_runtime_authenticity(self):
        result = audit(self.repo, self.upstream, pristine=True)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['baseline_authenticity'], 'PRISTINE_AUTHENTICITY_UNVERIFIED')
        self.overlay()
        failed = audit(self.repo, self.upstream, pristine=True)
        self.assertEqual(failed['status'], 'FAIL')
        self.assertEqual(failed['classification'], 'UNVERIFIED_SOURCE')

    def test_overlay_and_registration_are_checked_byte_for_byte(self):
        self.overlay()
        self.assertEqual(audit(self.repo, self.upstream)['status'], 'PASS')
        with (self.upstream/'src/cpu/pred/SConscript').open('ab') as stream:
            stream.write(REGISTRATION)
        result = audit(self.repo, self.upstream)
        self.assertEqual(result['status'], 'FAIL')
        self.assertTrue(any('SConscript' in error for error in result['errors']))

    def test_unexpected_untracked_hook_fails(self):
        self.overlay()
        self.put(self.upstream, 'src/hidden_hook.cc', 'unexpected\n')
        self.assertEqual(audit(self.repo, self.upstream)['unexpected_changes'], ['src/hidden_hook.cc'])

    def test_missing_overlay_fails(self):
        self.overlay()
        (self.upstream/'src/tage/access.hpp').unlink()
        self.assertEqual(audit(self.repo, self.upstream)['status'], 'FAIL')

    def test_pin_mismatch_fails(self):
        self.put(self.upstream, 'src/cpu/core.cc', 'different producer\n')
        self.commit(self.upstream)
        result = audit(self.repo, self.upstream, pristine=True)
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('upstream commit differs from the pin', result['errors'])


if __name__ == '__main__':
    unittest.main()
