"""Ordinary TAGE control compatible with unmodified pinned upstream gem5.

This config deliberately imports no finite/protection SimObjects. A correct
program and clean source tree alone do not certify pristine authenticity.
"""
import argparse
import json
from pathlib import Path
import m5
from m5.objects import (System, SrcClockDomain, VoltageDomain, AddrRange,
    X86O3CPU, Cache, SystemXBar, MemCtrl, SEWorkload, Process, Root,
    BranchPredictor, TAGE, TAGEBase)
from gem5.components.memory.dram_interfaces.ddr3 import DDR3_1600_8x8


def create_system(args, output, conditional_predictor=None):
    system = System()
    clock = '{}ps'.format(args.cycle_ticks) if hasattr(args, 'cycle_ticks') else '2GHz'
    system.clk_domain = SrcClockDomain(clock=clock, voltage_domain=VoltageDomain())
    system.mem_mode = 'timing'
    system.mem_ranges = [AddrRange('256MiB')]
    system.cpu = X86O3CPU(numThreads=1, decoupledFrontEnd=False)
    if conditional_predictor is None:
        conditional_predictor = TAGE(tage=TAGEBase(minHist=5, maxHist=130,
            takenOnlyHistory=False, speculativeHistUpdate=True))
    system.cpu.branchPred = BranchPredictor(instShiftAmt=0,
        conditionalBranchPred=conditional_predictor,
        takenOnlyHistory=False, speculativeHistUpdate=True)
    system.membus = SystemXBar()

    class L1(Cache):
        assoc = 2
        tag_latency = data_latency = response_latency = 2
        mshrs = 4
        tgts_per_mshr = 20

    system.cpu.icache = L1(size='32KiB')
    system.cpu.dcache = L1(size='32KiB')
    system.cpu.icache_port = system.cpu.icache.cpu_side
    system.cpu.dcache_port = system.cpu.dcache.cpu_side
    system.cpu.icache.mem_side = system.membus.cpu_side_ports
    system.cpu.dcache.mem_side = system.membus.cpu_side_ports
    system.cpu.mmu.connectWalkerPorts(system.membus.cpu_side_ports, system.membus.cpu_side_ports)
    system.cpu.createInterruptController()
    system.cpu.interrupts[0].pio = system.membus.mem_side_ports
    system.cpu.interrupts[0].int_requestor = system.membus.cpu_side_ports
    system.cpu.interrupts[0].int_responder = system.membus.mem_side_ports
    system.mem_ctrl = MemCtrl(dram=DDR3_1600_8x8(range=system.mem_ranges[0]))
    system.mem_ctrl.port = system.membus.mem_side_ports
    system.system_port = system.membus.cpu_side_ports
    binary = str(args.binary.resolve())
    system.workload = SEWorkload.init_compatible(binary)
    command = [binary] + ([str(args.input.resolve())] if args.input else [])
    system.cpu.workload = Process(cmd=command, output=str(output/'program.stdout'),
                                  errout=str(output/'program.stderr'))
    system.cpu.createThreads()
    return system


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--max-ticks', type=int, default=2000000000000)
    parser.add_argument('--seed', type=int, default=548)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--initialize-only', action='store_true')
    args = parser.parse_args()
    if not args.binary.is_file() or (args.input and not args.input.is_file()):
        parser.error('binary or input does not exist')
    if args.max_ticks <= 0:
        parser.error('max-ticks must be positive')
    output = Path(m5.options.outdir).resolve()
    system = create_system(args, output)
    root = Root(full_system=False, system=system)
    m5.core.seedRandom(args.seed)
    m5.instantiate()
    if args.initialize_only:
        assert m5.curTick() == 0
        print('PASS_TICK0_NO_CPU')
        return root
    event = m5.simulate(args.max_ticks)
    m5.stats.dump()
    success = event.getCause() == 'exiting with last active thread context' and event.getCode() == 0
    (output/'baseline.json').write_text(json.dumps({
        'execution_status': 'COMPLETE' if success else 'FAILED',
        'baseline_authenticity': 'PRISTINE_AUTHENTICITY_UNVERIFIED',
        'control': 'ordinary TAGE; no finite stages or injector registered by this config',
        'program_exit_tick': m5.curTick(), 'exit_cause': event.getCause(),
        'exit_code': event.getCode(), 'seed': args.seed,
        'missing_authentication_observables': [
            'retired identity', 'prediction/training stream', 'RNG state', 'canonical state'],
    }, indent=2)+'\n')
    print('Exit cause:', event.getCause(), 'code:', event.getCode(), 'tick:', m5.curTick())
    if not success:
        raise RuntimeError('unexpected program termination')
    return root


if __name__ == '__m5_main__':
    root = main()
