"""Observe existing B4 coordinator; seal actual evidence when it terminates."""
import sys, pathlib, time, os, datetime
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b4'

def alive(pid, start):
    try:
        fields = (pathlib.Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()
        return fields[19] == start and fields[0] != 'Z'
    except OSError:
        return False

def main():
    driver = r.load(K / 'reports/RUNNING_COORDINATOR.lock.json')
    r.put(K / 'reports/FINALIZATION_WATCHER.lock.json', {
        'status': 'WATCHING_EXISTING_B4_PROCESS_NO_CPU_LAUNCH', 'watcher_pid': os.getpid(),
        'driver': driver, 'script': r.ref(__file__), 'at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    while alive(driver['pid'], driver['start_ticks']):
        time.sleep(5)
    while any(not (pathlib.Path(r.load(p)['output']) / 'EXECUTION.json').exists()
              for p in (ROOT / 'runtime/run_starts').glob('*.json')):
        time.sleep(5)
    import finalize_b4, package_b4
    finalize_b4.audit()
    if (K / 'reports/FINITE_MATRIX_COMPLETED.json').exists():
        import native_break_even_b4
        native_break_even_b4.derive()
    package_b4.package('TERMINAL_A1')
    r.put(K / 'reports/FINALIZATION_WATCHER_DONE.json', {
        'status': 'ACTUAL_B4_AUDIT_AND_HANDOFF_CREATED',
        'terminal_audit': r.ref(K / 'reports/ACTUAL_TERMINAL_AUDIT.json'),
        'archive': r.ref(K / 'reports/PACKAGE_TERMINAL_A1.json'), 'resources': r.snapshot()})

if __name__ == '__main__':
    main()
