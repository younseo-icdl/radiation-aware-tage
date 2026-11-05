#!/usr/bin/env python3
"""Prepare, build, and run the pinned gem5 integration in a separate local tree."""
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


def environment(cxx=None):
    """Choose compiler/Python libraries for this child process only."""
    env = os.environ.copy()
    if cxx:
        compiler = Path(cxx).resolve()
        env['CXX'] = str(compiler)
        env['CC'] = str(compiler.with_name('gcc'))
        env['PATH'] = str(compiler.parent) + os.pathsep + env.get('PATH', '')
    config = Path(sys.base_prefix) / 'bin/python3-config'
    if config.exists():
        env['PYTHON_CONFIG'] = str(config)
    libdir = sysconfig.get_config_var('LIBDIR')
    if libdir:
        env['LD_LIBRARY_PATH'] = os.pathsep.join(filter(None, [str(libdir), env.get('LD_LIBRARY_PATH', '')]))
    return env


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
            if source.is_file() and source.suffix in ('.cc', '.hh', '.hpp', '.py'):
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
    p.add_argument('action', choices=['prepare', 'build', 'run'])
    p.add_argument('--tree', type=Path, default=ROOT / 'build/gem5')
    p.add_argument('--jobs', type=int, default=4)
    p.add_argument('--cxx', help='compiler for this build only')
    p.add_argument('--outdir', type=Path, help='fresh run directory; required by run')
    arguments = sys.argv[1:]
    split = arguments.index('--') if '--' in arguments else len(arguments)
    a = p.parse_args(arguments[:split])
    config_args = arguments[split+1:]
    try:
        if a.action == 'prepare':
            prepare(a.tree.resolve())
        elif a.action == 'build':
            if not 1 <= a.jobs <= 32:
                p.error('jobs must be 1..32')
            args = [sys.executable, '-m', 'SCons', 'build/X86/gem5.opt', '-j', str(a.jobs)]
            command(args, a.tree.resolve(), environment(a.cxx))
        else:
            if not a.outdir:
                p.error('run requires --outdir and config arguments after --')
            if a.outdir.exists():
                raise ValueError('output exists; choose a fresh run namespace')
            executable = a.tree.resolve() / 'build/X86/gem5.opt'
            if not executable.is_file():
                raise ValueError('gem5 executable is missing; build this tree first')
            command([executable, '--outdir=' + str(a.outdir.resolve()),
                     ROOT / 'simulation/gem5/configs/finite.py'] + config_args,
                    env=environment())
    except (ValueError, subprocess.CalledProcessError) as error:
        p.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
