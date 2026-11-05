#!/usr/bin/env python3
"""Prepare and build the pinned gem5 integration in a separate local tree."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
TAG, COMMIT = (ROOT / 'simulation/gem5/VERSION').read_text().splitlines()


def command(args, cwd=None, env=None):
    subprocess.run([str(x) for x in args], cwd=str(cwd or ROOT), env=env, check=True)


def prepare(destination):
    if destination.exists():
        raise ValueError('destination exists; use a fresh directory for each producer')
    destination.parent.mkdir(parents=True, exist_ok=True)
    command(['git', 'clone', '--depth', '1', '--branch', TAG,
             'https://github.com/gem5/gem5.git', destination])
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(destination),
                                     universal_newlines=True).strip()
    if actual != COMMIT:
        raise ValueError('gem5 tag does not match the pinned commit')
    shutil.copytree(str(ROOT / 'tage/include/tage'), str(destination / 'src/tage'))
    for source_root in (ROOT / 'tage/backend', ROOT / 'simulation/gem5/overlay/src'):
        for source in source_root.rglob('*'):
            if source.is_file():
                target = destination / 'src' / source.relative_to(source_root)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(source), str(target))
    sconscript = destination / 'src/cpu/pred/SConscript'
    with sconscript.open('a') as out:
        out.write("\nSimObject('FiniteTAGE.py', sim_objects=['FiniteTAGEBase', 'FiniteTAGE'])\n")
        out.write("Source('finite_tage.cc')\n")
    print('Prepared {} at {}'.format(TAG, destination))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['prepare', 'build'])
    p.add_argument('--tree', type=Path, default=ROOT / 'build/gem5')
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--cxx', help='compiler for this build only')
    a = p.parse_args()
    try:
        if a.action == 'prepare':
            prepare(a.tree.resolve())
        else:
            if not 1 <= a.jobs <= 32:
                p.error('jobs must be 1..32')
            args = [sys.executable, '-m', 'SCons', 'build/X86/gem5.opt', '-j', str(a.jobs)]
            env = os.environ.copy()
            if a.cxx:
                compiler = Path(a.cxx).resolve()
                env['CXX'] = str(compiler)
                env['CC'] = str(compiler.with_name('gcc'))
                env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
            config = Path(sys.base_prefix) / 'bin/python3-config'
            if config.exists():
                env['PYTHON_CONFIG'] = str(config)
            libdir = sysconfig.get_config_var('LIBDIR')
            if libdir:
                env['LD_LIBRARY_PATH'] = str(libdir) + os.pathsep + env.get('LD_LIBRARY_PATH', '')
            command(args, a.tree.resolve(), env)
    except (ValueError, subprocess.CalledProcessError) as error:
        p.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
