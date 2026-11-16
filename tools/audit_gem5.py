#!/usr/bin/env python3
"""Audit a pinned upstream tree or a canonical overlay without changing either.

Source integrity is not pristine CPU authenticity: runtime controls and state
observations are still required. Write generated inventories outside Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

REGISTRATION = ("\nSimObject('FiniteTAGE.py', sim_objects=['FiniteTAGEBase', 'FiniteTAGE'])\n"
                "Source('finite_tage.cc')\n").encode()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def expected_overlay(repo, producer):
    expected = {}
    roots = ('tage/include/tage/', 'tage/backend/', 'simulation/gem5/overlay/src/')
    paths = git(repo, 'ls-tree', '-r', '-z', '--name-only', producer, '--', *roots)
    for raw in paths.split(b'\0'):
        if not raw:
            continue
        path = raw.decode()
        if Path(path).suffix not in ('.cc', '.hh', '.hpp', '.py'):
            continue
        if path.startswith(roots[0]):
            target = 'src/tage/' + path[len(roots[0]):]
        else:
            prefix = next(r for r in roots[1:] if path.startswith(r))
            target = 'src/' + path[len(prefix):]
        expected[target] = git(repo, 'show', producer + ':' + path)
    return expected


def audit(repo, tree, producer='HEAD', pristine=False):
    repo, tree = Path(repo).resolve(), Path(tree).resolve()
    producer_sha = git(repo, 'rev-parse', '--verify', producer + '^{commit}').decode().strip()
    version = git(repo, 'show', producer_sha + ':simulation/gem5/VERSION').decode().splitlines()
    if len(version) != 2:
        raise ValueError('VERSION must contain the tag and exact commit')
    tag, pinned = version
    actual = git(tree, 'rev-parse', 'HEAD').decode().strip()
    errors = []
    if actual != pinned:
        errors.append('upstream commit differs from the pin')
    expected = {} if pristine else expected_overlay(repo, producer_sha)
    if not pristine:
        paths = git(repo, 'ls-tree', '-z', '--name-only', producer_sha, '--', 'simulation/gem5/registration.txt')
        registration = git(repo, 'show', producer_sha + ':simulation/gem5/registration.txt') if paths else REGISTRATION
        expected['src/cpu/pred/SConscript'] = git(tree, 'show', 'HEAD:src/cpu/pred/SConscript') + registration
    files = []
    for name, content in sorted(expected.items()):
        target = tree/name
        actual_hash = sha256(target.read_bytes()) if target.is_file() else None
        want = sha256(content)
        matches = actual_hash == want
        files.append({'path': name, 'expected_sha256': want, 'actual_sha256': actual_hash,
                      'matches': matches})
        if not matches:
            errors.append('canonical overlay missing or changed: ' + name)
    modified = [x.decode() for x in git(tree, 'diff', '--name-only', '-z', 'HEAD').split(b'\0') if x]
    untracked = [x.decode() for x in git(tree, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if x]
    unexpected = sorted((set(modified) | set(untracked)) - set(expected))
    errors.extend('unexpected source-tree change: ' + name for name in unexpected)
    return {
        'status': 'FAIL' if errors else 'PASS',
        'classification': ('UNVERIFIED_SOURCE' if errors else
                           'UNMODIFIED_UPSTREAM' if pristine else 'CANONICAL_INSTRUMENTED_OVERLAY'),
        'baseline_authenticity': 'PRISTINE_AUTHENTICITY_UNVERIFIED',
        'scope': 'byte/source integrity only; no CPU behavior or hardware-cost certification',
        'repository': str(repo), 'producer_commit': producer_sha, 'tree': str(tree),
        'pinned_tag': tag, 'pinned_commit': pinned, 'actual_commit': actual,
        'modified_tracked_files': modified, 'untracked_files': untracked,
        'canonical_files': files, 'unexpected_changes': unexpected, 'errors': errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--producer', default='HEAD', help='committed canonical source revision')
    parser.add_argument('--pristine', action='store_true', help='require an unmodified upstream tree')
    parser.add_argument('--output', type=Path, help='new private inventory path; refuses existing files')
    args = parser.parse_args()
    try:
        result = audit(args.repo, args.tree, args.producer, args.pristine)
        encoded = json.dumps(result, indent=2) + '\n'
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open('x') as stream:
                stream.write(encoded)
            print(json.dumps({'status': result['status'], 'inventory': str(args.output),
                              'errors': result['errors']}))
        else:
            print(encoded, end='')
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, str(error) + '\n')
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
